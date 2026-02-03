# -*- coding: utf-8 -*-
"""
Daily Brief 配置管理模块
集中管理所有配置项，支持环境变量覆盖
"""
import os
from dataclasses import dataclass, field
from typing import List, Tuple

from dotenv import load_dotenv

load_dotenv()


def _get_env(key: str, default: str = "") -> str:
    """获取环境变量，返回字符串"""
    return os.getenv(key, default).strip()


def _get_env_int(key: str, default: int) -> int:
    """获取环境变量，返回整数"""
    val = os.getenv(key, "").strip()
    if val.isdigit():
        return int(val)
    return default


def _get_env_bool(key: str, default: bool = False) -> bool:
    """获取环境变量，返回布尔值"""
    val = os.getenv(key, "").strip().lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    wait_min: float = 1.0
    wait_max: float = 10.0


@dataclass
class RSSSource:
    """RSS 数据源配置"""
    name: str
    url: str
    quota: int = 3


@dataclass
class Config:
    """全局配置"""
    
    # Notion 配置
    notion_token: str = field(default_factory=lambda: _get_env("NOTION_TOKEN"))
    notion_database_id: str = field(default_factory=lambda: _get_env("NOTION_DATABASE_ID"))
    
    # GitHub 配置
    github_trending_api: str = field(default_factory=lambda: _get_env("GITHUB_TRENDING_API"))
    github_limit: int = field(default_factory=lambda: _get_env_int("GITHUB_LIMIT", 10))
    
    # 百度翻译配置
    baidu_fanyi_app_id: str = field(default_factory=lambda: _get_env("BAIDU_FANYI_APP_ID"))
    baidu_fanyi_secret: str = field(default_factory=lambda: _get_env("BAIDU_FANYI_SECRET"))
    
    # DeepSeek AI 配置
    deepseek_api_key: str = field(default_factory=lambda: _get_env("DEEPSEEK_API_KEY"))
    deepseek_base_url: str = field(default_factory=lambda: _get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    ai_summary_enabled: bool = field(default_factory=lambda: _get_env_bool("AI_SUMMARY_ENABLED", False))
    
    # 新数据源开关
    weibo_enabled: bool = field(default_factory=lambda: _get_env_bool("WEIBO_ENABLED", True))
    hn_enabled: bool = field(default_factory=lambda: _get_env_bool("HN_ENABLED", True))
    zhihu_enabled: bool = field(default_factory=lambda: _get_env_bool("ZHIHU_ENABLED", True))
    
    # 各数据源条目数量
    news_limit: int = field(default_factory=lambda: _get_env_int("NEWS_LIMIT", 10))
    weibo_limit: int = field(default_factory=lambda: int(_get_env("WEIBO_LIMIT", "5")))
    hn_limit: int = field(default_factory=lambda: _get_env_int("HN_LIMIT", 5))
    zhihu_limit: int = field(default_factory=lambda: int(_get_env("ZHIHU_LIMIT", "5")))
    
    # HTTP 请求配置
    request_timeout: int = field(default_factory=lambda: _get_env_int("REQUEST_TIMEOUT", 10))
    
    # 重试配置
    retry: RetryConfig = field(default_factory=RetryConfig)
    
    # RSS 源配置
    rss_sources: List[RSSSource] = field(default_factory=lambda: [
        RSSSource("IT之家", "https://www.ithome.com/rss/", 3),
        RSSSource("36氪", "https://36kr.com/feed", 3),
        RSSSource("瓦斯", "https://rss.aishort.top/?type=wasi", 4),
    ])
    
    # API URL 配置（支持环境变量覆盖）
    weibo_api_url: str = field(default_factory=lambda: _get_env("WEIBO_API_URL", "https://cn.apihz.cn/api/xinwen/weibo.php?id=10012783&key=f9e75946dd5395dd1eb64a68ab594d6f").strip())
    weibo_api_backup: str = field(default_factory=lambda: _get_env("WEIBO_API_BACKUP", "https://api.oioweb.cn/api/common/weibo/hot").strip())
    
    hn_api_url: str = field(default_factory=lambda: _get_env("HN_API_URL", "https://hacker-news.firebaseio.com/v0").strip())
    
    zhihu_api_url: str = field(default_factory=lambda: _get_env("ZHIHU_API_URL", "https://v.api.aa1.cn/api/zhihu-news/index.php?aa1=xiarou").strip())
    zhihu_api_backup: str = field(default_factory=lambda: _get_env("ZHIHU_API_BACKUP", "https://api.oioweb.cn/api/common/zhihu/hot").strip())

    # 调度配置
    schedule_time: str = field(default_factory=lambda: _get_env("SCHEDULE_TIME", "08:00"))


# 全局配置实例
config = Config()
