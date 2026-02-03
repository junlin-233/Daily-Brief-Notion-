import time
import os

import schedule

from config import config
from github_trending import get_github_trending
from news_fetcher import fetch_news
from weibo_fetcher import fetch_weibo
from hn_fetcher import fetch_hn
from zhihu_fetcher import fetch_zhihu
from ai_summarizer import summarize_news_list, translate_to_chinese
from notion_writer import (
    NotionClient,
    build_news_blocks,
    build_trending_blocks,
    build_weibo_blocks,
    build_hn_blocks,
    build_zhihu_blocks,
)
from utils import logger, deduplicate_items, baidu_translate


def generate_daily_brief() -> None:
    logger.info("开始执行 Daily Brief 任务")
    notion = NotionClient()

    if notion.find_today_page():
        logger.info("今天的 Notion 页面已存在，本次跳过。")
        return

    # ===== 获取各数据源 =====
    
    # 新闻（多取一些用于去重）
    news = fetch_news(limit=20)
    news = deduplicate_items(news, title_key="title", threshold=0.5, limit=config.news_limit)
    # 可选：AI 摘要
    news = summarize_news_list(news)
    
    # GitHub Trending
    trending = get_github_trending()
    # 可选：翻译描述
    if config.ai_summary_enabled:
        for item in trending:
            if item.get("description"):
                item["description"] = translate_to_chinese(item["description"])
    
    # 微博热搜
    weibo = fetch_weibo() if config.weibo_enabled else []
    
    # Hacker News
    hn = fetch_hn() if config.hn_enabled else []
    
    # 尝试翻译 HN 标题（优先使用百度翻译，回退到 AI 翻译）
    if hn:
        for item in hn:
            title = item.get("title", "")
            if not title:
                continue
            
            # 1. 尝试百度翻译
            trans = baidu_translate(title)
            if trans and trans != title:
                item["title_zh"] = trans
                continue
                
            # 2. 尝试 AI 翻译
            if config.ai_summary_enabled:
                item["title_zh"] = translate_to_chinese(title)
    
    # 知乎热榜
    zhihu = fetch_zhihu() if config.zhihu_enabled else []

    # ===== 构建 Notion 区块 =====
    news_blocks = build_news_blocks(news)
    trending_blocks = build_trending_blocks(trending)
    weibo_blocks = build_weibo_blocks(weibo)
    hn_blocks = build_hn_blocks(hn)
    zhihu_blocks = build_zhihu_blocks(zhihu)
    
    all_blocks = (
        news_blocks 
        + weibo_blocks 
        + hn_blocks 
        + zhihu_blocks
        + trending_blocks 
    )

    # ===== 统计数量 =====
    total_news = len(news)
    total_gh = len(trending)
    
    logger.info(
        "准备创建 Notion 页面：新闻 %d 条，GitHub %d 个，微博 %d 条，HN %d 条，知乎 %d 条",
        total_news, total_gh, len(weibo), len(hn), len(zhihu)
    )
    
    try:
        page_id = notion.create_page(news_count=total_news, gh_count=total_gh)
        notion.append_blocks(page_id, all_blocks)
        logger.info("Daily Brief 页面创建成功，页面 ID: %s", page_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("写入 Notion 失败: %s", exc)


def main() -> None:
    # 立即执行一次（方便调试 / cron），并在每日调度
    generate_daily_brief()
    schedule.every().day.at(config.schedule_time).do(generate_daily_brief)
    logger.info("调度器已启动，将在每天 %s 执行。", config.schedule_time)
    
    # 如果是在 CI 环境或指定了只运行一次，则退出
    if os.getenv("CI") or os.getenv("RUN_ONCE"):
        logger.info("检测到 CI 环境或 RUN_ONCE，任务执行完毕，退出调度器。")
        return

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
