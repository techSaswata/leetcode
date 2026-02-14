#!/usr/bin/env python3
"""
Fetch a LeetCode question by URL. Terminal only, no browser.
Uses curl_cffi to bypass Cloudflare (Chrome TLS impersonation).
"""
import json
import re
import sys
from urllib.parse import urlparse

try:
    from curl_cffi import requests
except ImportError:
    print("Install: pip install curl_cffi", file=sys.stderr)
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Install: pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)


def slug_from_url(url: str) -> str:
    m = re.search(r"leetcode\.com/problems/([^/]+)", url)
    return m.group(1) if m else ""


def html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def fetch_question(url: str) -> dict:
    slug = slug_from_url(url)
    if not slug:
        print("Could not parse problem slug from URL.", file=sys.stderr)
        sys.exit(1)

    session = requests.Session(impersonate="chrome")
    session.get("https://leetcode.com/", timeout=15)
    csrf = session.cookies.get("csrftoken", "")

    payload = {
        "operationName": "questionData",
        "variables": {"titleSlug": slug},
        "query": (
            "query questionData($titleSlug: String!) {"
            " question(titleSlug: $titleSlug) {"
            " questionId questionFrontendId title titleSlug content difficulty"
            " isPaidOnly topicTags { name slug }"
            " codeSnippets { lang langSlug code }"
            " exampleTestcases sampleTestCase"
            " } }"
        ),
    }
    r = session.post(
        "https://leetcode.com/graphql/",
        json=payload,
        headers={
            "Referer": "https://leetcode.com/",
            "Origin": "https://leetcode.com",
            "x-csrftoken": csrf,
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    if "data" not in data or "question" not in data["data"]:
        print("Unexpected response.", file=sys.stderr)
        sys.exit(1)
    return data["data"]["question"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_question.py <problem_url>", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    q = fetch_question(url)
    title = q.get("title", "")
    difficulty = q.get("difficulty", "")
    content_html = q.get("content", "")
    content_text = html_to_text(content_html)
    snippets = q.get("codeSnippets") or []
    examples = q.get("exampleTestcases", "")
    tags = [t.get("name", "") for t in (q.get("topicTags") or [])]

    print(f"# {title} ({difficulty})")
    print(f"Tags: {', '.join(tags)}")
    print()
    print(content_text)
    if examples:
        print("\n--- Example test cases ---")
        print(examples.strip())
    for s in snippets:
        if s.get("langSlug") == "python3":
            print("\n--- Python3 snippet ---")
            print(s.get("code", ""))


if __name__ == "__main__":
    main()
