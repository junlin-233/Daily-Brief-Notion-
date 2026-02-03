import hashlib
import logging
import os
import random
from datetime import datetime
from typing import List, Dict

import requests
from dotenv import load_dotenv

from config import config


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


def baidu_translate(text: str) -> str:
    """
    使用百度翻译开放平台将英文描述翻译为中文：
    - 需要在 .env 中配置 BAIDU_FANYI_APP_ID 和 BAIDU_FANYI_SECRET
    - 如果未配置或调用失败，则直接返回英文原文
    """
    app_id = config.baidu_fanyi_app_id
    secret = config.baidu_fanyi_secret
    if not app_id or not secret or not text:
        return text

    api = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    salt = str(random.randint(100000, 999999))
    sign_src = app_id + text + salt + secret
    sign = hashlib.md5(sign_src.encode("utf-8")).hexdigest()

    params = {
        "q": text,
        "from": "en",
        "to": "zh",
        "appid": app_id,
        "salt": salt,
        "sign": sign,
    }

    try:
        resp = requests.get(api, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if "trans_result" in data and data["trans_result"]:
            dst = data["trans_result"][0].get("dst", "")
            return dst or text
        return text
    except Exception as exc:  # noqa: BLE001
        logger.warning("百度翻译失败: %s", exc)
        return text

