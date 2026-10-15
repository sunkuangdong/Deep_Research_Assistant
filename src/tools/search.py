import os

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

BOCHA_API_URL = "https://api.bochaai.com/v1/web-search"

def format_web_pages(webpages: list[dict]) -> str:
    parts = []
    for idx, page in enumerate(webpages):
        parts.append(
            f"""引用: {idx + 1}
            标题: {page.get("name") or ""}
            URL: {page.get("url") or ""}
            摘要: {page.get("summary") or ""}
            网站名称: {page.get("siteName") or ""}
            网站图标: {page.get("siteIcon") or ""}
            发布时间: {page.get("dateLastCrawled") or ""}"""
        )
    return "\n\n".join(parts)
    
async def bocha_web_search(query: str, count: int) -> str:
    api_key = (os.getenv("BOCHA_API_KEY") or "").strip()

    if not api_key:
        return (
            "Bocha 联网搜索的 API Key 未配置（环境变量 BOCHA_API_KEY），"
            "请先在 .env 中配置后再重试。"
        )
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            BOCHA_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "query": query,
                "count": count,
                "summary": True,
                "freshness": "noLimit",
            },
        )

        if not response.is_success:
            return (
                f"搜索 API 请求失败，状态码: {response.status_code}，"
                f"错误信息: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as e:
            return f"Bocha 联网搜索 API 返回的 JSON 数据解析失败: {e}"

        if not isinstance(data, dict):
            return "Bocha 联网搜索 API 返回了非对象 JSON。"
        if data.get("code") != 200 or not isinstance(data.get("data"), dict):
            return f"搜索 API 请求失败，原因是: {data.get('msg') or '未知错误'}"

        web_pages = data["data"].get("webPages") or {}
        if not isinstance(web_pages, dict):
            return "Bocha 联网搜索 API 的 webPages 字段格式无效。"
        webpages = web_pages.get("value") or []
        if not isinstance(webpages, list):
            return "Bocha 联网搜索 API 的结果列表格式无效。"

        if not webpages:
            return f"未找到与「{query}」相关的结果。"

        return format_web_pages(webpages)

class WebSearchInput(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description=(
            "搜索关键词应跟随当前任务语言；查找原始资料时优先使用官方域名定向查询，"
            "例如 site:rfc-editor.org RFC 6455。Search in the task language and "
            "use domain-qualified queries when primary documentation is required."
        ),
    )
    count: int = Field(
        default=10,
        ge=1,
        le=20,
        description="返回的搜索结果数量，默认 10 条",
    )

@tool("web_search", args_schema=WebSearchInput)
async def web_search(query: str, count: int = 10) -> str:
    """使用 Bocha 联网搜索 API 检索网页；查询语言跟随任务语言，并返回来源 URL 与摘要。"""

    print(f"  🔎 搜索: {query}（{count} 条）")
    return await bocha_web_search(query, count)



