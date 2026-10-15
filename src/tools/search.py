import asyncio
import ipaddress
import os
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

BOCHA_API_URL = "https://api.bochaai.com/v1/web-search"


class BochaSearchError(RuntimeError):
    """Raised when the search provider remains unavailable after retries."""


class WebFetchError(RuntimeError):
    """Raised when a requested page cannot be fetched safely."""


class _VisibleTextParser(HTMLParser):
    """Extract readable text from HTML without adding another dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        normalized = tag.casefold()
        if normalized in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1
        if normalized == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in {"script", "style", "noscript", "svg"}:
            self._hidden_depth = max(0, self._hidden_depth - 1)
        if normalized == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._hidden_depth or not data.strip():
            return
        self.text_parts.append(data)
        if self._in_title:
            self.title_parts.append(data)


def bocha_timeout_seconds() -> float:
    value = float((os.getenv("BOCHA_TIMEOUT_SECONDS") or "20").strip())
    if value <= 0:
        raise ValueError("BOCHA_TIMEOUT_SECONDS must be positive")
    return value


def bocha_max_retries() -> int:
    value = int((os.getenv("BOCHA_MAX_RETRIES") or "2").strip())
    if value < 0:
        raise ValueError("BOCHA_MAX_RETRIES must be non-negative")
    return value


def web_fetch_timeout_seconds() -> float:
    value = float((os.getenv("WEB_FETCH_TIMEOUT_SECONDS") or "20").strip())
    if value <= 0:
        raise ValueError("WEB_FETCH_TIMEOUT_SECONDS must be positive")
    return value


def web_fetch_max_retries() -> int:
    value = int((os.getenv("WEB_FETCH_MAX_RETRIES") or "1").strip())
    if value < 0:
        raise ValueError("WEB_FETCH_MAX_RETRIES must be non-negative")
    return value


def web_fetch_max_bytes() -> int:
    value = int((os.getenv("WEB_FETCH_MAX_BYTES") or "200000").strip())
    if value <= 0:
        raise ValueError("WEB_FETCH_MAX_BYTES must be positive")
    return value


def web_fetch_max_chars() -> int:
    value = int((os.getenv("WEB_FETCH_MAX_CHARS") or "12000").strip())
    if value <= 0:
        raise ValueError("WEB_FETCH_MAX_CHARS must be positive")
    return value


def canonical_source_url(value: str) -> str:
    """Normalize a source page URL while treating fragments as the same page."""

    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").casefold()
        if not host:
            return value.strip()
        authority_host = f"[{host}]" if ":" in host else host
        port = f":{parsed.port}" if parsed.port is not None else ""
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit(
            (
                parsed.scheme.casefold(),
                authority_host + port,
                path,
                parsed.query,
                "",
            )
        )
    except ValueError:
        return value.strip()


def _validate_web_url(url: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(url.strip())
        _ = parsed.port
    except ValueError as exc:
        raise WebFetchError("invalid URL") from exc

    if parsed.scheme.casefold() not in {"http", "https"}:
        raise WebFetchError("only HTTP(S) URLs are allowed")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise WebFetchError("URL must have a host and must not contain credentials")

    host = parsed.hostname.casefold().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise WebFetchError("local or internal hosts are not allowed")
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not literal_ip.is_global:
            raise WebFetchError("non-public IP addresses are not allowed")
    return parsed.geturl(), host


async def _validate_public_dns(host: str) -> None:
    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            host,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise WebFetchError(f"host could not be resolved: {host}") from exc

    resolved_ips = {
        item[4][0].split("%", 1)[0]
        for item in addresses
        if item[4] and item[4][0]
    }
    if not resolved_ips:
        raise WebFetchError(f"host resolved to no addresses: {host}")
    if any(not ipaddress.ip_address(value).is_global for value in resolved_ips):
        raise WebFetchError("host resolves to a non-public IP address")


def _page_text(content: str, content_type: str) -> tuple[str, str]:
    if "html" not in content_type.casefold():
        return "", re.sub(r"\s+", " ", content).strip()

    parser = _VisibleTextParser()
    parser.feed(content)
    title = re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip()
    text = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    return title, text


async def fetch_web_page(
    url: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    retry_delay_seconds: float = 0.5,
) -> str:
    """Fetch one public text page and return bounded evidence with its final URL."""

    max_retries = web_fetch_max_retries()
    max_bytes = web_fetch_max_bytes()
    max_chars = web_fetch_max_chars()
    allowed_types = ("text/", "application/xhtml+xml", "application/json")
    headers = {
        "Accept": "text/html,text/plain,application/xhtml+xml,application/json",
        "User-Agent": "DeepResearchAssistant/1.0 (+source-verification)",
    }

    for attempt in range(max_retries + 1):
        current_url = url.strip()
        try:
            async with httpx.AsyncClient(
                timeout=web_fetch_timeout_seconds(),
                transport=transport,
                follow_redirects=False,
            ) as client:
                for redirect_count in range(4):
                    validated_url, host = _validate_web_url(current_url)
                    if transport is None:
                        await _validate_public_dns(host)

                    async with client.stream(
                        "GET", validated_url, headers=headers
                    ) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                raise WebFetchError("redirect response had no Location")
                            if redirect_count >= 3:
                                raise WebFetchError("too many redirects")
                            current_url = urljoin(validated_url, location)
                            continue

                        if response.status_code == 429 or response.status_code >= 500:
                            raise httpx.HTTPStatusError(
                                "transient fetch response",
                                request=response.request,
                                response=response,
                            )
                        if not response.is_success:
                            return (
                                f"FETCH_ERROR: HTTP {response.status_code} for "
                                f"{validated_url}"
                            )

                        content_type = response.headers.get("content-type", "")
                        media_type = content_type.split(";", 1)[0].strip().casefold()
                        if media_type and not media_type.startswith(allowed_types):
                            return (
                                "FETCH_ERROR: unsupported content type "
                                f"{media_type} for {validated_url}"
                            )

                        body = bytearray()
                        truncated_bytes = False
                        async for chunk in response.aiter_bytes():
                            remaining = max_bytes - len(body)
                            if remaining <= 0:
                                truncated_bytes = True
                                break
                            body.extend(chunk[:remaining])
                            if len(chunk) > remaining:
                                truncated_bytes = True
                                break

                        encoding = response.encoding or "utf-8"
                        decoded = body.decode(encoding, errors="replace")
                        title, visible_text = _page_text(decoded, media_type)
                        truncated_chars = len(visible_text) > max_chars
                        visible_text = visible_text[:max_chars]
                        if not visible_text:
                            return f"FETCH_ERROR: no readable text at {validated_url}"

                        return (
                            f"Fetched URL: {response.url!s}\n"
                            f"Title: {title}\n"
                            f"Content-Type: {media_type or 'unknown'}\n"
                            f"Truncated: {truncated_bytes or truncated_chars}\n"
                            f"Content:\n{visible_text}"
                        )
        except WebFetchError as exc:
            return f"FETCH_ERROR: {exc}"
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if attempt >= max_retries:
                return (
                    "FETCH_ERROR: request failed after "
                    f"{attempt + 1} attempts ({type(exc).__name__})"
                )
            await asyncio.sleep(retry_delay_seconds * (2**attempt))

    raise AssertionError("unreachable web fetch state")


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
    
async def bocha_web_search(
    query: str,
    count: int,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    retry_delay_seconds: float = 0.5,
) -> str:
    api_key = (os.getenv("BOCHA_API_KEY") or "").strip()

    if not api_key:
        return (
            "Bocha 联网搜索的 API Key 未配置（环境变量 BOCHA_API_KEY），"
            "请先在 .env 中配置后再重试。"
        )
    
    max_retries = bocha_max_retries()
    response: httpx.Response | None = None
    async with httpx.AsyncClient(
        timeout=bocha_timeout_seconds(),
        transport=transport,
    ) as client:
        for attempt in range(max_retries + 1):
            try:
                response = await client.post(
                    BOCHA_API_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "count": count,
                        "summary": True,
                        "freshness": "noLimit",
                    },
                )
            except httpx.TransportError as exc:
                if attempt >= max_retries:
                    raise BochaSearchError(
                        "Bocha Web Search transport failed after "
                        f"{attempt + 1} attempts: {type(exc).__name__}"
                    ) from exc
            else:
                if response.status_code != 429 and response.status_code < 500:
                    break
                if attempt >= max_retries:
                    raise BochaSearchError(
                        "Bocha Web Search remained unavailable after "
                        f"{attempt + 1} attempts (HTTP {response.status_code})"
                    )
            await asyncio.sleep(retry_delay_seconds * (2**attempt))

    if response is None:
        raise BochaSearchError("Bocha Web Search returned no response")
    if response.status_code in {401, 403}:
        raise BochaSearchError(
            "Bocha Web Search authentication or quota failure "
            f"(HTTP {response.status_code})"
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
            "use domain-qualified queries when primary documentation is required. "
            "The site: filter must contain a domain only, never a URL path."
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


class WebFetchInput(BaseModel):
    url: str = Field(
        ...,
        min_length=8,
        description=(
            "A complete public HTTP(S) source URL to retrieve and verify. "
            "Use the exact Fetched URL returned by this tool when citing the page."
        ),
    )


@tool("web_fetch", args_schema=WebFetchInput)
async def web_fetch(url: str) -> str:
    """读取公开 HTTP(S) 文本页面；成功时返回可引用的最终 URL 和受限正文。"""

    print(f"  🌐 抓取: {url}")
    return await fetch_web_page(url)



