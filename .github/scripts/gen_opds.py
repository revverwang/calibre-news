#!/usr/bin/env python3
"""生成 OPDS 目录（供 KOReader 订阅下载新闻 epub）。"""
import datetime
import html
import os
import pathlib
import shutil
import urllib.parse
import uuid

BOOKS = pathlib.Path("docs/books")
BOOKS.mkdir(parents=True, exist_ok=True)

# 同时产出两份目录：jsDelivr 源（国内可访问）与 GitHub Pages 源（实时）
BASES = {
    "opds.xml": os.environ.get("OPDS_BASE_JSD", "").rstrip("/"),
    "opds-pages.xml": os.environ.get("OPDS_BASE_PAGES", "").rstrip("/"),
}

RETENTION = int(os.environ.get("RETENTION_DAYS", "7"))
EXT_ALLOWED = {".epub", ".azw3", ".mobi", ".pdf"}
NS = uuid.UUID("6f1b5a2e-1c4d-4f6a-9a1e-0d3c7b8e5f21")


def parse_date(p: pathlib.Path):
    """文件名形如 2026-11-12-Title.epub，取出日期用于保留期判断。"""
    try:
        return datetime.date.fromisoformat(p.name[:10])
    except ValueError:
        return None


# 清理超期文件，避免仓库无限增长
today = datetime.date.today()
for f in BOOKS.iterdir():
    if not f.is_file():
        continue
    d = parse_date(f)
    if d and (today - d).days > RETENTION:
        f.unlink()

books = [p for p in BOOKS.iterdir() if p.is_file() and p.suffix.lower() in EXT_ALLOWED]
books.sort(key=lambda p: p.name, reverse=True)

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
feed_id = f"urn:uuid:{uuid.uuid5(NS, 'calibre-news-feed')}"


def build(base: str) -> str:
    entries = []
    for p in books:
        stem = p.stem
        display = stem[11:] if len(stem) > 11 and stem[10] == "-" else stem
        d = parse_date(p)
        updated = (
            d.isoformat() + "T00:00:00Z" if d else now
        )
        href = (
            f"{base}/books/{urllib.parse.quote(p.name)}"
            if base
            else f"books/{urllib.parse.quote(p.name)}"
        )
        mime = {
            ".epub": "application/epub+zip",
            ".azw3": "application/x-mobipocket-ebook",
            ".mobi": "application/x-mobipocket-ebook",
            ".pdf": "application/pdf",
        }.get(p.suffix.lower(), "application/octet-stream")
        size_kb = max(1, p.stat().st_size // 1024)
        entries.append(
            f"""  <entry>
    <title>{html.escape(display)}</title>
    <id>urn:uuid:{uuid.uuid5(NS, p.name)}</id>
    <updated>{updated}</updated>
    <author><name>Calibre News Delivery</name></author>
    <content type="text">{p.suffix.lstrip('.').upper()} · {size_kb} KB</content>
    <link rel="http://opds-spec.org/acquisition" type="{mime}" href="{html.escape(href)}"/>
  </entry>"""
        )
    self_href = f"{base}/opds.xml" if base else "opds.xml"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opds="http://opds-spec.org/2010/catalog">
  <id>{feed_id}</id>
  <title>Calibre 每日新闻</title>
  <subtitle>每天自动抓取并转制的新闻电子书</subtitle>
  <updated>{now}</updated>
  <author><name>Calibre News Delivery</name></author>
  <link rel="self" href="{html.escape(self_href)}" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <link rel="start" href="{html.escape(self_href)}" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
{chr(10).join(entries)}
</feed>
"""


for name, base in BASES.items():
    pathlib.Path("docs", name).write_text(build(base), encoding="utf-8")
    print(f"generated docs/{name} (base={base!r}, books={len(books)})")

# 网页版索引，方便手机浏览器直接点开
rows = "\n".join(
    f'    <li><a href="books/{urllib.parse.quote(p.name)}">{html.escape(p.stem[11:] if len(p.stem) > 11 else p.stem)}</a></li>'
    for p in books
)
pathlib.Path("docs/index.html").write_text(
    f"""<!doctype html>
<html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Calibre 每日新闻</title>
<style>body{{font:16px/1.7 -apple-system,sans-serif;max-width:38rem;margin:2rem auto;padding:0 1rem;color:#222}}
a{{color:#0a6cff;text-decoration:none}}li{{margin:.4rem 0}}</style>
<h1>Calibre 每日新闻</h1>
<p>共 {len(books)} 本，保留最近 {RETENTION} 天。KOReader 可订阅 OPDS：<code>opds.xml</code></p>
<ul>
{rows}
</ul>
</html>
""",
    encoding="utf-8",
)
print("generated docs/index.html")
