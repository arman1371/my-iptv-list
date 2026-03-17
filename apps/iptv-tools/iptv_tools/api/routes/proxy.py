import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, Response

from iptv_tools.api.utils.m3u8_rewriter import rewrite_m3u8

router = APIRouter()

# Content-Type values that indicate an HLS playlist
_M3U8_CONTENT_TYPES = (
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "audio/mpegurl",
    "audio/x-mpegurl",
)


def _is_m3u8(url: str, content_type: str) -> bool:
    """Return True if the response looks like an HLS/M3U8 playlist."""
    ct = content_type.lower()
    if any(ct.startswith(t) for t in _M3U8_CONTENT_TYPES):
        return True
    # Fall back to URL suffix (some servers send text/plain for .m3u8)
    stripped = url.split("?")[0].lower()
    return stripped.endswith(".m3u8") or stripped.endswith(".m3u")


@router.get("/proxy")
async def proxy(
    request: Request,
    url: str = Query(..., description="The target URL to fetch."),
    referer: str = Query(
        ..., description="The Referer header value to inject into the request."
    ),
):
    """
    Fetch *url* with the given *referer* injected as a request header,
    follow redirects, and return the raw response body.

    If the response is an HLS/M3U8 playlist, all relative segment/playlist
    URLs are rewritten to route back through this proxy endpoint so that
    subsequent requests also carry the correct Referer automatically.

    For binary responses (e.g. MPEG-TS segments) the raw bytes are streamed
    directly without any charset decoding, which would otherwise corrupt or
    truncate binary data.
    """
    headers = {"Referer": referer}

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Upstream returned {exc.response.status_code} for {url}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach upstream: {exc}",
        )

    content_type = response.headers.get("content-type", "")
    final_url = str(response.url)  # post-redirect URL, used as base for relative paths

    # hop-by-hop and encoding headers that must not be forwarded
    _skip = {"content-length", "transfer-encoding", "content-encoding", "connection"}
    upstream_headers = {
        k: v for k, v in response.headers.items() if k.lower() not in _skip
    }

    if _is_m3u8(final_url, content_type):
        # Build the proxy base URL from the incoming request so it works
        # regardless of the host/port the server is running on.
        proxy_base = str(request.base_url).rstrip("/")
        body = rewrite_m3u8(
            content=response.text,
            base_url=final_url,
            referer=referer,
            proxy_base_url=proxy_base,
        )
        return PlainTextResponse(content=body, headers=upstream_headers)

    # For binary segments (MPEG-TS, AAC, etc.) stream the raw bytes to avoid
    # charset decoding which silently corrupts/truncates binary content.
    raw_bytes = response.content
    return Response(content=raw_bytes, headers=upstream_headers)
