import hashlib
import logging
import os
from datetime import datetime
from typing import List, Dict

from dotenv import load_dotenv


load_dotenv()


def setup_logger() -> logging.Logger:
    """配置基础日志记录器。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    return logging.getLogger("daily_brief")


logger = setup_logger()


def get_env(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    if not value:
        logger.warning("环境变量 %s 未设置，将使用默认值。", key)
    return value


def today_date_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def simple_normalize(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum() or ch.isspace()).strip()


def title_similarity(a: str, b: str) -> float:
    """基于分词集合的 Jaccard 相似度，用于轻量级去重。"""
    sa = set(simple_normalize(a).split())
    sb = set(simple_normalize(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def deduplicate_items(items: List[Dict], title_key: str, threshold: float = 0.5, limit: int = 8) -> List[Dict]:
    """
    Deduplicate list of dicts based on title similarity.
    Keeps order and truncates to limit.
    """
    deduped: List[Dict] = []
    for item in items:
        title = item.get(title_key, "")
        if any(title_similarity(title, existing.get(title_key, "")) >= threshold for existing in deduped):
            continue
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def stable_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

