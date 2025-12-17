# Daily Brief（Notion 自动日报）

这是一个使用 Python 编写的自动化脚本项目，每天在 Notion 中自动生成一页「Daily Brief」，内容包含：

- 📰 当日热点新闻（最多 10 条，去重 + 简要摘要）
- ⭐ GitHub 当日 Trending 项目（最多 10 个，按当日 star 排序）- ⭐ GitHub's trending projects of the day (up to 10, sorted by stars gained on that day)

目标是：**信息密度高、形式克制、每天只一页、方便长期回顾**。

## 功能说明

- 从 GitHub Trending（自定义 API 或直接抓取 github.com/trending）获取热门仓库。Fetch popular repositories from GitHub Trending (either through a custom API or by directly scraping github.com/trending).Fetch popular repositories from GitHub Trending (either through a custom API or by directly scraping github.com/trending). Fetch popular repositories from GitHub Trending (either through a custom API or by directly scraping github.com/trending).
- 从多个国内 RSS 源获取新闻热点。
- 使用标题相似度做去重，只保留同一事件的一条。
- 每天在 Notion 的 `Daily Brief` 数据库中**只创建一条**记录：Create only one record in the `Daily Brief` database of Notion every day:Create only one record in the `Daily Brief   日常简短` database of Notion every day:
  - 若当天已存在，则直接跳过，避免重复创建。
  - 固定页面 Block 结构，便于长期浏览。
- 可通过 `schedule` 常驻运行，也可用 cron / GitHub Actions 定时触发。It can be run persistently via `schedule`, or triggered at regular intervals using cron / GitHub Actions.可以通过 `schedule   时间表` 常驻运行，也可以用 cron 或 GitHub Actions 定时触发。

## 工程结构
```
daily-brief/   每日简讯/   daily-brief / Daily Briefing /
├─ main.py
├─ github_trending.py
├─ news_fetcher.py
├─ notion_writer.py
├─ utils.py
├─ .env
├─ requirements.txt
└─ README.md
```

## 安装步骤

1）准备 Python 环境：Python 3.10+，并确认已安装 `pip`。  1) Prepare the Python environment: Python 3.10, and confirm that `pip` has been installed.1) 准备 Python 环境：Python 3.10，并确认已安装 `pip   皮普`。
2）安装依赖：
```bash   ”“bash   ”“bash”“bash
pip install -r requirements.txt运行命令 `pip install -r requirements.txt` 以安装所需的包。Run the command `pip install -r requirements.txt` to install the required packages.
```
3）复制环境变量配置：
```bash   ”“bash   ”“bash”“bash
cp .env.example .env  # Windows 请手动复制Copy `.env.example` to `.env`  # Please copy manually on Windows复制 `.env.example` 文件为 `.env`  # Windows 系统请手动复制
```
然后在 `.env` 中填写：
```
NOTION_TOKEN=secret_xxx          # Notion 集成的 TokenNOTION_TOKEN=secret_xxx 
NOTION_TOKEN=secret_xxx  # 用于 Notion 集成的令牌
NOTION_DATABASE_ID=xxxx          # Daily Brief 数据库 IDNOTION_DATABASE_ID=xxxx         
NOTION_DATABASE_ID=xxxx          # Daily Brief 数据库的 ID
GITHUB_TRENDING_API=             # 可选：配置国内的 GitHub Trending 代理 API，留空则直接抓取 github.com/trendingGITHUB_TRENDING_API=           
BAIDU_FANYI_APP_ID=              # 可选：百度翻译开放平台的 APP ID（用于翻译 GitHub 描述）BAIDU_FANYI_APP_ID=              
BAIDU_FANYI_SECRET=              # 可选：百度翻译开放平台的密钥BAIDU_FANYI_SECRET=              

# GitHub Actions 运行时请在仓库 Secrets 中配置：When running GitHub Actions, please configure the following in the repository's Secrets:
# NOTION_TOKEN
# NOTION_DATABASE_ID   # NOTION 数据库 ID
# GITHUB_TRENDING_API           （可选）# GITHUB_TRENDING_API (Optional)
# BAIDU_FANYI_APP_ID            （可选）# BAIDU_FANYI_APP_ID (Optional)
# BAIDU_FANYI_SECRET            （可选）# BAIDU_FANYI_SECRET (optional)
```

## Notion Database 创建说明   
1. 在 Notion 中创建一个 Database（表格视图即可），命名为 `Daily Brief`。  
2. 确认存在以下属性（字段）：
   - `Name   名字`：类型为 **Title**  
   - `Date`：类型为 **Date**
   - `News Count`：类型为 **Number**
   - `GitHub Count`：类型为 **Number**
3. 复制该数据库的 ID（在浏览器地址栏 URL 中可找到），填入 `.env` 的 `NOTION_DATABASE_ID`。3. Copy the ID of this database (which can be found in the URL of the browser's address bar) and fill it into `NOTION_DATABASE_ID` in the `.env` file.

## 运行方式

```bash   ”“bash
python main.py
```
脚本启动后会：

立即执行一次「生成今日 Daily Brief」；

## 定时执行示例

### 使用 cron（Linux 服务器）   

示例：每天 UTC 08:00 执行：
```cron   “‘cron   “”cron的cron
0 8 * * * cd /path/to/daily-brief && /usr/bin/python main.py >> /var/log/daily_brief.log 2>&1每晚 0 点 8 分，切换到 /path/to/daily-brief 目录，然后使用 /usr/bin/python 运行 main.py 脚本，并将输出重定向到 /var/log/daily_brief.log 文件中，同时将错误输出重定向到标准输出。At 0:08 every night, switch to the /path/to/daily-brief directory and run the main.py script using /usr/bin/python. Redirect the output to the /var/log/daily_brief.log file and also redirect the error output to the standard output.
```

### 使用 GitHub Actions  

```yaml   “‘yaml
name: Daily Brief   名称：每日简报Name: Daily BriefName: Daily Brief
on:   :   ::
  schedule:   时间表:
    - cron: "0 8 * * *"- cron：“0 8”- 定时任务：每天 8 点整执行
- 定时任务：每小时 8 分钟执行
jobs:   工作:
  run:   运行:
    runs-on: ubuntu-latest   运行于：ubuntu-latest运行于：ubuntu-latest
    steps:   步骤:
      - uses: actions/checkout@v4- 使用：actions/checkout@v4
      - uses: actions/setup-python@v5- 使用：actions/setup-python@v5
        with:   :
          python-version: '3.11'   Python 版本：'3.1
      - run: pip install -r requirements.txt运行：pip install -r requirements.txt
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








