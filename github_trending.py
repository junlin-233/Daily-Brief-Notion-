import re
import html
from typing import List, Dict

import requests

from utils import logger, get_env
import hashlib
import random


def _translate_to_zh(text: str) -> str:
    """
    使用百度翻译开放平台将英文描述翻译为中文（可选）：
    - 需要在 .env 中配置：
        BAIDU_FANYI_APP_ID
        BAIDU_FANYI_SECRET
    - 如果未配置或调用失败，则直接返回英文原文。
    """
    app_id = get_env("BAIDU_FANYI_APP_ID", "").strip()
    secret = get_env("BAIDU_FANYI_SECRET", "").strip()
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
        resp = requests.get(api, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "trans_result" in data and data["trans_result"]:
            dst = data["trans_result"][0].get("dst", "")
            return dst or text
        return text
    except Exception as exc:  # noqa: BLE001
        logger.error("GitHub 描述百度翻译失败，使用原文: %s", exc)
        return text


def fetch_trending_via_api(api_url: str) -> List[Dict]:
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = []
        for item in data[:20]:
            items.append(
                {
                    "repo_name": item.get("name") or item.get("repo_name") or "",
                    "description": item.get("description", "") or "",
                    "language": item.get("language", "") or "",
                    "stars_today": item.get("stars_today")
                    or item.get("stars")  # some APIs use "stars"
                    or 0,
                    "repo_url": item.get("url") or item.get("repo_url") or "",
                }
            )
        return items
    except Exception as exc:  # noqa: BLE001
        logger.error("GitHub Trending API 调用失败: %s", exc)
        return []


TRENDING_URL = "https://github.com/trending"


def fetch_trending_via_scrape() -> List[Dict]:
    headers = {"User-Agent": "daily-brief-bot"}
    try:
        resp = requests.get(TRENDING_URL, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.error("GitHub Trending 页面抓取失败: %s", exc)
        return []

    page_html = resp.text
    # 使用简单正则解析，避免额外依赖（足够应对 Trending 页）
    repo_blocks = re.findall(r"<article[\s\S]*?<\/article>", page_html)
    items: List[Dict] = []
    for block in repo_blocks:
        # 仓库链接（用于 URL）
        href_match = re.search(r'href="(/[^"]+)"', block)
        # 仓库名（a 标签内的纯文本）
        name_text_match = re.search(r"<h2[^>]*>\s*<a[^>]*>(.*?)</a>", block, re.S)
        stars_today_match = re.search(r"(\d+,?\d*)\s+stars\s+today", block)
        desc_match = re.search(r'<p[^>]*>(.*?)<\/p>', block, re.S)
        lang_match = re.search(r'programmingLanguage">([\w\+#]+)<', block)

        if not href_match or not name_text_match:
            continue

        href_path = href_match.group(1)  # e.g. /owner/repo
        repo_url = f"https://github.com{href_path}"

        # 提取 a 标签里的文本作为仓库名，例如 "owner / repo"
        raw_name = name_text_match.group(1)
        name_no_tag = re.sub(r"<.*?>", "", raw_name)
        name_no_tag = html.unescape(name_no_tag)
        repo_name = re.sub(r"\s+", " ", name_no_tag).strip()

        # description 里可能带有复杂 HTML，先去标签再压缩空白，并截断长度
        if desc_match:
            raw_desc = desc_match.group(1)
            # 去掉所有 HTML 标签，只保留纯文本
            no_tag = re.sub(r"<.*?>", "", raw_desc)
            no_tag = html.unescape(no_tag)
            description = re.sub(r"\s+", " ", no_tag).strip()
            if len(description) > 200:
                description = description[:197] + "..."
            # 可选：翻译为中文
            description = _translate_to_zh(description)
        else:
            description = ""

        language = lang_match.group(1) if lang_match else ""
        stars_today = (
            int(stars_today_match.group(1).replace(",", ""))
            if stars_today_match
            else 0
        )

        items.append(
            {
                "repo_name": repo_name,
                "description": description,
                "language": language,
                "stars_today": stars_today,
                "repo_url": repo_url,
            }
        )
    return items


def get_github_trending(limit: int = 8) -> List[Dict]:
    """
    获取 GitHub Trending：
    - 若 .env 中配置了 GITHUB_TRENDING_API，则优先使用该国内代理 / API；
    - 否则直接抓取 GitHub 官方 Trending 页面（需要能够访问 github.com）。
    """
    api_url = get_env("GITHUB_TRENDING_API", "").strip()
    if api_url:
        items = fetch_trending_via_api(api_url)
    else:
        items = fetch_trending_via_scrape()
    # Sort by stars_today desc and truncate
    items_sorted = sorted(items, key=lambda x: x.get("stars_today", 0), reverse=True)
    return items_sorted[:limit]

