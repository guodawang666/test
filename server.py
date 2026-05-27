from __future__ import annotations

import email.utils
import hashlib
import html
import json
import mimetypes
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "4174"))
CACHE_SECONDS = 240
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

FEED_CACHE = {"at": 0.0, "payload": None}
ARTICLE_CACHE: dict[str, dict] = {}


def fetch_url(url: str, timeout: int = 10) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/rss+xml,application/json,text/xml,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def google_news_url(query: str, language: str = "zh-CN", region: str = "CN") -> str:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "hl": language,
            "gl": region,
            "ceid": f"{region}:zh-Hans",
        }
    )
    return f"https://news.google.com/rss/search?{params}"


SOURCES = [
    {
        "kind": "tiktok",
        "category": "meme",
        "source": "TikTok Creative Center",
        "reason": "TikTok 当前热门 hashtag",
        "url": "https://ads.tiktok.com/creative/creativeCenter/trends",
    },
    {
        "kind": "github",
        "category": "ai",
        "source": "GitHub Trending Signals",
        "reason": "近 14 天新发且快速涨星的 AI 项目",
        "url": "https://api.github.com/search/repositories",
    },
    {
        "kind": "rss",
        "category": "finance",
        "source": "Google News",
        "reason": "国内财经关键词",
        "url": google_news_url("中国 财经 OR A股 OR 人民币 OR 中国经济 OR 央行 OR 财报 when:3d"),
    },
]


def collect_feed() -> dict:
    now = time.time()
    if FEED_CACHE["payload"] and now - FEED_CACHE["at"] < CACHE_SECONDS:
        return FEED_CACHE["payload"]

    items = []
    errors = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_source, source): source for source in SOURCES}
        for future in as_completed(futures):
            source = futures[future]
            try:
                items.extend(future.result())
            except Exception as exc:  # noqa: BLE001
                errors.append({"source": source["source"], "error": str(exc)})

    items = dedupe(items)
    items.sort(key=lambda item: item.get("publishedAt") or "", reverse=True)
    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "items": items[:70],
        "errors": errors,
    }
    FEED_CACHE["at"] = now
    FEED_CACHE["payload"] = payload
    return payload


def fetch_source(source: dict) -> list[dict]:
    if source["kind"] == "tiktok":
        return fetch_tiktok_trends(source)
    if source["kind"] == "github":
        return fetch_github_ai_repos(source)

    raw = fetch_url(source["url"])
    if source["kind"] == "hn":
        return parse_hn(raw, source)
    return parse_rss(raw, source)


def fetch_tiktok_trends(source: dict) -> list[dict]:
    names_url = "https://ads.tiktok.com/CreativeOne/Inspiration/PublicGetSeoObjectList?bizType=2"
    request = urllib.request.Request(
        names_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": source["url"],
        },
    )
    names_payload = json.loads(urllib.request.urlopen(request, timeout=12).read().decode("utf-8"))
    names = names_payload.get("name", [])[:12]
    if not names:
        return []

    detail_body = json.dumps({"bizType": 2, "nameList": names}, ensure_ascii=False).encode("utf-8")
    detail_request = urllib.request.Request(
        "https://ads.tiktok.com/CreativeOne/Inspiration/GetSeoObjectDetail",
        data=detail_body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": source["url"],
        },
    )
    detail_payload = json.loads(urllib.request.urlopen(detail_request, timeout=15).read().decode("utf-8"))
    updated_at = datetime.fromtimestamp(names_payload.get("lastUpdateTime", time.time()), timezone.utc).isoformat()
    items = []
    for detail in detail_payload.get("seoObjectDetailList", []):
        hashtag = detail.get("hashtagObjDetail") or {}
        name = hashtag.get("name")
        if not name:
            continue
        views = hashtag.get("videoViews") or 0
        publish_count = hashtag.get("publishCnt") or 0
        wow = hashtag.get("publishCntWow")
        view_wow = hashtag.get("videoViewsWow")
        related_videos = hashtag.get("relatedVideos") or []
        interest_tags = hashtag.get("interestHashtag") or []
        top_video = related_videos[0] if related_videos else {}
        video_url = (
            top_video.get("itemLink")
            or top_video.get("userLink")
            or f"https://www.tiktok.com/tag/{urllib.parse.quote(name)}"
        )
        video_samples = build_tiktok_video_samples(related_videos)
        related_tag_names = [tag.get("name") for tag in interest_tags[:5] if tag.get("name") and tag.get("name") != name]
        explanation = explain_tiktok_topic(name, video_samples, related_tag_names).rstrip("。")
        summary_parts = [
            f"这是什么：{explanation}",
            f"为什么热：#{name} 正在 TikTok Creative Center 榜单中升温，累计播放量约 {format_large_number(views)}，发布量约 {format_large_number(publish_count)}",
        ]
        if isinstance(wow, (int, float)):
            summary_parts.append(f"近期发布量变化 {wow:+.0%}")
        if isinstance(view_wow, (int, float)):
            summary_parts.append(f"近期播放量变化 {view_wow:+.0%}")
        if top_video.get("likeCnt"):
            summary_parts.append(f"代表视频点赞约 {format_large_number(top_video.get('likeCnt'))}")

        item = make_item(
            source=source,
            title=f"TikTok 热门话题：#{name}",
            url=video_url,
            summary="；".join(summary_parts) + "。",
            published_at=updated_at,
        )
        item["videoSamples"] = video_samples
        item["relatedTags"] = related_tag_names
        item["stats"] = {
            "views": views,
            "publishCount": publish_count,
            "publishCountWow": wow,
            "videoViewsWow": view_wow,
        }
        items.append(item)
    return items


