# -*- coding: utf-8 -*-
"""
AI 摘要模块
使用 DeepSeek API 生成智能摘要
"""
from openai import OpenAI

from config import config
from utils import logger


def get_client() -> OpenAI | None:
    """获取 DeepSeek API 客户端"""
    if not config.deepseek_api_key:
        return None
    return OpenAI(
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
    )


def summarize_text(text: str, max_length: int = 50) -> str:
    """
    使用 DeepSeek 生成文本摘要
    
    Args:
        text: 需要摘要的文本
        max_length: 摘要最大长度
    
    Returns:
        摘要文本，失败时返回原文截断
    """
    if not config.ai_summary_enabled:
        return text[:max_length] if len(text) > max_length else text
    
    client = get_client()
    if not client:
        logger.warning("DeepSeek API Key 未配置，使用原文截断")
        return text[:max_length] if len(text) > max_length else text
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": f"你是一个专业的新闻摘要助手。请用不超过{max_length}个字简洁概括以下内容的核心要点。只输出摘要，不要有任何前缀或解释。",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            max_tokens=100,
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()
        return summary[:max_length] if len(summary) > max_length else summary
    except Exception as exc:  # noqa: BLE001
        logger.error("DeepSeek 摘要生成失败: %s", exc)
        return text[:max_length] if len(text) > max_length else text


def summarize_news_list(news_list: list) -> list:
    """
    为新闻列表生成 AI 摘要
    
    Args:
        news_list: 新闻列表
    
    Returns:
        带有 AI 摘要的新闻列表
    """
    if not config.ai_summary_enabled:
        return news_list
    
    for item in news_list:
        description = item.get("description", "") or item.get("summary", "")
        if description and len(description) > 30:
            item["ai_summary"] = summarize_text(description, max_length=50)
        else:
            item["ai_summary"] = description
    
    return news_list


def translate_to_chinese(text: str) -> str:
    """
    使用 DeepSeek 将英文翻译为中文
    
    Args:
        text: 英文文本
    
    Returns:
        中文翻译，失败时返回原文
    """
    if not config.ai_summary_enabled or not text:
        return text
    
    client = get_client()
    if not client:
        return text
    
    # 简单判断是否需要翻译（包含中文则不翻译）
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        return text
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的翻译助手。请将以下英文翻译为简洁的中文，只输出翻译结果。",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("DeepSeek 翻译失败: %s", exc)
        return text
