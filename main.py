import time

import schedule

from github_trending import get_github_trending
from news_fetcher import fetch_news
from notion_writer import (
    NotionClient,
    build_news_blocks,
    build_trending_blocks,
)
from utils import logger, deduplicate_items


def generate_daily_brief() -> None:
    logger.info("开始执行 Daily Brief 任务")
    notion = NotionClient()

    if notion.find_today_page():
        logger.info("今天的 Notion 页面已存在，本次跳过。")
        return

    # 多取一些，便于去重后仍然能有足够数量
    news = fetch_news(limit=20)
    news = deduplicate_items(news, title_key="title", threshold=0.5, limit=10)
    trending = get_github_trending(limit=10)

    news_blocks = build_news_blocks(news)
    trending_blocks = build_trending_blocks(trending)

    logger.info("准备创建 Notion 页面：新闻 %s 条，GitHub 项目 %s 个", len(news), len(trending))
    try:
        page_id = notion.create_page(news_count=len(news), gh_count=len(trending))
        notion.append_blocks(page_id, news_blocks + trending_blocks)
        logger.info("Daily Brief 页面创建成功，页面 ID: %s", page_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("写入 Notion 失败: %s", exc)


def main() -> None:
    # 立即执行一次（方便调试 / cron），并在 UTC 08:00 每日调度
    generate_daily_brief()
    schedule.every().day.at("08:00").do(generate_daily_brief)
    logger.info("调度器已启动，等待下一次执行。")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()