def fetch_github_ai_repos(source: dict) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
    queries = [
        f"llm created:>{since} stars:>20",
        f"ai-agent created:>{since} stars:>10",
        f"mcp created:>{since} stars:>10",
        f"rag created:>{since} stars:>10",
        f"openai created:>{since} stars:>10",
        f"claude created:>{since} stars:>10",
        f"gemini created:>{since} stars:>10",
    ]
    repos = {}
    for query in queries:
        params = urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": 12})
        request = urllib.request.Request(
            f"{source['url']}?{params}",
            headers={
                "User-Agent": "signal-radar",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            payload = json.loads(urllib.request.urlopen(request, timeout=12).read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for repo in payload.get("items", []):
            full_name = repo.get("full_name")
            if not full_name:
                continue
            repos[full_name] = repo

    ranked = sorted(
        repos.values(),
        key=lambda repo: (
            repo.get("stargazers_count") or 0,
            repo.get("forks_count") or 0,
            repo.get("updated_at") or "",
        ),
        reverse=True,
    )
    items = []
    for repo in ranked[:26]:
        stars = repo.get("stargazers_count") or 0
        forks = repo.get("forks_count") or 0
        created_at = repo.get("created_at")
        description = clean_text(repo.get("description")) or "暂无项目描述。"
        topics = ", ".join(repo.get("topics") or [])
        summary = (
            f"GitHub 近 14 天新建 AI 相关仓库，当前 {stars} stars、{forks} forks。"
            f"项目描述：{description}"
        )
        if topics:
            summary += f" Topics：{topics}。"
        items.append(
            make_item(
                source=source,
                title=f"{repo.get('full_name')}：{description[:72]}",
                url=repo.get("html_url"),
                summary=summary,
                published_at=created_at,
            )
        )
    return items


def build_tiktok_video_samples(videos: list[dict]) -> list[dict]:
    samples = []
    for video in videos[:4]:
        title = clean_text(video.get("title"))
        if not title:
            continue
        url = video.get("itemLink") or video.get("userLink") or ""
        stats = []
        if video.get("videoViews"):
            stats.append(f"{format_large_number(video.get('videoViews'))} 播放")
        if video.get("likeCnt"):
            stats.append(f"{format_large_number(video.get('likeCnt'))} 赞")
        if video.get("commentCnt"):
            stats.append(f"{format_large_number(video.get('commentCnt'))} 评论")
        user_name = video.get("userName")
        plain = f"{title}"
        if user_name:
            plain += f"（@{user_name}）"
        if stats:
            plain += f"，{ '，'.join(stats) }"
        samples.append(
            {
                "title": title,
                "url": url,
                "userName": user_name,
                "stats": "，".join(stats),
                "plainText": plain,
            }
        )
    return samples


def explain_tiktok_topic(name: str, video_samples: list[dict], related_tags: list[str]) -> str:
    lower_name = name.lower()
    sample_text = " ".join(sample["title"].lower() for sample in video_samples)
    related = "、".join(f"#{tag}" for tag in related_tags[:4])

    if any(word in lower_name for word in ("live", "incentive", "paidpartnership")):
        return "这更像 TikTok 官方直播/商业合作活动标签，不是自然形成的段子梗；相关视频多是在参加 LIVE 活动、带广告合作标签或引导直播互动。"
    if any(word in lower_name for word in ("football", "futbol", "soccer", "neymar", "worldcup")) or any(
        word in sample_text for word in ("football", "futebol", "world cup", "copa", "neymar")
    ):
        return "这是足球/球星相关热度，相关视频通常是比赛片段、球员反应、进球剪辑或粉丝二创。"
    if any(word in lower_name for word in ("music", "dance", "song")) or any(
        word in sample_text for word in ("dance", "song", "music", "cover")
    ):
        return "这是音乐或舞蹈类传播话题，相关视频通常围绕同一段音乐、动作模板或翻跳进行二创。"
    if any(word in lower_name for word in ("game", "mobilelegends", "roblox", "minecraft")) or any(
        word in sample_text for word in ("game", "mobile legends", "roblox", "minecraft")
    ):
        return "这是游戏相关话题，相关视频通常是高光操作、搞笑片段、皮肤/角色内容或玩家社区梗。"
    if video_samples:
        sample_titles = "；".join(sample["title"] for sample in video_samples[:2])
        suffix = f" 同时它和 {related} 等标签一起出现。" if related else ""
        return f"从榜内代表视频看，它主要围绕这些内容传播：{sample_titles}。{suffix}"
    if related:
        return f"它和 {related} 等标签同时出现在热门榜，说明它属于同一批社媒传播话题。"
    return "这是 TikTok Creative Center 当前榜单里的热门标签，但公开数据没有给出足够视频文案，需要打开代表视频确认具体语境。"


def parse_hn(raw: bytes, source: dict) -> list[dict]:
    data = json.loads(raw.decode("utf-8"))
    items = []
    for hit in data.get("hits", []):
        title = clean_text(hit.get("title") or hit.get("story_title"))
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        if not title or not url:
            continue
        points = hit.get("points") or 0
        comments = hit.get("num_comments") or 0
        summary = f"Hacker News 新讨论，{points} 分，{comments} 条评论。"
        items.append(
            make_item(
                source=source,
                title=title,
                url=url,
                summary=summary,
                published_at=hit.get("created_at"),
            )
        )
    return items


def parse_rss(raw: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(raw)
    items = []
    for entry in root.findall(".//item")[:24]:
        if "trends.google.com" in source["url"]:
            trend_item = parse_google_trends_item(entry, source)
            if trend_item:
                items.append(trend_item)
            continue

        title = clean_text(entry.findtext("title"))
        url = clean_text(entry.findtext("link"))
        description = clean_text(entry.findtext("description"))
        published = parse_date(entry.findtext("pubDate"))
        source_node = entry.find("source")
        source_name = clean_text(source_node.text if source_node is not None else None) or source["source"]
        if not title or not url:
            continue
        items.append(
            make_item(
                source={**source, "source": source_name},
                title=title,
                url=url,
                summary=description[:220],
                published_at=published,
            )
        )
    return items


def parse_google_trends_item(entry: ET.Element, source: dict) -> dict | None:
    namespace = "{https://trends.google.com/trending/rss}"
    trend_title = clean_text(entry.findtext("title"))
    traffic = clean_text(entry.findtext(f"{namespace}approx_traffic"))
    published = parse_date(entry.findtext("pubDate"))
    news_items = entry.findall(f"{namespace}news_item")

    for news in news_items:
        article_title = clean_text(news.findtext(f"{namespace}news_item_title"))
        article_url = clean_text(news.findtext(f"{namespace}news_item_url"))
        article_source = clean_text(news.findtext(f"{namespace}news_item_source"))
        snippet = clean_text(news.findtext(f"{namespace}news_item_snippet"))
        if not article_url:
            continue

        summary_parts = [f"趋势词：{trend_title}"]
        if traffic:
            summary_parts.append(f"搜索热度：{traffic}")
        if article_title:
            summary_parts.append(f"相关报道：{article_title}")
        if snippet:
            summary_parts.append(snippet)

        return make_item(
            source={**source, "source": article_source or source["source"]},
            title=trend_title or article_title,
            url=article_url,
            summary="。".join(summary_parts),
            published_at=published,
        )

    return None


def make_item(source: dict, title: str, url: str, summary: str, published_at: str | None) -> dict:
    item_id = hashlib.sha1(f"{source['category']}|{normalize_url(url)}|{title}".encode("utf-8")).hexdigest()[:16]
    return {
        "id": item_id,
        "category": source["category"],
        "title": title,
        "summary": summary,
        "url": url,
        "source": source["source"],
        "reason": source["reason"],
        "publishedAt": published_at or datetime.now(timezone.utc).isoformat(),
    }


def build_article_summary(url: str, title: str, category: str, source: str) -> dict:
    cache_key = hashlib.sha1(f"{url}|{title}".encode("utf-8")).hexdigest()
    if cache_key in ARTICLE_CACHE:
        return ARTICLE_CACHE[cache_key]

    resolved_url = resolve_original_url(url)
    used_fallback = False
    article_text = ""
    meta_description = ""

    try:
        raw_html = fetch_url(resolved_url, timeout=12).decode("utf-8", errors="ignore")
        meta_description = extract_meta_description(raw_html)
        article_text = extract_article_text(raw_html)
    except Exception:  # noqa: BLE001
        used_fallback = True

    base_text = " ".join([title, meta_description, article_text]).strip()
    if len(base_text) < 120:
        base_text = " ".join([title, source]).strip()
        used_fallback = True

    sentences = split_sentences(base_text)
    selected = select_summary_sentences(sentences)
    translated_points = [translate_to_chinese(sentence) for sentence in selected[:6]]
    translated_title = translate_to_chinese(title)
    overview_source = " ".join(selected[:3]) or title
    overview = translate_to_chinese(overview_source)

    summary = f"这篇原文主要讲：{overview}"
    why = build_why_it_matters(category, translated_title, translated_points)

    payload = {
        "resolvedUrl": resolved_url,
        "title": translated_title,
        "summary": summary,
        "points": translated_points,
        "whyItMatters": why,
        "usedFallback": used_fallback,
    }
    ARTICLE_CACHE[cache_key] = payload
    return payload


def resolve_original_url(url: str) -> str:
    if "news.google.com/" not in url:
        return url

    try:
        page = fetch_url(url, timeout=12).decode("utf-8", errors="ignore")
        article_id = find_attr(page, "data-n-a-id") or google_article_id_from_url(url)
        timestamp = find_attr(page, "data-n-a-ts")
        signature = find_attr(page, "data-n-a-sg")
        if not article_id or not timestamp or not signature:
            return url

        request_payload = [
            "garturlreq",
            [
                [
                    "zh-CN",
                    "CN",
                    ["FINANCE_TOP_INDICES", "WEB_TEST_1_0_0"],
                    None,
                    None,
                    1,
                    1,
                    "CN:zh-Hans",
                    None,
                    180,
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    None,
                    None,
                    [int(timestamp), 0],
                ],
                "zh-CN",
                "CN",
                1,
                [2, 3, 4, 8],
                1,
                0,
                "655000234",
                0,
                0,
                None,
                0,
            ],
            article_id,
            int(timestamp),
            signature,
        ]
        f_req = [[["Fbv4je", json.dumps(request_payload, separators=(",", ":")), None, "generic"]]]
        body = urllib.parse.urlencode({"f.req": json.dumps(f_req, separators=(",", ":"))}).encode("utf-8")
        request = urllib.request.Request(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je",
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Referer": url,
            },
        )
        response_text = urllib.request.urlopen(request, timeout=12).read().decode("utf-8", errors="ignore")
        match = re.search(r"https?://[^\\\"\]]+", response_text)
        if match:
            return html.unescape(match.group(0))
    except Exception:  # noqa: BLE001
        return url

    return url


def find_attr(markup: str, name: str) -> str | None:
    match = re.search(rf'{re.escape(name)}="([^"]+)"', markup)
    return html.unescape(match.group(1)) if match else None


def google_article_id_from_url(url: str) -> str | None:
    match = re.search(r"/articles/([^?]+)", url)
    return match.group(1) if match else None


def extract_meta_description(markup: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, markup, flags=re.I)
        if match:
            return clean_text(match.group(1))
    return ""


def extract_article_text(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style|noscript|svg|header|footer|nav|aside).*?</\1>", " ", markup)
    article_match = re.search(r"(?is)<article[^>]*>(.*?)</article>", markup)
    scope = article_match.group(1) if article_match else markup
    paragraphs = re.findall(r"(?is)<p[^>]*>(.*?)</p>", scope)
    cleaned = [clean_text(paragraph) for paragraph in paragraphs]
    useful = [paragraph for paragraph in cleaned if 45 <= len(paragraph) <= 900]
    if len(useful) < 3:
        useful = [paragraph for paragraph in cleaned if len(paragraph) >= 25]
    return " ".join(useful[:18])


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+", text)
    return [part.strip() for part in parts if 30 <= len(part.strip()) <= 420]


def select_summary_sentences(sentences: list[str]) -> list[str]:
    if not sentences:
        return []

    keywords = (
        "OpenAI",
        "AI",
        "model",
        "agent",
        "China",
        "market",
        "stock",
        "央行",
        "人民币",
        "A股",
        "TikTok",
        "trend",
        "viral",
        "meme",
        "because",
        "reported",
        "said",
    )
    scored = []
    for index, sentence in enumerate(sentences[:28]):
        score = max(0, 16 - index)
        score += sum(4 for keyword in keywords if keyword.lower() in sentence.lower())
        score += min(len(sentence) // 80, 4)
        scored.append((score, index, sentence))

    chosen = sorted(scored, reverse=True)[:7]
    return [sentence for _, _, sentence in sorted(chosen, key=lambda item: item[1])]


def translate_to_chinese(text: str) -> str:
    text = clean_text(text)
    if not text:
        return ""
    if contains_chinese(text):
        return text

    chunks = chunk_text(text, 1200)
    translated = []
    for chunk in chunks:
        try:
            params = urllib.parse.urlencode(
                {
                    "client": "gtx",
                    "sl": "auto",
                    "tl": "zh-CN",
                    "dt": "t",
                    "q": chunk,
                }
            )
            raw = fetch_url(f"https://translate.googleapis.com/translate_a/single?{params}", timeout=10)
            data = json.loads(raw.decode("utf-8"))
            translated.append("".join(part[0] for part in data[0] if part and part[0]))
        except Exception:  # noqa: BLE001
            translated.append(chunk)
    return "".join(translated)


def chunk_text(text: str, limit: int) -> list[str]:
    chunks = []
    current = ""
    for sentence in split_sentences(text) or [text]:
        if len(current) + len(sentence) > limit and current:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current[:limit])
    return chunks


def build_why_it_matters(category: str, title: str, points: list[str]) -> str:
    joined = " ".join(points[:3])
    if category == "ai":
        return f"它值得关注，因为这类消息往往会影响模型能力边界、AI 产品节奏和开发者可用工具。结合原文看，重点是：{joined[:220]}"
    if category == "finance":
        return f"它值得关注，因为财经消息会影响市场预期、资产价格和政策判断。结合原文看，重点是：{joined[:220]}"
    if category == "meme":
        return f"它值得关注，因为热梗通常反映了海外社媒正在传播的情绪、话题和表达方式。结合原文看，重点是：{joined[:220]}"
    return f"它值得关注，因为它可能影响你后续的信息判断。标题是：{title}"


def format_large_number(value: int | float | None) -> str:
    if not value:
        return "0"
    value = float(value)
    if value >= 100_000_000:
        return f"{value / 100_000_000:.1f} 亿"
    if value >= 10_000:
        return f"{value / 10_000:.1f} 万"
    return str(int(value))


def dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        key = normalize_title(item["title"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def normalize_title(title: str) -> str:
    value = title.lower()
    value = re.sub(r"[\W_]+", "", value, flags=re.UNICODE)
    return value[:90]


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/feed":
            self.send_json(collect_feed())
            return

        if parsed.path == "/api/article":
            params = urllib.parse.parse_qs(parsed.query)
            self.send_json(
                build_article_summary(
                    url=(params.get("url") or [""])[0],
                    title=(params.get("title") or [""])[0],
                    category=(params.get("category") or [""])[0],
                    source=(params.get("source") or [""])[0],
                )
            )
            return

        path = parsed.path.strip("/") or "index.html"
        target = (ROOT / path).resolve()
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(target.read_bytes())

    def send_json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[radar] {self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"信息雷达已启动：http://127.0.0.1:{PORT}")
    print(f"同一 Wi-Fi 下的手机请打开：http://电脑局域网IP:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
