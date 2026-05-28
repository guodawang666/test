const savedKey = "signal-radar-saved";
const themeKey = "signal-radar-theme";

const labels = {
  meme: "海外热梗",
  ai: "GitHub AI",
  finance: "国内财经",
};

const state = {
  items: [],
  saved: loadSaved(),
  articleCache: {},
  filter: "all",
  search: "",
  lastUpdated: "",
};

const refreshBtn = document.querySelector("#refreshBtn");
const statusText = document.querySelector("#statusText");
const searchInput = document.querySelector("#searchInput");
const filters = document.querySelector("#filters");
const feedList = document.querySelector("#feedList");
const template = document.querySelector("#feedTemplate");
const totalCount = document.querySelector("#totalCount");
const savedCount = document.querySelector("#savedCount");
const sourceCount = document.querySelector("#sourceCount");
const copySavedBtn = document.querySelector("#copySavedBtn");
const themeBtn = document.querySelector("#themeBtn");

refreshBtn.addEventListener("click", fetchSignals);

searchInput.addEventListener("input", () => {
  state.search = searchInput.value.trim().toLowerCase();
  render();
});

filters.addEventListener("click", (event) => {
  const button = event.target.closest("[data-filter]");
  if (!button) return;

  state.filter = button.dataset.filter;
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("active", chip === button);
  });
  render();
});

feedList.addEventListener("click", async (event) => {
  const card = event.target.closest("[data-id]");
  if (!card) return;

  const id = card.dataset.id;
  const item = state.items.find((entry) => entry.id === id);
  if (!item) return;

  if (event.target.closest(".save-btn")) {
    toggleSaved(item);
    saveSaved();
    render();
  }

  if (event.target.closest(".copy-btn")) {
    await copyText(formatShare(item));
    flashButton(event.target.closest(".copy-btn"), "已复制");
  }

  if (event.target.closest(".article-btn")) {
    await loadArticleSummary(item, card, event.target.closest(".article-btn"));
  }
});

copySavedBtn.addEventListener("click", async () => {
  const savedItems = state.items.filter((item) => state.saved[item.id]);
  if (!savedItems.length) return;

  await copyText(savedItems.map(formatShare).join("\n\n"));
  flashButton(copySavedBtn, "已复制");
});

themeBtn.addEventListener("click", () => {
  const isDark = document.documentElement.classList.toggle("dark");
  localStorage.setItem(themeKey, isDark ? "dark" : "light");
});

