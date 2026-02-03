import re
import html
import hashlib
import random
from typing import List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import config
from utils import logger, baidu_translate


@retry(
    stop=stop_after_attempt(config.retry.max_attempts),
    wait=wait_exponential(min=config.retry.wait_min, max=config.retry.wait_max),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _http_get(url: str, **kwargs) -> requests.Response:
    """带重试的 HTTP GET 请求"""
    resp = requests.get(url, timeout=config.request_timeout, **kwargs)
    resp.raise_for_status()
    return resp


def fetch_trending_via_api(api_url: str) -> List[Dict]:
    try:
        resp = _http_get(api_url)
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
        resp = _http_get(TRENDING_URL, headers=headers)
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
            description = baidu_translate(description)
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


def get_github_trending(limit: int | None = None) -> List[Dict]:
    """
    获取 GitHub Trending：
    - 若 .env 中配置了 GITHUB_TRENDING_API，则优先使用该国内代理 / API；
    - 否则直接抓取 GitHub 官方 Trending 页面（需要能够访问 github.com）。
    """
    if limit is None:
        limit = config.github_limit
    
    api_url = config.github_trending_api
    if api_url:
        items = fetch_trending_via_api(api_url)
    else:
        items = fetch_trending_via_scrape()
    # Sort by stars_today desc and truncate
    items_sorted = sorted(items, key=lambda x: x.get("stars_today", 0), reverse=True)
    return items_sorted[:limit]

