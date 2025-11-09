#!/usr/bin/env python3
"""
Script to fetch live stream URL from a web page and update m3u playlist file.
"""

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def strip_url_parameters(url: str) -> str:
    """
    Strip query parameters from a URL.

    Args:
        url: The URL to process

    Returns:
        URL without query parameters

    Example:
        Input: https://example.com/file.m3u8?s=abc&e=123
        Output: https://example.com/file.m3u8
    """
    parsed = urlparse(url)
    # Reconstruct URL without query string and fragment
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return clean_url


def extract_m3u8_from_page(url: str, preferred_domain: str = None) -> str | None:
    """
    Extract the m3u8 link from a web page using Playwright.
    This handles JavaScript-rendered content.

    Args:
        url: The URL of the page to fetch
        preferred_domain: Optional domain to prefer when multiple m3u8 URLs are found

    Returns:
        The m3u8 URL if found, None otherwise
    """
    print("Launching browser to fetch dynamic content...")

    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Track network requests to capture m3u8 URLs
        m3u8_urls = []

        def handle_request(request):
            if ".m3u8" in request.url:
                m3u8_urls.append(request.url)
                print(f"Captured m3u8 URL: {request.url}")

        page = context.new_page()
        page.on("request", handle_request)

        try:
            print(f"Navigating to: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Wait a bit more for the player to load and make requests
            time.sleep(5)

            # Also check the page content for any m3u8 links
            content = page.content()
            patterns = [
                r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    url_match = match if isinstance(match, str) else match
                    url_match = re.sub(r'["\',;)\]}]+$', "", url_match)
                    if url_match not in m3u8_urls:
                        m3u8_urls.append(url_match)

        except PlaywrightTimeoutError:
            print("Timeout while loading page", file=sys.stderr)
        finally:
            browser.close()

        if m3u8_urls:
            # Prefer URLs from specified domain if provided
            if preferred_domain:
                for url in m3u8_urls:
                    if preferred_domain in url:
                        print(f"Found m3u8 link: {url}")
                        return url
            # Return the first one if no preferred domain found or specified
            print(f"Found m3u8 link: {m3u8_urls[0]}")
            return m3u8_urls[0]

        print("No m3u8 link found")
        return None


def update_m3u_file(file_path: Path, new_url: str, entry_name: str) -> bool:
    """
    Update a stream URL in an m3u playlist file.

    Args:
        file_path: Path to the m3u file
        new_url: New stream URL to set
        entry_name: Name of the entry to update
    """
    try:
        content = file_path.read_text()

        pattern = rf"(#EXTINF:[^\n]*,{re.escape(entry_name)}\n)(https?://[^\n]+)"

        # Check if entry exists
        match = re.search(pattern, content)
        if not match:
            print(f'Entry "{entry_name}" not found in the m3u file', file=sys.stderr)
            return False

        old_url = match.group(2)

        # Check if URL has changed
        if old_url == new_url:
            print(f"URL unchanged: {new_url}")
            return False

        # Replace the old URL with the new one
        new_content = re.sub(pattern, rf"\g<1>{new_url}", content)

        # Write back to file
        file_path.write_text(new_content)
        print(f"Updated {entry_name} URL:")
        print(f"  Old: {old_url}")
        print(f"  New: {new_url}")
        return True

    except Exception as e:
        print(f"Error updating m3u file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch live stream URL from a web page and update m3u playlist file"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="URL of the web page to fetch the m3u8 link from",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the m3u playlist file to update",
    )
    parser.add_argument(
        "--entry-name",
        required=True,
        help="Name of the entry to update",
    )
    parser.add_argument(
        "--preferred-domain",
        help="Optional preferred domain for m3u8 URLs",
        required=False,
    )
    parser.add_argument(
        "--strip-parameters",
        action="store_true",
        help="Strip query parameters from the m3u8 URL",
        required=False,
        default=False,
    )

    args = parser.parse_args()

    m3u_file = Path(args.file)
    if not m3u_file.exists():
        print(f"Error: File not found: {m3u_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching live stream URL from: {args.url}")
    m3u8_url = extract_m3u8_from_page(args.url, args.preferred_domain)

    # Check if m3u8 URL was found
    if m3u8_url is None:
        print("✓ No m3u8 link found - skipping update")
        sys.exit(0)

    # Strip parameters if requested
    if args.strip_parameters:
        original_url = m3u8_url
        m3u8_url = strip_url_parameters(m3u8_url)
        if original_url != m3u8_url:
            print("Stripped parameters from URL:")
            print(f"  Original: {original_url}")
            print(f"  Cleaned:  {m3u8_url}")

    print(f"Updating m3u file: {m3u_file}")
    updated = update_m3u_file(m3u_file, m3u8_url, args.entry_name)

    if updated:
        print(f"✓ Successfully updated {args.entry_name} stream URL")
    else:
        print("✓ No update needed")


if __name__ == "__main__":
    main()
