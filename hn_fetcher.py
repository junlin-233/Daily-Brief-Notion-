# -*- coding: utf-8 -*-
"""
Hacker News 热门帖子抓取模块
使用 HN 官方 Firebase API
"""
from typing import List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import config
from utils import logger


# Hacker News 官方 API
HN_API_BASE = config.hn_api_url.rstrip("/")
HN_TOP_STORIES = f"{HN_API_BASE}/topstories.json"
HN_ITEM_URL = f"{HN_API_BASE}/item"


@retry(
    stop=stop_after_attempt(config.retry.max_attempts),
    wait=wait_exponential(min=config.retry.wait_min, max=config.retry.wait_max),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _http_get(url: str) -> requests.Response:
    """带重试的 HTTP GET 请求"""
    resp = requests.get(url, timeout=config.request_timeout)
    resp.raise_for_status()
    return resp


def _get_item_detail(item_id: int) -> Dict | None:
    """获取单个帖子详情"""
    try:
        resp = _http_get(f"{HN_ITEM_URL}/{item_id}.json")
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("获取 HN 帖子 %d 失败: %s", item_id, exc)
        return None


def fetch_hn(limit: int | None = None) -> List[Dict]:
    """
    获取 Hacker News 热门帖子
    
    Args:
        limit: 返回条目数量，默认使用配置值
    
    Returns:
        帖子列表，每项包含 title, score, url, comments, author 等字段
    """
    if limit is None:
        limit = config.hn_limit
    
    if not config.hn_enabled:
        logger.info("Hacker News 已禁用")
        return []
    
    try:
        resp = _http_get(HN_TOP_STORIES)
        story_ids = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.error("获取 HN Top Stories 失败: %s", exc)
        return []
    
    # 多获取一些以防某些获取失败
    fetch_count = min(limit * 2, len(story_ids))
    items = []
    
    for story_id in story_ids[:fetch_count]:
        if len(items) >= limit:
            break
            
        detail = _get_item_detail(story_id)
        if not detail:
            continue
        
        title = detail.get("title", "")
        if not title:
            continue
        
        # HN 帖子可能是链接或者讨论帖
        url = detail.get("url", "")
        if not url:
            url = f"https://news.ycombinator.com/item?id={story_id}"
        
        items.append({
            "title": title,
            "score": detail.get("score", 0),
            "url": url,
            "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
            "comments": detail.get("descendants", 0),
            "author": detail.get("by", ""),
            "time": detail.get("time", 0),
        })
    
    logger.info("获取到 %d 条 Hacker News 帖子", len(items))
    return items[:limit]
