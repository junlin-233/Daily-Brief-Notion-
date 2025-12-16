from datetime import datetime
from typing import List, Dict

import requests

from utils import logger, get_env, today_date_str


NOTION_BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Notion 对单个 rich_text 的 content 长度限制为 2000 字符，这里留一点余量
MAX_TEXT_LENGTH = 1800


class NotionClient:
    def __init__(self) -> None:
        self.token = get_env("NOTION_TOKEN")
        self.database_id = get_env("NOTION_DATABASE_ID")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
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

