# -*- coding: utf-8 -*-
"""
知乎热榜抓取模块
使用公开 API 获取知乎热榜数据
"""
from typing import List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import config
from utils import logger


# 知乎热榜 API（从配置获取）
ZHIHU_API_URL = config.zhihu_api_url
# 备用 API
ZHIHU_API_BACKUP = config.zhihu_api_backup


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
    # 确保 Accept 头存在
    if "Accept" not in headers:
        headers["Accept"] = "application/json"
    kwargs["headers"] = headers
    
    resp = requests.get(url, timeout=config.request_timeout, **kwargs)
    resp.raise_for_status()
    return resp


def _fetch_from_official() -> List[Dict]:
    """从 aa1.cn API 获取热榜"""
    try:
        resp = _http_get(ZHIHU_API_URL)
        data = resp.json()
        
        # 新格式：{"date": "...", "news": [...]}
        items = []
        for item in data.get("news", []):
            title = item.get("title", "")
            if not title:
                continue
            
            items.append({
                "title": title,
                "hot": "",
                "url": item.get("url", ""),
                "excerpt": "",
                "answer_count": 0,
            })
        return items
    except Exception as exc:  # noqa: BLE001
        logger.warning("知乎主 API 请求失败: %s，尝试备用 API", exc)
        return []


def _fetch_from_backup() -> List[Dict]:
    """从备用 API (oioweb) 获取热榜"""
    try:
        resp = _http_get(ZHIHU_API_BACKUP)
        data = resp.json()
        
        items = []
        for item in data.get("result", []):
            title = item.get("title", "")
            if not title:
                continue
            items.append({
                "title": title,
                "hot": item.get("hot", ""),
                "url": f"https://www.zhihu.com/question/{item.get('id', '')}",
                "excerpt": "",
                "answer_count": 0,
            })
        return items
    except Exception as exc:  # noqa: BLE001
        logger.error("知乎备用 API 也请求失败: %s", exc)
        return []


def fetch_zhihu(limit: int | None = None) -> List[Dict]:
    """
    获取知乎热榜
    
    Args:
        limit: 返回条目数量，默认使用配置值
    
    Returns:
        热榜列表，每项包含 title, hot, url, excerpt 等字段
    """
    if limit is None:
        limit = config.zhihu_limit
    
    if not config.zhihu_enabled:
        logger.info("知乎热榜已禁用")
        return []
    
    # 优先使用官方 API，失败则使用备用
    items = _fetch_from_official()
    if not items:
        items = _fetch_from_backup()
    
    logger.info("获取到 %d 条知乎热榜", len(items))
    return items[:limit]