async function fetchSignals() {
  refreshBtn.disabled = true;
  refreshBtn.classList.add("loading");
  statusText.textContent = "正在抓取公开信息源...";

  try {
    const response = await fetch(`/api/feed?ts=${Date.now()}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    state.items = payload.items ?? [];
    state.lastUpdated = payload.updatedAt ?? new Date().toISOString();
    statusText.textContent = `已更新 ${formatTime(state.lastUpdated)}，共 ${state.items.length} 条。`;
    render();
  } catch (error) {
    statusText.textContent = "抓取失败：请确认 server.py 正在运行，并且网络可用。";
    console.error(error);
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.classList.remove("loading");
  }
}

async function loadArticleSummary(item, card, button) {
  const panel = card.querySelector(".detail-panel");
  panel.hidden = false;

  if (state.articleCache[item.id]) {
    renderArticlePanel(panel, state.articleCache[item.id]);
    return;
  }

  button.disabled = true;
  const oldLabel = button.textContent;
  button.textContent = "总结中";
  panel.innerHTML = `<p class="detail-loading">正在解析真实原文链接并提取正文...</p>`;

  try {
    const params = new URLSearchParams({
      url: item.url,
      title: item.title,
      category: item.category,
      source: item.source,
    });
    const response = await fetch(`/api/article?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const article = await response.json();
    state.articleCache[item.id] = article;
    item.resolvedUrl = article.resolvedUrl;
    renderArticlePanel(panel, article);
  } catch (error) {
    panel.innerHTML = `<p class="detail-error">原文解析失败。这个来源可能限制抓取，可以先用下方链接打开查看。</p><a class="article-link" href="${escapeAttr(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.url)}</a>`;
    console.error(error);
  } finally {
    button.disabled = false;
    button.textContent = oldLabel;
  }
}

function renderArticlePanel(panel, article) {
  const points = article.points?.length
    ? article.points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")
    : `<li>${escapeHtml(article.summary || "暂时没有提取到足够正文。")}</li>`;
  const sourceNote = article.usedFallback
    ? "未能完整抓取正文，以下是基于标题、摘要和可访问内容生成的总结。"
    : "已基于可访问的原文正文生成总结。";

  panel.innerHTML = `
    <div class="article-source">
      <span>${escapeHtml(sourceNote)}</span>
      <a href="${escapeAttr(article.resolvedUrl)}" target="_blank" rel="noreferrer">打开真实原文</a>
    </div>
    <h4>中文详细总结</h4>
    <p>${escapeHtml(article.summary)}</p>
    <ul>${points}</ul>
    <h4>为什么值得关注</h4>
    <p>${escapeHtml(article.whyItMatters)}</p>
  `;
}

function filteredItems() {
  return state.items.filter((item) => {
    const isSaved = Boolean(state.saved[item.id]);
    const matchesFilter =
      state.filter === "all" ||
      (state.filter === "saved" ? isSaved : item.category === state.filter);
    const searchable = [item.title, item.summary, item.source, labels[item.category]]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch = !state.search || searchable.includes(state.search);

    return matchesFilter && matchesSearch;
  });
}

function render() {
  const items = filteredItems();
  const sources = new Set(state.items.map((item) => item.source).filter(Boolean));

  totalCount.textContent = state.items.length;
  savedCount.textContent = Object.keys(state.saved).length;
  sourceCount.textContent = sources.size;
  feedList.innerHTML = "";

  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.items.length
      ? "没有符合筛选的信息。"
      : "点一下刷新情报，它会主动去公开来源搜集信息。";
    feedList.append(empty);
    return;
  }

  items.forEach((item) => {
    const node = template.content.firstElementChild.cloneNode(true);
    const isSaved = Boolean(state.saved[item.id]);
    node.dataset.id = item.id;
    node.classList.toggle("saved", isSaved);

    const badge = node.querySelector(".badge");
    badge.textContent = labels[item.category] ?? "信息";
    badge.classList.toggle("finance", item.category === "finance");

    node.querySelector("time").textContent = formatTime(item.publishedAt);
    node.querySelector("h3").textContent = item.title;
    node.querySelector(".summary").textContent = item.summary || "暂无摘要，点原文总结查看详情。";
    renderVideoSamples(node.querySelector(".video-samples"), item.videoSamples);
    node.querySelector(".meta-line").textContent = `${item.source} · ${item.reason}`;
    node.querySelector(".save-btn").textContent = isSaved ? "已存" : "保存";
    node.querySelector(".save-btn").classList.toggle("active", isSaved);

    if (state.articleCache[item.id]) {
      const panel = node.querySelector(".detail-panel");
      panel.hidden = false;
      renderArticlePanel(panel, state.articleCache[item.id]);
    }

    feedList.append(node);
  });
}

function renderVideoSamples(container, samples) {
  container.innerHTML = "";
  if (!samples?.length) {
    container.hidden = true;
    return;
  }

  container.hidden = false;
  const title = document.createElement("div");
  title.className = "video-samples-title";
  title.textContent = "代表视频在讲什么";
  container.append(title);

  samples.slice(0, 3).forEach((sample) => {
    const row = document.createElement(sample.url ? "a" : "div");
    row.className = "video-sample";
    if (sample.url) {
      row.href = sample.url;
      row.target = "_blank";
      row.rel = "noreferrer";
    }

    const text = document.createElement("span");
    text.textContent = sample.title;
    row.append(text);

    if (sample.stats) {
      const stats = document.createElement("small");
      stats.textContent = sample.stats;
      row.append(stats);
    }
    container.append(row);
  });
}

function toggleSaved(item) {
  if (state.saved[item.id]) {
    delete state.saved[item.id];
    return;
  }

  state.saved[item.id] = {
    title: item.title,
    url: item.resolvedUrl || item.url,
    category: item.category,
    savedAt: new Date().toISOString(),
  };
}

function formatShare(item) {
  const cached = state.articleCache[item.id];
  const url = cached?.resolvedUrl || item.resolvedUrl || item.url;
  const summary = cached?.summary || item.summary || "";
  return `【${labels[item.category] ?? "信息"}】${item.title}\n${summary}\n${url}`;
}

function loadSaved() {
  try {
    return JSON.parse(localStorage.getItem(savedKey)) ?? {};
  } catch {
    return {};
  }
}

function saveSaved() {
  localStorage.setItem(savedKey, JSON.stringify(state.saved));
}

function formatTime(value) {
  if (!value) return "刚刚";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "刚刚";

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

async function copyText(text) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function flashButton(button, label) {
  const oldLabel = button.textContent;
  button.textContent = label;
  window.setTimeout(() => {
    button.textContent = oldLabel;
  }, 900);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function applySavedTheme() {
  const savedTheme = localStorage.getItem(themeKey);
  if (savedTheme === "dark") {
    document.documentElement.classList.add("dark");
  }
}

applySavedTheme();
render();
fetchSignals();
