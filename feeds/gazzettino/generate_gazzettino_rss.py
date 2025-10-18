#!/usr/bin/env python3
"""
generate_gazzettino_rss.py
Genera un feed RSS completo da https://www.ilgazzettino.it/nordest/
Salva titolo + descrizione + corpo completo dell'articolo.
"""

import requests, time, os
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

# ---------- CONFIG ---------- #
BASE = "https://www.ilgazzettino.it/nordest/"
OUT_PATH = os.path.join(os.path.dirname(__file__), "gazzettino_rss.xml")
USER_AGENT = "SimpleRSS/1.0 (+https://example.com)"
MAX_LINKS = 50
REQUEST_DELAY = 1.0
TIMEOUT = 15
# ---------------------------- #

def fetch_text(url):
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def discover_links(html):
    s = BeautifulSoup(html, "html.parser")
    found = []
    # 1) link dentro <article>
    for a in s.select("article a[href]"):
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = BASE.rstrip("/") + href
        if href.startswith("http") and href not in found:
            found.append(href)
        if len(found) >= MAX_LINKS:
            return found
    # 2) fallback: link contenenti "/20", "/news/", "/cronaca/" ecc.
    for a in s.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = BASE.rstrip("/") + href
        if href.startswith("http") and href not in found:
            lower = href.lower()
            if "/20" in lower or "/news/" in lower or "/cronaca/" in lower:
                found.append(href)
        if len(found) >= MAX_LINKS:
            break
    return found

def parse_article(html, url):
    s = BeautifulSoup(html, "html.parser")
    # titolo
    title = s.find("h1").get_text(strip=True) if s.find("h1") else url
    # descrizione
    desc = ""
    meta = s.find("meta", {"property": "og:description"}) or s.find("meta", {"name": "description"})
    if meta and meta.get("content"):
        desc = meta.get("content")
    # corpo completo
    body = s.select_one("article, .article-body, .news-content, .content")
    corpo = ""
    if body:
        corpo = "\n".join([p.get_text(strip=True) for p in body.find_all("p")])
    # unisci descrizione + corpo (così il feed contiene tutto)
    full_text = "\n".join([desc, corpo]).strip()
    # pubdate
    pub = None
    m = s.find("meta", {"property": "article:published_time"})
    if m and m.get("content"):
        pub = m["content"]
    return {"title": title, "link": url, "description": full_text, "pubDate": pub}

def build_rss(items):
    fg = FeedGenerator()
    fg.title("Il Gazzettino - Nordest")
    fg.link(href=BASE)
    fg.description("Feed RSS generato automaticamente contenente titolo, descrizione e corpo")
    fg.language("it")
    for it in items:
        fe = fg.add_entry()
        fe.id(it["link"])
        fe.title(it["title"])
        fe.link(href=it["link"])
        fe.description(it["description"])
        if it.get("pubDate"):
            fe.pubDate(it["pubDate"])
    return fg.rss_str(pretty=True).decode("utf-8")

def main():
    print("[*] Scarico la home page...")
    html = fetch_text(BASE)
    links = discover_links(html)
    print(f"[*] Trovati {len(links)} link.")
    items = []
    for i, link in enumerate(links, 1):
        print(f"  - ({i}/{len(links)}) {link}")
        try:
            ahtml = fetch_text(link)
            item = parse_article(ahtml, link)
            items.append(item)
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print("    errore:", e)
    xml = build_rss(items)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"[+] Feed aggiornato: {OUT_PATH}")

if __name__ == "__main__":
    main()


