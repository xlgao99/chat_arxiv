## 目标与范围
- **每天自动化**：从 arXiv 拉取“新增/更新”的论文（按类别订阅），再用关键词过滤得到与“强化学习 + 后训练/对齐”相关的集合。
- **自动总结**：调用 **DeepSeek** 生成面向阅读的中文总结（包含关键贡献、方法、实验结论、与 RL/后训练的关系、局限）。
- **自动投递**：通过 **GitHub Actions** 定时执行，将当日摘要用 **SMTP** 发送到你的邮箱。
- **可靠性**：去重（同一篇论文只发一次，或仅在版本更新时再发一次）、失败重试、速率限制、可观测日志。

## 关键约束与默认假设（可配置）
- **arXiv 源**：使用官方 Atom API `http://export.arxiv.org/api/query`（稳定、无需 key）。
- **订阅类别（默认）**：`cs.AI`, `cs.LG`, `stat.ML`（可在配置中增删）。
- **关键词过滤（默认，大小写不敏感）**：
  - RL/算法：`reinforcement learning`, `policy optimization`, `PPO`, `RL`, `Q-learning`
  - 后训练/对齐：`post-training`, `alignment`, `RLHF`, `preference optimization`, `DPO`, `IPO`, `KTO`, `RLAIF`, `reward model`, `SFT`, `instruction tuning`
  - 可加：`LLM`, `language model`, `agent`
- **语言**：邮件与总结默认中文。
- **邮件发送**：SMTP（通过 Actions Secrets 提供账号/密码/主机/端口）。

## 状态与去重策略（重要）
GitHub Actions 每次是“干净环境”，需要持久化“已处理论文”的状态。两种实现：
- **方案 A（默认推荐）Repo 状态文件**：在仓库内维护 `data/state.json`（记录已发送的 arXiv id + 版本号/更新时间戳）。Action 运行后自动提交更新（使用 `GITHUB_TOKEN`）。
  - 优点：稳定、透明、可追踪。
  - 缺点：仓库会有每日小提交。
- **方案 B GitHub Actions Cache**：用 cache 存 `data/state.json`。
  - 优点：不产生提交。
  - 缺点：cache 不保证永远可用，偶发丢失会导致重复发送。

规划默认采用 **方案 A**，并在配置里提供开关。

## 架构与数据流
```mermaid
flowchart TD
  cron[GitHubActionsCron] --> run[python -m app.main]
  run --> fetch[ArxivFetcher
(categories+timeWindow)]
  fetch --> filter[KeywordFilter
(title+abstract)]
  filter --> dedupe[StateStore
(skipSeenOrNot)]
  dedupe --> summarize[DeepSeekSummarizer]
  summarize --> render[EmailRenderer
(HTML+Text)]
  render --> send[SmtpMailer]
  send --> persist[StateStore
(updateState)]
  persist -->|OptionA| commit[CommitStateToRepo]
```

## 仓库结构（建议）
- `plan.md`：本规划。
- `app/`
  - `main.py`：入口；组织流程、参数解析、日志。
  - `config.py`：从环境变量与 `config.yaml` 读取配置并校验。
  - `arxiv_client.py`：按类别与时间窗口拉取；解析 Atom。
  - `filtering.py`：关键词过滤与打分（可选：最低分阈值）。
  - `state_store.py`：读写 `data/state.json`，实现去重策略。
  - `deepseek_client.py`：HTTP 客户端；重试、超时、限速。
  - `summarizer.py`：提示词模板与批处理；控制 token 与并发。
  - `renderer.py`：把结果渲染成 HTML/纯文本邮件。
  - `mailer.py`：SMTP 发送（TLS/SSL、重试）。
- `data/`
  - `state.json`：已处理论文状态（方案 A 会随 Action 自动更新）。
- `.github/workflows/daily.yml`：定时任务与 secrets 注入。
- `requirements.txt`：依赖管理。
- `README.md`：本地运行说明、secrets、常见问题。

## DeepSeek 总结策略（提示词与输出格式）
- **输入**：标题、作者、类别、摘要、arXiv 链接、（可选）PDF 前 N 页文本（可后续迭代）。
- **输出（每篇固定结构，便于邮件排版）**：
  - 1 句话结论（适合扫读）
  - 核心贡献（3-5 条）
  - 方法要点（3-5 条）
  - 实验与结果（若摘要不足则注明“摘要未提供细节”）
  - 与“强化学习/后训练/对齐”的关联（1-3 条）
  - 局限与开放问题（1-3 条）
- **工程约束**：
  - 单次请求最多 N 篇（默认 5-10）分批，防止上下文过长。
  - 失败重试（指数退避），并在邮件末尾列出“本次未总结成功的条目”。

## GitHub Actions 设计
- **触发**：
  - `schedule`：每天固定时间（UTC）运行。
  - `workflow_dispatch`：手动触发便于调试。
- **步骤**：checkout → setup-python → install deps → run 脚本 →（方案 A）提交 `data/state.json`。
- **Secrets（SMTP）**：
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
  - `MAIL_FROM`, `MAIL_TO`（可支持多个收件人，以逗号分隔）
- **Secrets（DeepSeek）**：
  - `DEEPSEEK_API_KEY`
  - 可选：`DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`

## 可测试性与本地运行
- 提供 `DRY_RUN=1`：不发邮件，只在 stdout 打印渲染结果。
- 提供 `LIMIT=10`：限制当天最多处理 N 篇。
- 提供 `SINCE_HOURS=24`：控制时间窗口（默认 24 小时）。

## 里程碑与验收标准
- **M1 抓取+过滤**：能从指定类别拉取并过滤出相关论文；日志输出清晰。
- **M2 总结**：DeepSeek 输出稳定、结构化；失败可重试。
- **M3 邮件投递**：SMTP 成功发送 HTML/纯文本；主题包含日期与数量。
- **M4 去重/状态**：连续两天运行不重复发送；版本更新可选“再发”。
- **M5 Actions 定时**：在 GitHub 上按 cron 正常运行并可追踪日志。

## 风险与应对
- **重复或漏发**：通过 `data/state.json` 记录 arXiv id + `updated` 时间戳；并在抓取时用 `sortBy=lastUpdatedDate` + 时间窗口兜底。
- **摘要信息不足**：邮件中明确标注“基于摘要总结”；后续可加入 PDF 抽取作为增强。
- **SMTP 限制**：添加重试与降频；必要时支持分批发送或改用邮件服务商 API。

