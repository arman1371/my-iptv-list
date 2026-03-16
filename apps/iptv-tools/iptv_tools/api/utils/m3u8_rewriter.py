"""
Utility for rewriting relative URLs inside .m3u8 playlists so that all
non-comment lines (segment URLs, sub-playlist URLs) are routed back
through the proxy endpoint with the same referer.
"""

from urllib.parse import urljoin


def rewrite_m3u8(content: str, base_url: str, referer: str, proxy_base_url: str) -> str:
    """
    Rewrite a .m3u8 playlist so that every non-comment line (i.e. every URL)
    is replaced with a proxy URL pointing back to this server.

    Args:
        content:        Raw text content of the .m3u8 playlist.
        base_url:       The final (post-redirect) URL that was fetched, used to
                        resolve relative paths via urljoin.
        referer:        The referer string to embed in each rewritten proxy URL.
        proxy_base_url: The base URL of this proxy server, e.g.
                        "http://192.168.1.10:8000" — rewritten lines will look like
                        "http://192.168.1.10:8000/proxy?url=<abs_url>&referer=<referer>"

    Returns:
        The rewritten playlist as a plain string.
    """
    lines = content.splitlines()
    result = []

    for line in lines:
        stripped = line.strip()

        # Keep blank lines and comment/tag lines as-is
        if not stripped or stripped.startswith("#"):
            result.append(line)
            continue

        # Resolve relative URL against the base (post-redirect) URL
        absolute_url = urljoin(base_url, stripped)

        proxy_url = f"{proxy_base_url}/proxy?url={absolute_url}&referer={referer}"

        result.append(proxy_url)

    return "\n".join(result) + "\n"
