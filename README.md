# Daily Brief（Notion 自动日报）

这是一个使用 Python 编写的自动化脚本项目，每天在 Notion 中自动生成一页「Daily Brief」，内容包含：

- 📰 当日热点新闻（最多 10 条，去重 + 简要摘要）
- ⭐ GitHub 当日 Trending 项目（最多 10 个，按当日 star 排序）

目标是：**信息密度高、形式克制、每天只一页、方便长期回顾**。

## 功能说明

- 从 GitHub Trending（自定义 API 或直接抓取 github.com/trending）获取热门仓库。
- 从多个国内 RSS 源获取新闻热点（当前默认：IT 之家 / 36氪快讯 / 观察者网，可按需替换）。
- 使用标题相似度做去重，只保留同一事件的一条。
- 每天在 Notion 的 `Daily Brief` 数据库中**只创建一条**记录：
  - 若当天已存在，则直接跳过，避免重复创建。
  - 固定页面 Block 结构，便于长期浏览。
- 可通过 `schedule` 常驻运行，也可用 cron / GitHub Actions 定时触发。

## 工程结构
```
daily-brief/
├─ main.py
├─ github_trending.py
├─ news_fetcher.py
├─ notion_writer.py
├─ utils.py
├─ .env.example
├─ requirements.txt
└─ README.md
```

## 安装步骤

1）准备 Python 环境：Python 3.10+，并确认已安装 `pip`。  
2）安装依赖：
```bash
pip install -r requirements.txt
```
3）复制环境变量配置：
```bash
cp .env.example .env  # Windows 请手动复制
```
然后在 `.env` 中填写：
```
NOTION_TOKEN=secret_xxx          # Notion 集成的 Token
NOTION_DATABASE_ID=xxxx          # Daily Brief 数据库 ID
GITHUB_TRENDING_API=             # 可选：配置国内的 GitHub Trending 代理 API，留空则直接抓取 github.com/trending
BAIDU_FANYI_APP_ID=              # 可选：百度翻译开放平台的 APP ID（用于翻译 GitHub 描述）
BAIDU_FANYI_SECRET=              # 可选：百度翻译开放平台的密钥

# GitHub Actions 运行时请在仓库 Secrets 中配置：
# NOTION_TOKEN
# NOTION_DATABASE_ID
# GITHUB_TRENDING_API           （可选）
# BAIDU_FANYI_APP_ID            （可选）
# BAIDU_FANYI_SECRET            （可选）
```

## Notion Database 创建说明

1. 在 Notion 中创建一个 Database（表格视图即可），命名为 `Daily Brief`。  
2. 确认存在以下属性（字段）：
   - `Name`：类型为 **Title**（标题）
   - `Date`：类型为 **Date**
   - `News Count`：类型为 **Number**
   - `GitHub Count`：类型为 **Number**
3. 复制该数据库的 ID（在浏览器地址栏 URL 中可找到），填入 `.env` 的 `NOTION_DATABASE_ID`。

## 运行方式

```bash
python main.py
```
脚本启动后会：

- 立即执行一次「生成今日 Daily Brief」；
- 然后使用 `schedule` 在 **每天 UTC 时间 08:00** 再自动执行一次。

如果你只打算用 cron / GitHub Actions 调用一次，可以把 `main.py` 中的循环改为只调用 `generate_daily_brief()` 一次后退出。

## 定时执行示例

### 使用 cron（Linux 服务器）

示例：每天 UTC 08:00 执行：
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
          GITHUB_TRENDING_API: ${{ secrets.GITHUB_TRENDING_API }}
```

## 常见错误排查

- **Notion API 报错**
  - 检查 `.env` 中的 `NOTION_TOKEN` 是否正确、是否有访问该数据库的权限。
  - 检查 `NOTION_DATABASE_ID` 是否为对应数据库的 ID。
- **GitHub Trending 为空**
  - 若你在国内环境，直接访问 `github.com/trending` 可能不稳定，建议：
    - 给系统 / 终端配置代理，或
    - 自己搭一个 GitHub Trending 代理 API，并在 `.env` 中配置 `GITHUB_TRENDING_API`。
- **新闻列表为空**
  - 可能是 IT 之家 RSS 源暂时不可用，可以稍后再试，或在 `news_fetcher.py` 中把 `RSS_URL` 换成你常用资讯站的 RSS 地址。
- **出现多条当天页面**
  - 请确认数据库中存在 `Date` 字段，并且类型为 Date。
- **使用 cron / GitHub Actions 时脚本不退出**
  - 若只需要执行一次，请删除 `main.py` 中的 `schedule` 部分和死循环，只保留 `generate_daily_brief()` 调用。


