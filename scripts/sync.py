"""
네이버 블로그 → GitHub Pages 미러 자동 동기화
- RSS 수집 → 중복 제거 → 미러 HTML 생성 → index.html + sitemap.xml 갱신
"""

import os
import re
import json
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

# ===== 설정 =====
BLOG_ID = "ggplus1"
SITE_TITLE = "연약지반 전문 공사업체 금강플러스"
SITE_DESC = "보링그라우팅, 파일공사, 토목공사, 포장공사, DCM공법, PP매트, 사석천공 전문"
KEYWORDS = "보링그라우팅, 파일공사, 토목공사, 포장공사, DCM공법, PP매트, 사석천공, 연약지반, 금강플러스"
SITE_URL = "https://ggplus1.github.io/blog-mirror"  # 끝에 / 없음

RSS_URL = f"https://rss.blog.naver.com/{BLOG_ID}.xml"

# ===== 경로 =====
ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
TEMPLATES_DIR = ROOT / "templates"
INDEX_JSON = ROOT / "posts_index.json"

POSTS_DIR.mkdir(exist_ok=True)


def load_index() -> dict:
    """이미 처리한 글 목록 로드 (중복 방지용)"""
    if INDEX_JSON.exists():
        return json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    return {"posts": []}


def save_index(index: dict) -> None:
    INDEX_JSON.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def extract_post_no(url: str) -> str | None:
    """네이버 블로그 URL에서 글 번호 추출"""
    # https://blog.naver.com/ggplus1/223456789 형태
    m = re.search(r"/(\d{9,})(?:[/?#]|$)", url)
    return m.group(1) if m else None


def clean_html(raw: str) -> str:
    """RSS 본문에서 스크립트/스타일 제거, 텍스트만 안전하게 추출"""
    soup = BeautifulSoup(raw or "", "html.parser")
    for tag in soup(["script", "style", "iframe"]):
        tag.decompose()
    # 이미지 src 중 네이버 내부 경로는 그대로 두되, 허용된 태그만 남김
    return str(soup)


def make_summary(text_html: str, limit: int = 160) -> str:
    """메타태그용 요약 텍스트 (HTML 태그 제거)"""
    text = BeautifulSoup(text_html or "", "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def fetch_feed() -> list[dict]:
    """RSS 피드 파싱"""
    print(f"[fetch] {RSS_URL}")
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BlogMirrorBot/1.0)"
    }
    try:
        resp = requests.get(RSS_URL, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[error] RSS 가져오기 실패: {e}")
        return []

    feed = feedparser.parse(resp.content)
    if feed.bozo:
        print(f"[warn] RSS 파싱 경고: {feed.bozo_exception}")

    items = []
    for entry in feed.entries:
        link = entry.get("link", "")
        post_no = extract_post_no(link)
        if not post_no:
            continue

        # 발행일
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
        else:
            pub_dt = datetime.now(timezone.utc)

        # 본문
        body_html = ""
        if "content" in entry and entry.content:
            body_html = entry.content[0].value
        elif "summary" in entry:
            body_html = entry.summary

        items.append({
            "post_no": post_no,
            "title": entry.get("title", "(제목 없음)"),
            "original_url": link,
            "published": pub_dt.isoformat(),
            "body_html": clean_html(body_html),
            "summary": make_summary(body_html),
        })
    print(f"[fetch] {len(items)}개 항목 수신")
    return items


def render_post(env: Environment, post: dict) -> None:
    """개별 미러 HTML 파일 생성"""
    tmpl = env.get_template("post.html.j2")
    html_out = tmpl.render(
        site_title=SITE_TITLE,
        site_url=SITE_URL,
        keywords=KEYWORDS,
        post=post,
    )
    out = POSTS_DIR / f"{post['post_no']}.html"
    out.write_text(html_out, encoding="utf-8")


def render_index(env: Environment, posts: list[dict]) -> None:
    """홈페이지(index.html) 생성"""
    tmpl = env.get_template("index.html.j2")
    # 최신순 정렬
    posts_sorted = sorted(posts, key=lambda p: p["published"], reverse=True)
    html_out = tmpl.render(
        site_title=SITE_TITLE,
        site_desc=SITE_DESC,
        site_url=SITE_URL,
        keywords=KEYWORDS,
        posts=posts_sorted,
        blog_id=BLOG_ID,
        updated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    (ROOT / "index.html").write_text(html_out, encoding="utf-8")


def render_sitemap(posts: list[dict]) -> None:
    """sitemap.xml 생성 (구글 크롤러용)"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    # 홈
    lines.append(
        f"  <url><loc>{SITE_URL}/</loc>"
        f"<lastmod>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</lastmod>"
        f"<changefreq>weekly</changefreq><priority>1.0</priority></url>"
    )
    for p in posts:
        lastmod = p["published"][:10]
        lines.append(
            f"  <url><loc>{SITE_URL}/posts/{p['post_no']}.html</loc>"
            f"<lastmod>{lastmod}</lastmod>"
            f"<changefreq>monthly</changefreq><priority>0.8</priority></url>"
        )
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")


def render_robots() -> None:
    """robots.txt 생성"""
    content = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    (ROOT / "robots.txt").write_text(content, encoding="utf-8")


def main() -> None:
    index = load_index()
    known = {p["post_no"] for p in index["posts"]}

    new_items = fetch_feed()
    if not new_items:
        print("[done] RSS 수집 결과 없음 — 기존 상태 유지")
        return

    # 템플릿 환경
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,  # XSS 방지
    )

    added = 0
    for item in new_items:
        if item["post_no"] in known:
            # 이미 있으면 HTML은 업데이트(제목/본문 수정 반영), 인덱스는 그대로
            render_post(env, item)
            continue
        render_post(env, item)
        index["posts"].append({
            "post_no": item["post_no"],
            "title": item["title"],
            "original_url": item["original_url"],
            "published": item["published"],
            "summary": item["summary"],
        })
        added += 1

    print(f"[new] 신규 {added}개 추가")

    # index.html / sitemap.xml / robots.txt 는 매번 재생성
    render_index(env, index["posts"])
    render_sitemap(index["posts"])
    render_robots()
    save_index(index)

    print(f"[done] 전체 {len(index['posts'])}개 게시물 미러링 완료")


if __name__ == "__main__":
    main()
