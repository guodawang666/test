---
name: resume-job-customizer
description: Use this skill when the user provides a resume and a target job description, and wants a customized Chinese resume optimized for the job while keeping the original structure, truthful experience, one-page A4 layout, black font style, readable font size, reasonable margins, and Word/PDF outputs. Also use it when the user asks to explain optimized resume keywords for interview preparation.
---

# Resume Job Customizer

This skill turns a user's original resume plus a target job description into a polished, job-matched resume. It is designed for Chinese internship/job applications, especially business, marketing, cross-border e-commerce, DTC independent-site operations, overseas social media marketing, platform operations, and related roles.

## Core Principles

1. Keep the user's real background. Do not invent responsibilities, platforms, tools, companies, awards, certificates, or metrics.
2. Improve wording and matching, not truthfulness. Rewrite existing experience so it better matches the job description.
3. Maintain a one-page A4 resume unless the user explicitly requests otherwise.
4. Keep the basic template and section structure close to the user's original resume.
5. Use a clean business style: black font style, clear hierarchy, readable font size, and reasonable margins.
6. Avoid overly small text, cramped spacing, strange line breaks, overlap, or excessive blank space.
7. Export both editable Word `.docx` and final delivery PDF `.pdf` when the environment supports document generation.
8. After resume optimization, prepare short interview explanations for potentially questioned keywords.

## Standard User Input

The user may provide:

- Original resume as PDF, Word, image, or pasted text.
- Target job description or job requirements.
- Target role name.
- Optional preferences, such as "keep format", "one page A4", "use black font", "make it full but not crowded", or "make it suitable for internship delivery".

If the target role is not clearly stated, infer it from the job description. If the original resume is missing key information, work with the available content and do not fabricate.

## Workflow

### Step 1: Read the Original Resume

Extract and preserve the user's existing information:

- Name and contact information.
- Education background.
- Work/internship experience.
- Project experience.
- Student organization or club experience.
- Competition experience.
- Skills and certificates.
- Personal advantages or summary.

If the source file contains visual layout, inspect the rendered page when possible, not only the parsed text, because resumes often have columns, section bars, hidden text, or layout issues.

### Step 2: Analyze the Job Description

Extract the hiring keywords from the JD, including:

- Role orientation.
- Core responsibilities.
- Required tools/platforms.
- Required skills.
- Preferred background.
- Metrics mentioned in the JD.
- Soft skills and long-term development expectations.

For cross-border e-commerce / DTC independent-site marketing roles, common keywords include:

- 跨境电商
- DTC独立站
- 美国独立站运营
- 产品上架
- Listing优化
- 页面排版
- Meta / Google / TikTok
- 英文文案
- 短视频素材
- 广告投放
- CTR / ROAS / 转化率
- 竞品调研
- 用户需求
- 黑五 / 圣诞 / 大促活动
- 折扣活动 / 优惠码
- 数据复盘

### Step 3: Build a Match Map

Create an internal match between job requirements and the user's real experiences.

Example:

| Job Requirement | User Experience | Optimization Direction |
|---|---|---|
| Independent-site or platform operations | OTA / Meituan homestay operation | Listing optimization, page content, pricing, conversion path |
| Overseas social media marketing | Huawei MKT / Douyin / Xiaohongshu content | UGC content, short videos, influencer coordination, content data |
| Data analysis | Revenue, views, reach, adoption of suggestions | Exposure, clicks, conversion, review reports |
| Market research | Competition or user research experience | Target users, competitor analysis, market positioning |
| Campaign execution | Student union events or promotions | Event planning, resource coordination, landing execution |

Use this map to decide what to emphasize. Do not include the map in the final resume unless the user asks.

### Step 4: Rewrite Resume Content

Rewrite the resume in a more job-matched way.

Preferred style:

- Start each bullet with action verbs: 负责、协助、参与、对接、整理、分析、优化、策划、执行、跟进.
- Use measurable results when already present in the original resume.
- Connect platform operations with traffic, exposure, clicks, conversion, user experience, and data review.
- Use internship-level wording. Do not make the user sound like a senior manager.
- Use professional but safe wording such as “了解”, “参与”, “协助”, “具备基础认知”, when the user has not independently owned a tool or task.

Avoid:

- “精通” unless clearly proven.
- “独立负责Google Ads投放” if the user only understands basic ad logic.
- Fake metrics.
- Inflated leadership claims.
- Generic phrases that do not match the JD.

### Step 5: Recommended Resume Structure

Default structure:

1. Header: name, phone, email, age/gender if already in original resume.
2. Education Background.
3. Work Experience.
4. Project Experience.
5. Student Organization / Club Experience.
6. Competition Experience.
7. Personal Advantages.
8. Skills.

For marketing and e-commerce applications, emphasize Work Experience and Project Experience. Reduce less relevant content if space is tight.

### Step 6: Layout Rules

Use the user's preferred style:

- A4 portrait page.
- One page.
- Content should roughly fill the A4 page.
- Reasonable top, bottom, left, and right margins.
- Unified black font style for Chinese text, such as SimHei/黑体 or a close sans-serif fallback.
- Clear section headings.
- Font must not be too small.
- Spacing should be comfortable but not loose.
- Avoid awkward whitespace, cramped text, overlap, strange alignment, or page overflow.
- Export Word first, then PDF.
- Visually inspect the PDF after export if possible.

### Step 7: Output Format

When completing the task, provide:

1. A concise explanation of what was optimized.
2. Download links for the Word and PDF files when generated.
3. Optionally, a short interview explanation pack for resume keywords that may be questioned.

### Step 8: Interview Explanation Pack

When the user asks “帮我解释一下这些，方便问到时候回答”, prepare simple interview-ready answers.

For each keyword:

- Explain what it means.
- Connect it to the user's real experience.
- Provide a short answer suitable for interviews.
- Avoid sounding overqualified or fake.

Example: OTA平台运营逻辑

> 我理解OTA平台运营的核心是围绕“曝光—点击—咨询—转化—评价”这条路径优化。比如在美团民宿运营中，可以通过标题、图片、价格、活动和评价等因素提升房源曝光和下单转化。所以它不是简单上架产品，而是持续根据页面表现和用户反馈去优化转化效率。

Example: DTC独立站流量与转化

> 我理解DTC独立站的核心是“先引流，再转化”。独立站没有平台自带流量，所以需要通过社媒、广告、KOL、SEO等渠道引流；用户进入网站后，再通过产品页面、卖点、优惠、评价、物流和支付信息提升信任感和转化率。我之前的OTA运营和社媒内容经历，可以迁移到内容优化、用户分析和数据复盘上。

Example: Meta / Google / TikTok传播逻辑

> Meta更偏兴趣人群和品牌种草，Google更偏承接主动搜索需求，TikTok更偏短视频内容传播。我的理解还在基础阶段，但我有内容策划、短视频、博主对接和数据观察经验，可以在岗位中继续学习海外平台投放和传播逻辑。

## Quality Checklist

Before final delivery, check:

- Does every bullet come from the user's real background?
- Does the resume clearly match the JD keywords?
- Is the wording suitable for an intern, not exaggerated?
- Is the page one A4 page?
- Are margins reasonable?
- Is the font black/sans-serif style and readable?
- Are Word and PDF both produced if possible?
- Are there any layout problems in the exported PDF?
- Are risky keywords explained for interview follow-up?
