# -*- coding: utf-8 -*-
"""
微博热搜抓取模块
使用公开 API 获取微博热搜榜数据
"""
from typing import List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import config
from utils import logger


# 微博热搜 API（从配置获取）
WEIBO_API_URL = config.weibo_api_url
# 备用 API
WEIBO_API_BACKUP = config.weibo_api_backup


@retry(
    stop=stop_after_attempt(config.retry.max_attempts),
    wait=wait_exponential(min=config.retry.wait_min, max=config.retry.wait_max),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _http_get(url: str, **kwargs) -> requests.Response:
    """带重试的 HTTP GET 请求"""
    # 添加默认 UA 模拟浏览器
    headers = kwargs.get("headers", {})
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    kwargs["headers"] = headers

    resp = requests.get(url, timeout=config.request_timeout, **kwargs)
    resp.raise_for_status()
    return resp


def _fetch_from_official() -> List[Dict]:
    """从 apihz API 获取热搜"""
    try:
        resp = _http_get(WEIBO_API_URL)
        data = resp.json()
        
        # 新格式：{"code": 200, "data": [...]}
        if data.get("code") != 200:
            logger.warning("微博主 API 返回非 200 code: %s", data.get("code"))
            return []
        
        items = []
        for idx, item in enumerate(data.get("data", []), start=1):
            title = item.get("title", "")
            if not title:
                continue
            items.append({
                "title": title,
                "hot": idx,  # 使用排名作为热度
                "url": item.get("scheme", f"https://s.weibo.com/weibo?q=%23{title}%23"),
                "category": "",
                "is_hot": False,
                "is_new": False,
            })
        return items
    except Exception as exc:  # noqa: BLE001
        logger.warning("微博主 API 请求失败: %s，尝试备用 API", exc)
        return []


def _fetch_from_backup() -> List[Dict]:
    """从备用 API (oioweb) 获取热搜"""
    try:
        resp = _http_get(WEIBO_API_BACKUP)
        data = resp.json()
        
        items = []
        for item in data.get("result", []):
            title = item.get("word", "")
            if not title:
                continue
            items.append({
                "title": title,
                "hot": item.get("hot", 0),
                "url": f"https://s.weibo.com/weibo?q=%23{title}%23",
                "category": "",
                "is_hot": False,
                "is_new": False,
            })
        return items
    except Exception as exc:  # noqa: BLE001
        logger.error("微博备用 API 也请求失败: %s", exc)
        return []


def fetch_weibo(limit: int | None = None) -> List[Dict]:
    """
    获取微博热搜榜
    
    Args:
        limit: 返回条目数量，默认使用配置值
    
    Returns:
        热搜列表，每项包含 title, hot, url, category 等字段
    """
    if limit is None:
        limit = config.weibo_limit
    
    if not config.weibo_enabled:
        logger.info("微博热搜已禁用")
        return []
    
    # 优先使用官方 API，失败则使用备用
    items = _fetch_from_official()
    if not items:
        items = _fetch_from_backup()
    
    logger.info("获取到 %d 条微博热搜", len(items))
    return items[:limit]
