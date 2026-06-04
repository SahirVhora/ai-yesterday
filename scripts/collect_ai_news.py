#!/usr/bin/env python3
"""Collect high-signal AI news and write data/digest.json.
Stdlib only so it can run in GitHub Actions without setup.
"""
from __future__ import annotations

import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "digest.json"

SOURCES = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "tier": 5},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "tier": 5},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "tier": 4},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "tier": 4},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "tier": 3},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "tier": 3},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "tier": 3},
    {"name": "Hacker News AI", "url": "https://hnrss.org/newest?q=AI+OR+LLM+OR+OpenAI+OR+Anthropic&points=100", "tier": 2},
    {"name": "arXiv AI", "url": "https://rss.arxiv.org/rss/cs.AI", "tier": 2},
]

CATEGORY_RULES = [
    ("Models", ["model", "llm", "gpt", "claude", "gemini", "llama", "mistral", "reasoning", "benchmark"]),
    ("Products", ["app", "agent", "assistant", "copilot", "tool", "api", "launch", "feature"]),
    ("Research", ["paper", "research", "arxiv", "study", "training", "inference", "eval", "dataset"]),
    ("Business", ["funding", "startup", "acquisition", "deal", "revenue", "enterprise", "market"]),
    ("Policy", ["regulation", "policy", "safety", "copyright", "lawsuit", "government", "act"]),
]

IMPACT_TERMS = {
    "Critical": ["openai", "anthropic", "google", "deepmind", "microsoft", "nvidia", "security", "safety", "regulation", "major", "new model", "released"],
    "High": ["model", "agent", "api", "benchmark", "enterprise", "research", "funding", "lawsuit"],
    "Medium": ["tool", "feature", "startup", "dataset", "preview", "integration"],
}

FALLBACK_ITEMS = [
    {
        "title": "OpenAI, Anthropic, Google and open-source labs continue rapid model and agent releases",
        "source": "AI Yesterday sample",
        "url": "https://openai.com/news/",
        "published": "2026-06-03T09:00:00Z",
        "category": "Models",
        "importance": "Critical",
        "score": 96,
        "summary": "The biggest labs are improving models, tools and agent workflows quickly. For non-technical users, this means AI assistants are becoming better at doing multi-step work, not just answering questions.",
        "why_it_matters": "Useful for people who want practical productivity gains, but it also means skills and business processes need regular review.",
    },
    {
        "title": "AI coding tools keep moving from autocomplete to autonomous development",
        "source": "AI Yesterday sample",
        "url": "https://github.blog/ai-and-ml/",
        "published": "2026-06-03T12:30:00Z",
        "category": "Products",
        "importance": "High",
        "score": 88,
        "summary": "Developer tools are increasingly able to plan, edit, test and explain code changes. The shift is from typing assistance to delegated work.",
        "why_it_matters": "Small teams can build faster, but review, testing and security checks become more important.",
    },
    {
        "title": "AI regulation and safety debates are becoming part of normal product planning",
        "source": "AI Yesterday sample",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/",
        "published": "2026-06-03T16:00:00Z",
        "category": "Policy",
        "importance": "Medium",
        "score": 72,
        "summary": "Governments and companies are paying closer attention to how AI systems are tested, explained and controlled.",
        "why_it_matters": "Businesses using AI need simple governance: what data is used, who checks outputs, and where humans stay accountable.",
    },
]


def clean_text(value: str | None) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "AI-Yesterday/0.1"})
    with urllib.request.urlopen(req, timeout=12) as response:
        return response.read()


def item_text(title: str, description: str) -> str:
    return f"{title} {description}".lower()


def classify(title: str, description: str) -> str:
    text = item_text(title, description)
    for category, terms in CATEGORY_RULES:
        if any(term in text for term in terms):
            return category
    return "Signals"


def importance(title: str, description: str, tier: int) -> tuple[str, int]:
    text = item_text(title, description)
    score = tier * 12
    for label, terms in IMPACT_TERMS.items():
        hits = sum(1 for term in terms if term in text)
        score += hits * {"Critical": 10, "High": 7, "Medium": 4}[label]
    if score >= 82:
        return "Critical", min(score, 99)
    if score >= 62:
        return "High", min(score, 89)
    if score >= 42:
        return "Medium", min(score, 74)
    return "Low", min(score, 55)


