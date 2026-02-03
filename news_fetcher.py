import re
import html
import xml.etree.ElementTree as ET
from typing import List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import config
from utils import logger, deduplicate_items, title_similarity


def _clean_text(text: str) -> str:
    # 先去除HTML标签
    text = re.sub(r"<.*?>", "", text or "")
    # 解码HTML实体（如 &nbsp; &amp; 等）
    text = html.unescape(text)
    # 压缩空白字符
    text = re.sub(r"\s+", " ", text).strip()
    return text


@retry(
    stop=stop_after_attempt(config.retry.max_attempts),
    wait=wait_exponential(min=config.retry.wait_min, max=config.retry.wait_max),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _fetch_rss_request(url: str) -> requests.Response:
    """带重试的 HTTP 请求"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=config.request_timeout)
    resp.raise_for_status()
    return resp


def _fetch_single_rss(source_name: str, url: str, limit: int) -> List[Dict]:
    """从单个 RSS 源抓取若干条新闻。"""
    try:
        resp = _fetch_rss_request(url)
    except Exception as exc:  # noqa: BLE001
        logger.error("新闻 RSS 拉取失败（%s）: %s", source_name, exc)
        return []

    items: List[Dict] = []
    try:
        root = ET.fromstring(resp.text)
        for item in root.findall(".//item")[:limit]:
            title = _clean_text(item.findtext("title", default=""))
            link = item.findtext("link", default="")
            # 有些源没有 <source>，就用我们传入的源名
            source = _clean_text(item.findtext("source", default=source_name)) or source_name
            description = _clean_text(item.findtext("description", default=""))
            summary = description[:30]
            # 如果摘要以来源名开头，去掉重复的来源前缀
            prefix = f"{source} "
            if summary.startswith(prefix):
                summary = summary[len(prefix) :].lstrip("：:，, ")
            items.append(
                {
                    "title": title,
                    "source": source,
                    "url": link,
                    "summary": summary,
                }
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("新闻 RSS 解析失败（%s）: %s", source_name, exc)
        return []
    return items


def _is_duplicate(candidate: Dict, selected: List[Dict]) -> bool:
    """判断候选新闻标题是否与已选列表重复（基于标题相似度）。"""
    title = candidate.get("title", "")
    for item in selected:
        if title_similarity(title, item.get("title", "")) >= 0.5:
            return True
    return False


def fetch_news(limit: int | None = None) -> List[Dict]:
    """
    全局去重时，先保证每个源至少拿到 N 条，再补足到 limit：
    """
    if limit is None:
        limit = config.news_limit
    
    selected: List[Dict] = []
    leftovers: List[Dict] = []

    for rss_source in config.rss_sources:
        name, url, quota = rss_source.name, rss_source.url, rss_source.quota
        if quota <= 0:
            continue

        # 为该源多抓一些，再在本源内部去重
        raw_items = _fetch_single_rss(name, url, quota * 3)
        unique_in_source = deduplicate_items(
            raw_items, title_key="title", threshold=0.5, limit=quota * 3
        )

        # 先尽量选出 quota 条，优先避免与其他源重复；
        # 若可选的不够，就允许少量重复以保证每个源至少有 quota 条（前提是源本身有数据）。
        count = 0
        for item in unique_in_source:
            if not _is_duplicate(item, selected) or count < quota:
                selected.append(item)
                count += 1
            else:
                leftovers.append(item)
            if count >= quota:
                # 该源配额已满，其余进入候选池
                leftovers.extend(unique_in_source[unique_in_source.index(item) + 1 :])
                break
        else:
            # 没能凑齐 quota，剩余的也加入候选池
            leftovers.extend(unique_in_source[count:])

    # 若总数仍不足 limit，则从所有剩余候选中补足，严格避免重复
    for item in leftovers:
        if len(selected) >= limit:
            break
        if not _is_duplicate(item, selected):
            selected.append(item)

    # 最终截断为 limit 条
    return selected[:limit]

