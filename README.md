# Daily Brief（Notion 自动日报）

这是一个使用 Python 编写的自动化脚本项目，每天在 Notion 中自动生成一页「Daily Brief」，内容包含：

- 📰 当日热点新闻（最多 10 条，去重 + 简要摘要）
- ⭐ GitHub 当日 Trending 项目（最多 10 个，按当日 star 排序）
- 🔥 微博热搜（最多 3 条）
- 📰 Hacker News 热帖（最多 3 条）
- 💡 知乎热榜（最多 3 条）

目标是：**信息密度高、形式克制、每天只一页、方便长期回顾**。

## 功能说明

- 从 GitHub Trending（自定义 API 或直接抓取 github.com/trending）获取热门仓库
- 从多个国内 RSS 源获取新闻热点（IT 之家 / 瓦斯 / 百度）
- **新增** 微博热搜、Hacker News、知乎热榜数据源
- **新增** DeepSeek AI 智能摘要和翻译（可选）
- 使用标题相似度做去重，只保留同一事件的一条
- 内置自动重试机制，网络异常时自动重试
- 集中配置管理，支持环境变量覆盖
- 每天在 Notion 的 `Daily Brief` 数据库中**只创建一条**记录
- 可通过 `schedule` 常驻运行，也可用 cron / GitHub Actions 定时触发

## 工程结构
```
daily-brief/
├─ main.py              # 主入口
├─ config.py            # 配置管理
├─ news_fetcher.py      # RSS 新闻抓取
├─ github_trending.py   # GitHub Trending
├─ weibo_fetcher.py     # 微博热搜
├─ hn_fetcher.py        # Hacker News
├─ zhihu_fetcher.py     # 知乎热榜
├─ ai_summarizer.py     # AI 摘要（DeepSeek）
├─ notion_writer.py     # Notion API 写入
├─ utils.py             # 工具函数
├─ .env.example         # 环境变量示例
├─ requirements.txt     # 依赖
└─ README.md
```

## 安装步骤

1）准备 Python 环境：Python 3.10+，并确认已安装 `pip`

2）安装依赖：
```bash
pip install -r requirements.txt
```

3）复制环境变量配置：
```bash
cp .env.example .env  # Windows 请手动复制
```

4）在 `.env` 中填写配置（详见下方说明）

## 环境变量配置

### 必需配置
```env
NOTION_TOKEN=secret_xxx          # Notion 集成的 Token
NOTION_DATABASE_ID=xxxx          # Daily Brief 数据库 ID
```

### 可选配置
```env
# GitHub
GITHUB_TRENDING_API=             # 国内 GitHub Trending 代理 API
GITHUB_LIMIT=10                  # GitHub 项目数量

# 百度翻译（翻译 GitHub 描述）
BAIDU_FANYI_APP_ID=
BAIDU_FANYI_SECRET=

# DeepSeek AI（智能摘要和翻译）
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
AI_SUMMARY_ENABLED=false         # 设为 true 启用 AI 摘要

# 数据源开关
WEIBO_ENABLED=true               # 微博热搜
HN_ENABLED=true                  # Hacker News
ZHIHU_ENABLED=true               # 知乎热榜

# 各数据源条目数量
NEWS_LIMIT=10
WEIBO_LIMIT=3
HN_LIMIT=3
ZHIHU_LIMIT=3

# 调度时间（UTC）
SCHEDULE_TIME=08:00
```

## Notion Database 创建说明

1. 在 Notion 中创建一个 Database（表格视图即可），命名为 `Daily Brief`
2. 确认存在以下属性（字段）：
   - `Name`：类型为 **Title**（标题）
   - `Date`：类型为 **Date**
   - `News Count`：类型为 **Number**
   - `GitHub Count`：类型为 **Number**
3. 复制该数据库的 ID（在浏览器地址栏 URL 中可找到），填入 `.env` 的 `NOTION_DATABASE_ID`

## 运行方式

```bash
python main.py
```

脚本启动后会：
- 立即执行一次「生成今日 Daily Brief」
- 然后使用 `schedule` 在配置的时间（默认 UTC 08:00）再自动执行

## 定时执行示例

### 使用 cron（Linux 服务器）
```cron
0 8 * * * cd /path/to/daily-brief && /usr/bin/python main.py >> /var/log/daily_brief.log 2>&1
```

### 使用 GitHub Actions
```yaml
name: Daily Brief
on:
  schedule:
    - cron: "0 8 * * *"
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          AI_SUMMARY_ENABLED: "true"
```

## 常见错误排查

- **Notion API 报错**
  - 检查 `.env` 中的 `NOTION_TOKEN` 是否正确、是否有访问该数据库的权限
  - 检查 `NOTION_DATABASE_ID` 是否为对应数据库的 ID
  
- **GitHub Trending 为空**
  - 国内环境可能无法直接访问 github.com，建议配置代理或使用 `GITHUB_TRENDING_API`
  
- **微博/知乎数据为空**
  - 公开 API 可能存在限流，程序会自动尝试备用 API
  - 可通过设置 `WEIBO_ENABLED=false` 等禁用特定数据源
  
- **AI 摘要不生效**
  - 确保 `DEEPSEEK_API_KEY` 已配置
  - 确保 `AI_SUMMARY_ENABLED=true`

## 更新日志

### v2.0.0 (2026-02)
- ✨ 新增微博热搜、Hacker News、知乎热榜数据源
- ✨ 新增 DeepSeek AI 智能摘要功能
- ♻️ 重构配置管理，集中管理所有配置项
- 🔧 添加自动重试机制，提高网络请求稳定性
- 📝 更新文档和环境变量示例
