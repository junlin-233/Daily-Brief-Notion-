import re
import xml.etree.ElementTree as ET
from typing import List, Dict

import requests

from utils import logger, deduplicate_items, title_similarity


# 三个国内 RSS 源，分别取 3、3、4 条组合成 10 条
RSS_SOURCES = [
    ("IT之家", "https://www.ithome.com/rss/"),  # 科技 / 数码
    ("瓦斯", "https://rss.aishort.top/?type=wasi"),  # 创业 / 商业快讯
    ("百度", "https://rss.aishort.top/?type=baidu"),  # 时政 / 热点
]


def _clean_text(text: str) -> str:
    text = re.sub(r"<.*?>", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fetch_single_rss(source_name: str, url: str, limit: int) -> List[Dict]:
    """从单个 RSS 源抓取若干条新闻。"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
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


def fetch_news(limit: int = 10) -> List[Dict]:
    """
    全局去重时，先保证每个源至少拿到 N 条，再补足到 limit：
    """
    per_source_quota = [4, 3, 3]
    selected: List[Dict] = []
    leftovers: List[Dict] = []

    for idx, (name, url) in enumerate(RSS_SOURCES):
        quota = per_source_quota[idx] if idx < len(per_source_quota) else 0
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

