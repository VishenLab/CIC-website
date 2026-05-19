#!/usr/bin/env python3
"""Fetch recent publications from Semantic Scholar and update index.html."""

import json
import re
import time
import urllib.request
from datetime import datetime

PIS = [
    {"name": "Mayor",    "author_id": "144688536"},
    {"name": "Köster",   "author_id": "47806737"},
    {"name": "Schneider","author_id": "144453640"},
    {"name": "Kreysing", "author_id": "51248942"},
    {"name": "Vishen",   "author_id": "2251618427"},
]

MIN_YEAR = datetime.now().year - 3  # keep last ~3 years
MAX_JOURNAL = 15
MAX_PREPRINT = 5


def fetch_papers(author_id):
    url = (
        f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers"
        f"?fields=title,year,authors,venue,externalIds,publicationTypes&limit=50"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CIC-website/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("data", [])
    except Exception as e:
        print(f"  Warning: could not fetch author {author_id}: {e}")
        return []


def paper_url(paper):
    ext = paper.get("externalIds") or {}
    if ext.get("DOI"):
        return f"https://doi.org/{ext['DOI']}"
    if ext.get("ArXiv"):
        return f"https://arxiv.org/abs/{ext['ArXiv']}"
    pid = paper.get("paperId")
    return f"https://www.semanticscholar.org/paper/{pid}" if pid else "#"


def short_authors(paper):
    authors = paper.get("authors") or []
    if not authors:
        return ""
    last = (authors[0].get("name") or "").split()[-1]
    return f"{last} et al." if len(authors) > 1 else last


def venue_display(paper):
    ext = paper.get("externalIds") or {}
    if ext.get("ArXiv"):
        return f"arXiv:{ext['ArXiv']}"
    return paper.get("venue") or ""


def is_preprint(paper):
    types = paper.get("publicationTypes") or []
    venue = (paper.get("venue") or "").lower()
    return (
        "Preprint" in types
        or "arxiv" in venue
        or "biorxiv" in venue
        or "medrxiv" in venue
    )


def render_item(paper):
    title = (paper.get("title") or "").strip()
    url   = paper_url(paper)
    ref   = " · ".join(filter(None, [
        short_authors(paper),
        f"<em>{venue_display(paper)}</em>" if venue_display(paper) else "",
        str(paper.get("year", "")),
    ]))
    return (
        f'          <li class="pub-item">\n'
        f'            <div class="pub-title">'
        f'<a href="{url}" target="_blank" rel="noopener">{title}</a></div>\n'
        f'            <div class="pub-ref">{ref}</div>\n'
        f'          </li>'
    )


def main():
    journals, preprints = [], []
    seen = set()

    for pi in PIS:
        print(f"Fetching papers for {pi['name']}...")
        papers = fetch_papers(pi["author_id"])
        time.sleep(1)  # be polite to the API

        for p in papers:
            year = p.get("year") or 0
            title = (p.get("title") or "").strip().lower()
            if year < MIN_YEAR or not title or title in seen:
                continue
            seen.add(title)
            (preprints if is_preprint(p) else journals).append(p)

    journals  = sorted(journals,  key=lambda p: p.get("year") or 0, reverse=True)[:MAX_JOURNAL]
    preprints = sorted(preprints, key=lambda p: p.get("year") or 0, reverse=True)[:MAX_PREPRINT]

    print(f"Found {len(journals)} journal articles, {len(preprints)} preprints.")

    with open("index.html", encoding="utf-8") as f:
        html = f.read()

    def replace_list(label_text, items, content):
        pattern = re.compile(
            r'(<div class="pub-section-label"[^>]*>' + re.escape(label_text) +
            r'</div>\s*<ol class="pub-list">)(.*?)(</ol>)',
            re.DOTALL,
        )
        replacement = (
            r'\g<1>' + "\n" +
            "\n".join(render_item(p) for p in items) +
            "\n        " + r'\g<3>'
        )
        return pattern.sub(replacement, content)

    if preprints:
        html = replace_list("Preprints", preprints, html)
    if journals:
        html = replace_list("Journal Articles", journals, html)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("index.html updated.")


if __name__ == "__main__":
    main()
