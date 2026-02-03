import time
from datetime import datetime
from typing import List, Dict

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import config
from utils import logger, today_date_str


NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Notion 对单个 rich_text 的 content 长度限制为 2000 字符，这里留一点余量
MAX_TEXT_LENGTH = 1800


def _is_rate_limited(exc: BaseException) -> bool:
    """检查是否为 Notion 限流错误 (429)"""
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code == 429
    return False


class NotionClient:
    def __init__(self) -> None:
        self.token = config.notion_token
        self.database_id = config.notion_database_id
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )

    @retry(
        stop=stop_after_attempt(config.retry.max_attempts),
        wait=wait_exponential(min=config.retry.wait_min, max=config.retry.wait_max),
        retry=retry_if_exception(_is_rate_limited),
        reraise=True,
    )
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            resp = self.session.request(method, url, timeout=30, **kwargs)
            if not resp.ok:
                # 打印 Notion 返回的原始响应，方便排查 400 的具体原因
                try:
                    logger.error("Notion 响应内容: %s", resp.text)
                except Exception:  # noqa: BLE001
                    logger.error("Notion 响应内容无法打印。")
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001
            logger.error("Notion API 调用出错 %s %s: %s", method, url, exc)
            raise

    def find_today_page(self) -> str | None:
        today = today_date_str()
        payload = {
            "filter": {
                "property": "Date",
                "date": {"equals": today},
            },
            "page_size": 1,
        }
        url = f"{NOTION_BASE_URL}/databases/{self.database_id}/query"
        resp = self._request("POST", url, json=payload)
        results = resp.json().get("results", [])
        if results:
            return results[0]["id"]
        return None

    def create_page(self, news_count: int, gh_count: int) -> str:
        title = today_date_str()
        url = f"{NOTION_BASE_URL}/pages"
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title,
                            }
                        }
                    ]
                },
                "Date": {"date": {"start": title}},
                "News Count": {"number": news_count},
                "GitHub Count": {"number": gh_count},
            },
            "children": build_initial_blocks(news_count, gh_count),
        }
        resp = self._request("POST", url, json=payload)
        return resp.json()["id"]

    def append_blocks(self, page_id: str, blocks: List[Dict]) -> None:
        if not blocks:
            return
        url = f"{NOTION_BASE_URL}/blocks/{page_id}/children"
        for i in range(0, len(blocks), 50):
            chunk = blocks[i : i + 50]
            self._request("PATCH", url, json={"children": chunk})


def _trim_content(content: str) -> str:
    """裁剪文本，确保不超过 Notion 的单段落长度限制。"""
    if len(content) <= MAX_TEXT_LENGTH:
        return content
    # 预留 1 个字符放省略号
    return content[: MAX_TEXT_LENGTH - 1] + "…"


def text_block(content: str) -> Dict:
    safe_content = _trim_content(content)
    return {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": safe_content}}],
        },
    }


def link_block(label: str, url: str) -> Dict:
    """
    创建一个整行可点击的链接段落。
    如果 url 为空，则退化为普通文本段落。
    """
    if not url:
        return text_block(label)
    safe_label = _trim_content(label)
    return {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": safe_label,
                        "link": {"url": url},
                    },
                }
            ]
        },
    }

def divider_block() -> Dict:
    return {"type": "divider", "divider": {}}


def build_initial_blocks(news_count: int, gh_count: int) -> List[Dict]:
    today = today_date_str()
    return [
        text_block(f"📅 {today} · Daily Brief"),
        divider_block(),
        text_block("📰 今日热点"),
        divider_block(),
    ]


def build_news_blocks(news_list: List[Dict]) -> List[Dict]:
    blocks: List[Dict] = []
    for idx, item in enumerate(news_list, start=1):
        title = item.get("title", "")
        source = item.get("source", "")
        summary = item.get("summary", "")
        url = item.get("url", "")
        blocks.append(text_block(f"{idx}. {title}"))
        blocks.append(text_block(f"   - {source}｜{summary}"))
        blocks.append(link_block("   - 🔗 原文链接", url))
    return blocks


def build_trending_blocks(trending: List[Dict]) -> List[Dict]:
    blocks: List[Dict] = [
        divider_block(),
        text_block("⭐ GitHub Trending"),
        divider_block(),
    ]
    for idx, item in enumerate(trending, start=1):
        repo = item.get("repo_name", "")
        desc = item.get("description", "")
        lang = item.get("language", "") or "Unknown"
        stars = item.get("stars_today", 0)
        url = item.get("repo_url", "")
        blocks.append(text_block(f"{idx}. {repo}"))
        blocks.append(text_block(f"   - {desc}"))
        blocks.append(text_block(f"   - ⭐ +{stars} today | {lang}"))
        blocks.append(link_block("   - 🔗 GitHub 链接", url))
    return blocks


def build_weibo_blocks(weibo_list: List[Dict]) -> List[Dict]:
    """构建微博热搜区块"""
    if not weibo_list:
        return []
    blocks: List[Dict] = [
        divider_block(),
        text_block("🔥 微博热搜"),
        divider_block(),
    ]
    for idx, item in enumerate(weibo_list, start=1):
        title = item.get("title", "")
        url = item.get("url", "")
        blocks.append(text_block(f"{idx}. {title}"))
        blocks.append(link_block("   - 🔗 查看详情", url))
    return blocks


def build_hn_blocks(hn_list: List[Dict]) -> List[Dict]:
    """构建 Hacker News 区块"""
    if not hn_list:
        return []
    blocks: List[Dict] = [
        divider_block(),
        text_block("📰 Hacker News"),
        divider_block(),
    ]
    for idx, item in enumerate(hn_list, start=1):
        # 优先使用翻译后的标题
        title = item.get("title_zh") or item.get("title", "")
        score = item.get("score", 0)
        comments = item.get("comments", 0)
        url = item.get("url", "")
        hn_url = item.get("hn_url", "")
        blocks.append(text_block(f"{idx}. {title}"))
        blocks.append(text_block(f"   - ⬆️ {score} points | 💬 {comments} comments"))
        blocks.append(link_block("   - 🔗 原文链接", url))
        if hn_url and hn_url != url:
            blocks.append(link_block("   - 🔗 HN 讨论", hn_url))
    return blocks


def build_zhihu_blocks(zhihu_list: List[Dict]) -> List[Dict]:
    """构建知乎热榜区块"""
    if not zhihu_list:
        return []
    blocks: List[Dict] = [
        divider_block(),
        text_block("💡 知乎热榜"),
        divider_block(),
    ]
    for idx, item in enumerate(zhihu_list, start=1):
        title = item.get("title", "")
        hot = item.get("hot", "")
        url = item.get("url", "")
        excerpt = item.get("excerpt", "")
        blocks.append(text_block(f"{idx}. {title}"))
        if excerpt:
            blocks.append(text_block(f"   - {excerpt[:50]}..."))
        if hot:
            blocks.append(text_block(f"   - 🔥 {hot}"))
        blocks.append(link_block("   - 🔗 查看问题", url))
    return blocks


