# chat_arxiv

每天从 arXiv（按类别订阅 + 关键词过滤）抓取强化学习/后训练相关论文，调用 DeepSeek 生成中文总结，并通过 GitHub Actions 定时发送到邮箱（SMTP）。

## 本地运行（推荐先 DRY_RUN）

1) 安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) 只跑抓取/渲染，不发邮件、不调用 DeepSeek（便于调试）：

```bash
DRY_RUN=1 python -m app.main
```

你也可以调整时间窗口与数量：

```bash
DRY_RUN=1 SINCE_HOURS=24 LIMIT=30 python -m app.main
```

## 环境变量（GitHub Actions Secrets 同名）

### arXiv
- `ARXIV_CATEGORIES`: 逗号分隔，例如 `cs.AI,cs.LG,stat.ML`
- `SINCE_HOURS`: 默认 `24`
- `LIMIT`: 默认 `50`
- `KEYWORDS`: 逗号分隔关键词（可选；不提供则使用内置默认关键词）

### DeepSeek
- `DEEPSEEK_API_KEY`: 必填（要生成总结时）
- `DEEPSEEK_BASE_URL`: 可选，默认 `https://api.deepseek.com`
- `DEEPSEEK_MODEL`: 可选，默认 `deepseek-chat`
- `DEEPSEEK_TIMEOUT_S`: 可选，默认 `60`
- `DEEPSEEK_MAX_RETRIES`: 可选，默认 `3`

### 邮件（SMTP）
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
- `SMTP_USE_SSL`: `true/false`（常见：465 用 SSL）
- `SMTP_STARTTLS`: `true/false`（常见：587 用 STARTTLS）
- `MAIL_FROM`: 发件人地址
- `MAIL_TO`: 收件人，逗号分隔（支持多个）

### 其他
- `DRY_RUN`: `1` 时不发邮件（但仍会渲染输出）
- `STATE_PATH`: 默认 `data/state.json`
- `RESEND_ON_UPDATE`: `true` 时当论文更新版本会再次发送

## GitHub Actions

工作流在 `.github/workflows/daily.yml`，默认每天定时运行，也支持手动触发。
首次使用需要在仓库设置里添加上述 Secrets。

