"""
Scrape a paginated catalogue into a clean CSV.

Target: books.toscrape.com - a sandbox site published specifically for scraping
practice, so this demo carries no terms-of-service or rate-limit concerns. The
same structure is what I run against a real client site: one polite session,
explicit selectors, retries on transient failures, and a typed row out.

Usage:
    python scrape_books.py --pages 5 --out data/books_scraped.csv
"""

import argparse
import csv
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://books.toscrape.com/catalogue/page-{}.html"
RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
HEADERS = {"User-Agent": "portfolio-demo-scraper/1.0 (contact via Fiverr)"}


def get(session, url, retries=3, backoff=1.5):
    """Fetch a URL, retrying transient failures rather than dying on the first blip."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait = backoff ** attempt
            print(f"  retry {attempt}/{retries} after {exc.__class__.__name__} ({wait:.1f}s)",
                  file=sys.stderr)
            time.sleep(wait)
    return None


def parse_price(text):
    """'£51.77' -> 51.77. Returns None rather than guessing if the format changes."""
    match = re.search(r"(\d+(?:\.\d{1,2})?)", text.replace(",", ""))
    return float(match.group(1)) if match else None


def parse_rating(article):
    """The rating is encoded in a class name, e.g. 'star-rating Three'."""
    classes = article.select_one("p.star-rating")
    if not classes:
        return None
    for word, value in RATING_WORDS.items():
        if word in classes.get("class", []):
            return value
    return None


def scrape_page(session, page_no):
    resp = get(session, BASE.format(page_no))
    if resp is None:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = []
    for article in soup.select("article.product_pod"):
        link = article.select_one("h3 a")
        availability = article.select_one("p.availability")
        rows.append({
            "title": link["title"].strip(),
            "price_gbp": parse_price(article.select_one("p.price_color").get_text()),
            "rating": parse_rating(article),
            "in_stock": "In stock" in availability.get_text() if availability else None,
            "url": urljoin("https://books.toscrape.com/catalogue/", link["href"]),
            "source_page": page_no,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=5, help="how many listing pages to walk")
    ap.add_argument("--out", default="data/books_scraped.csv")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    args = ap.parse_args()

    all_rows = []
    with requests.Session() as session:
        session.headers.update(HEADERS)
        for page_no in range(1, args.pages + 1):
            print(f"page {page_no} ...", file=sys.stderr)
            rows = scrape_page(session, page_no)
            if rows is None:
                print("  no more pages", file=sys.stderr)
                break
            all_rows.extend(rows)
            time.sleep(args.delay)

    if not all_rows:
        print("nothing scraped - selectors may have changed", file=sys.stderr)
        return 1

    fields = ["title", "price_gbp", "rating", "in_stock", "url", "source_page"]
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    priced = [r["price_gbp"] for r in all_rows if r["price_gbp"] is not None]
    print(f"{len(all_rows)} rows -> {args.out}")
    print(f"  priced rows: {len(priced)}  avg GBP {sum(priced)/len(priced):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
