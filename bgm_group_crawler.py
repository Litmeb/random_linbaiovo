import argparse
import json
import re
import time
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (compatible; bgm-group-crawler/1.0)"
TOPIC_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
TOPIC_LINK_RE = re.compile(
    r'<a[^>]+href="(/group/topic/\d+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
USER_LINK_RE = re.compile(
    r'<a[^>]+href="(/user/[^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
CONTENT_CLASS_KEYS = {
    "topic_content",
    "post_content",
    "message",
    "post_content_box",
    "post_body",
    "postContent",
}


def fetch_html(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="ignore")


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if tag in {"br", "p", "div", "li", "tr", "td", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if tag in {"p", "div", "li", "tr", "td"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self.parts)
        text = unescape(raw)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        return text.strip()


def strip_tags(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()


class BodyExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture_depth = 0
        self.done = False
        self.skip_depth = 0
        self.parts: list[str] = []

    def _matches_class(self, attrs) -> bool:
        for key, value in attrs:
            if key == "class":
                classes = set(value.split())
                if classes & CONTENT_CLASS_KEYS:
                    return True
        return False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            if self.capture_depth > 0:
                self.skip_depth += 1
            return
        if self.done:
            return
        if self.capture_depth > 0:
            if tag in {"br", "p", "div", "li", "tr", "td"}:
                self.parts.append("\n")
            self.capture_depth += 1
            return
        if tag in {"div", "section", "article"} and self._matches_class(attrs):
            self.capture_depth = 1

    def handle_endtag(self, tag):
        if self.done or self.capture_depth == 0:
            return
        if tag in {"script", "style", "noscript"} and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if tag in {"p", "div", "li", "tr", "td"}:
            self.parts.append("\n")
        self.capture_depth -= 1
        if self.capture_depth == 0:
            self.done = True

    def handle_data(self, data):
        if self.capture_depth > 0 and self.skip_depth == 0:
            self.parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self.parts)
        text = unescape(raw)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        return text.strip()


@dataclass
class TopicItem:
    title: str
    author: str
    username: str
    url: str
    body: str = ""
    reply_count: int = 0


def parse_topic_list(html: str, base_url: str) -> list[TopicItem]:
    items: list[TopicItem] = []
    seen: set[str] = set()
    for row in TOPIC_ROW_RE.findall(html):
        topic_match = TOPIC_LINK_RE.search(row)
        if not topic_match:
            continue
        href, title_html = topic_match.groups()
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        title = strip_tags(title_html)
        author = ""
        username = ""
        user_links = [m for m in USER_LINK_RE.finditer(row) if m.group(1).startswith("/user/")]
        if user_links:
            author = strip_tags(user_links[0].group(2))
            # href 形如 /user/username，取第二段为 username
            href = user_links[0].group(1).rstrip("/")
            username = href.removeprefix("/user/").split("/")[0] or ""
        reply_count = 0
        td_contents = re.findall(r"<td[^>]*>(.*?)</td>", row, re.IGNORECASE | re.DOTALL)
        if len(td_contents) >= 3:
            reply_str = strip_tags(td_contents[2]).strip()
            if reply_str.isdigit():
                reply_count = int(reply_str)
        items.append(TopicItem(title=title, author=author, username=username, url=url, reply_count=reply_count))
    return items


def extract_body(html: str) -> str:
    extractor = BodyExtractor()
    extractor.feed(html)
    body_text = extractor.get_text()
    if body_text:
        return body_text

    # Fallback: take the first post block with id="post_..."
    match = re.search(
        r'<div[^>]+id="post_\d+"[^>]*>(.*?)</div>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return strip_tags(match.group(1))
    return ""


def crawl_group(
    group_url: str,
    pages: int,
    limit: int | None,
    sleep_sec: float,
    min_replies: int | None = None,
) -> list[TopicItem]:
    topics: list[TopicItem] = []
    for page in range(1, pages + 1):
        page_url = f"{group_url.rstrip('/')}/forum?page={page}"
        print(f"[list] page {page}/{pages}: {page_url}", flush=True)
        page_html = fetch_html(page_url)
        topics.extend(parse_topic_list(page_html, group_url))
        time.sleep(sleep_sec)

    if min_replies is not None:
        topics = [t for t in topics if t.reply_count >= min_replies]
        print(f"[filter] min_replies>={min_replies}: {len(topics)} topics remain", flush=True)

    if limit is not None:
        topics = topics[:limit]

    for idx, topic in enumerate(topics, start=1):
        print(f"[post] {idx}/{len(topics)}: {topic.title}", flush=True)
        topic_html = fetch_html(topic.url)
        topic.body = extract_body(topic_html)
        if idx < len(topics):
            time.sleep(sleep_sec)
    return topics


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl Bangumi group topics.")
    parser.add_argument(
        "group_url",
        help="Group URL, e.g. https://bgm.tv/group/psycho",
    )
    parser.add_argument("--pages", type=int, default=1, help="Number of list pages to crawl.")
    parser.add_argument("--limit", type=int, default=None, help="Max number of topics.")
    parser.add_argument(
        "--min-replies",
        type=int,
        default=None,
        metavar="N",
        help="Filter out topics with fewer than N replies.",
    )
    parser.add_argument("--sleep", type=float, default=1.0, help="Sleep seconds between requests.")
    parser.add_argument("--output", default="posts.json", help="Output JSON file path.")
    args = parser.parse_args()

    EXCLUDE_PHRASE = "数据库中没有查询到指定话题"

    topics = crawl_group(
        args.group_url, args.pages, args.limit, args.sleep, args.min_replies
    )
    payload = [
        {"author": t.author, "username": t.username, "title": t.title, "url": t.url, "body": t.body}
        for t in topics
        if EXCLUDE_PHRASE not in t.body and EXCLUDE_PHRASE not in t.title
    ]
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(payload)} posts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