def layman_summary(title: str, description: str, category: str) -> str:
    base = description if len(description) > 80 else title
    base = clean_text(base)
    if len(base) > 220:
        base = base[:217].rsplit(" ", 1)[0] + "..."
    prefixes = {
        "Models": "In simple terms, this is about making AI systems more capable or cheaper to run.",
        "Products": "In simple terms, this is about turning AI research into tools people can actually use.",
        "Research": "In simple terms, researchers are testing a new way to make AI better or safer.",
        "Business": "In simple terms, money and strategy are moving toward this part of AI.",
        "Policy": "In simple terms, this affects the rules, risks or responsibilities around AI.",
        "Signals": "In simple terms, this is a useful signal about where AI is heading.",
    }
    return f"{prefixes.get(category, prefixes['Signals'])} {base}"


def why_it_matters(category: str, imp: str) -> str:
    if imp == "Critical":
        return "Track this closely because it may affect products, skills, costs or competitive advantage within weeks."
    if category == "Policy":
        return "Important for anyone using AI at work because compliance and data handling expectations are changing."
    if category == "Products":
        return "Worth testing because it could reduce manual work or create a new workflow for non-technical users."
    if category == "Research":
        return "Useful background signal. It may not matter today, but it can shape tools that appear later."
    return "Good trend signal. Save it if it connects to your work, learning or product ideas."


def parse_feed(source: dict) -> list[dict]:
    try:
        root = ET.fromstring(fetch(source["url"]))
    except Exception as exc:
        print(f"WARN feed failed: {source['name']}: {exc}", file=sys.stderr)
        return []
    entries = []
    channel_items = root.findall(".//item")
    atom_entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    for item in channel_items:
        title = clean_text(item.findtext("title"))
        link = clean_text(item.findtext("link"))
        description = clean_text(item.findtext("description") or item.findtext("summary"))
        published = parse_date(item.findtext("pubDate") or item.findtext("published") or item.findtext("updated"))
        entries.append(make_entry(source, title, link, description, published))
    for item in atom_entries:
        title = clean_text(item.findtext("{http://www.w3.org/2005/Atom}title"))
        link_el = item.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        description = clean_text(item.findtext("{http://www.w3.org/2005/Atom}summary") or item.findtext("{http://www.w3.org/2005/Atom}content"))
        published = parse_date(item.findtext("{http://www.w3.org/2005/Atom}published") or item.findtext("{http://www.w3.org/2005/Atom}updated"))
        entries.append(make_entry(source, title, link, description, published))
    return [e for e in entries if e["title"] and e["url"]]


def make_entry(source: dict, title: str, link: str, description: str, published: datetime) -> dict:
    category = classify(title, description)
    imp, score = importance(title, description, source["tier"])
    return {
        "title": title,
        "source": source["name"],
        "url": link,
        "published": published.isoformat().replace("+00:00", "Z"),
        "category": category,
        "importance": imp,
        "score": score,
        "summary": layman_summary(title, description, category),
        "why_it_matters": why_it_matters(category, imp),
    }


def collect() -> dict:
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).date()
    start = datetime.combine(yesterday, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    items = []
    seen = set()
    feed_count = 0
    for source in SOURCES:
        feed_items = parse_feed(source)
        feed_count += len(feed_items)
        for item in feed_items:
            dt = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
            key = re.sub(r"\W+", "", item["title"].lower())[:90]
            if key in seen:
                continue
            if start <= dt < end:
                seen.add(key)
                items.append(item)
    if not items:
        items = FALLBACK_ITEMS
    items.sort(key=lambda x: (x["score"], x["published"]), reverse=True)
    items = items[:24]
    categories = sorted({item["category"] for item in items})
    return {
        "metadata": {
            "name": "AI Yesterday",
            "generated_at": now.isoformat().replace("+00:00", "Z"),
            "coverage_date": yesterday.isoformat(),
            "source_count": len(SOURCES),
            "feed_items_scanned": feed_count,
            "item_count": len(items),
            "mode": "live" if items != FALLBACK_ITEMS else "fallback_sample",
        },
        "items": items,
        "categories": categories,
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = collect()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT} with {data['metadata']['item_count']} items ({data['metadata']['mode']})")


if __name__ == "__main__":
    main()
