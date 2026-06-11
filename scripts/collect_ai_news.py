#!/usr/bin/env python3
"""Collect high-signal AI news and write data/digest.json.
Stdlib only so it can run in GitHub Actions without setup.
"""
from __future__ import annotations

import email.utils
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "digest.json"
HISTORY_DIR = ROOT / "data" / "history"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_FALLBACK_MODEL = os.environ.get("OPENROUTER_FALLBACK_MODEL", "openrouter/free")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MAX_ITEMS = int(os.environ.get("OPENROUTER_MAX_ITEMS", "4"))


class OpenRouterRateLimited(Exception):
    pass

SOURCES = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "tier": 5},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "tier": 5},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "tier": 4},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "tier": 4},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "tier": 3},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "tier": 3},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "tier": 3},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "tier": 3},
    {"name": "WIRED", "url": "https://www.wired.com/feed/rss", "tier": 3},
    {"name": "AI News", "url": "https://www.artificialintelligence-news.com/feed/", "tier": 2},
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
    value = value.replace("\u2014", "-").replace("\u2013", "-")
    value = re.sub(r"Article URL:\s*https?://\S+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"Comments URL:\s*https?://\S+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"#\s*Comments:\s*\d+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"Points:\s*\d+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value or ""))


def clamp_words(value: str, max_words: int) -> str:
    words = re.findall(r"\S+", clean_text(value))
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "."


def extract_json_object(value: str) -> dict:
    text = value.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_briefing_fields(value: str) -> dict:
    try:
        parsed = extract_json_object(value)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    text = clean_text(value)
    summary = ""
    why = ""
    summary_match = re.search(r"(?:summary|plain english)\s*[:\-]\s*(.+?)(?:\s+why(?: it matters)?\s*[:\-]|$)", text, flags=re.IGNORECASE)
    why_match = re.search(r"why(?: it matters)?\s*[:\-]\s*(.+)$", text, flags=re.IGNORECASE)
    if summary_match:
        summary = summary_match.group(1).strip()
    if why_match:
        why = why_match.group(1).strip()
    if not summary and not why:
        quote_summary = re.search(r'"summary"\s*:\s*"([^"]+)', value, flags=re.IGNORECASE | re.DOTALL)
        quote_why = re.search(r'"why_it_matters"\s*:\s*"([^"]+)', value, flags=re.IGNORECASE | re.DOTALL)
        summary = clean_text(quote_summary.group(1)) if quote_summary else ""
        why = clean_text(quote_why.group(1)) if quote_why else ""
    return {"summary": summary, "why_it_matters": why}


def has_weak_briefing_text(summary: str, why: str, title: str) -> bool:
    combined = f"{summary} {why}".lower()
    generic_phrases = [
        "this ai news item",
        "this article",
        "the article",
        "busy non-technical reader",
        "staying informed",
        "rapidly evolving ai landscape",
    ]
    title_words = {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 3}
    summary_words = set(re.findall(r"[a-z0-9]+", summary.lower()))
    title_overlap = len(title_words & summary_words) / max(len(title_words), 1)
    return (
        any(phrase in combined for phrase in generic_phrases)
        or "http" in combined
        or word_count(summary) < 18
        or word_count(why) < 14
        or title_overlap > 0.82
    )


def briefing_quality_score(item: dict) -> int:
    summary = clean_text(item.get("summary"))
    why = clean_text(item.get("why_it_matters"))
    score = 100
    if not summary or not why:
        return 0
    if word_count(summary) < 18:
        score -= 25
    if word_count(summary) > 55:
        score -= 15
    if word_count(why) < 14:
        score -= 20
    if "http" in f"{summary} {why}".lower():
        score -= 25
    if has_weak_briefing_text(summary, why, item.get("title", "")):
        score -= 20
    if item.get("summary_engine") == "openrouter":
        score += 5
    return max(0, min(100, score))


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = value.strip()
    iso_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(iso_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
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


def source_quality(source: dict, feed_items: list[dict], selected_count: int) -> dict:
    scanned = len(feed_items)
    signal_ratio = round(selected_count / scanned, 3) if scanned else 0
    quality = source["tier"] * 10 + selected_count * 7
    if scanned > 300 and selected_count < 2:
        quality -= 8
    if selected_count >= 3:
        quality += 10
    return {
        "name": source["name"],
        "tier": source["tier"],
        "feed_items_scanned": scanned,
        "selected_items": selected_count,
        "signal_ratio": signal_ratio,
        "quality_score": max(0, min(100, quality)),
        "status": "active" if scanned else "unavailable",
    }


def request_openrouter(item: dict, model: str) -> dict:
    prompt = build_openrouter_prompt(item)
    body = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert AI industry editor. You turn raw AI headlines into "
                    "clear, specific, non-hyped briefings for busy professionals."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.15,
        "max_tokens": 220,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sahirvhora.github.io/ai-yesterday/",
            "X-Title": "AI Yesterday",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=18) as response:
        return json.loads(response.read().decode("utf-8"))


def build_openrouter_prompt(item: dict) -> str:
    return (
        "Create a concise daily briefing entry for a smart non-technical reader. "
        "Return only valid JSON with keys summary and why_it_matters.\n\n"
        "Quality rules:\n"
        "- summary: 28-45 words, plain English, specific to the story, no hype.\n"
        "- why_it_matters: 18-32 words, explain the practical implication.\n"
        "- Do not mention that this is an article, feed item, briefing, or AI news item.\n"
        "- Do not include URLs, markdown, source labels, or invented facts.\n"
        "- Use British English and a calm analytical tone.\n\n"
        f"Title: {item['title']}\nSource: {item['source']}\nCategory: {item['category']}\n"
        f"Importance: {item['importance']} ({item['score']}/100)\n"
        f"Published: {item['published']}\n"
        f"Current rules summary: {item['summary']}\n"
        f"Current why it matters: {item['why_it_matters']}"
    )


def parse_openrouter_briefing(item: dict, payload: dict) -> dict | None:
    if "choices" not in payload:
        raise ValueError(payload.get("error", {}).get("message") or "OpenRouter response missing choices")
    message = payload["choices"][0].get("message", {})
    content = message.get("content")
    if isinstance(content, list):
        content = " ".join(str(part.get("text") or part.get("content") or part) for part in content)
    if not content:
        raise ValueError("OpenRouter response had no content")
    parsed = extract_briefing_fields(content)
    if parsed.get("summary") and parsed.get("why_it_matters"):
        summary = clamp_words(parsed["summary"], 55)
        why = clamp_words(parsed["why_it_matters"], 38)
        if has_weak_briefing_text(summary, why, item["title"]):
            print(f"WARN OpenRouter weak output rejected: {item['title'][:50]}", file=sys.stderr)
            return None
        return {"summary": summary, "why_it_matters": why}
    return None


def call_openrouter(item: dict) -> dict | None:
    if not OPENROUTER_KEY:
        return None
    try:
        return parse_openrouter_briefing(item, request_openrouter(item, OPENROUTER_MODEL))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise OpenRouterRateLimited("OpenRouter rate limit reached")
        if exc.code == 402 and OPENROUTER_MODEL != OPENROUTER_FALLBACK_MODEL:
            print(f"WARN OpenRouter paid model unavailable; retrying free router for {item['title'][:50]}", file=sys.stderr)
            try:
                return parse_openrouter_briefing(item, request_openrouter(item, OPENROUTER_FALLBACK_MODEL))
            except urllib.error.HTTPError as retry_exc:
                if retry_exc.code == 429:
                    raise OpenRouterRateLimited("OpenRouter fallback rate limit reached")
                print(f"WARN OpenRouter fallback failed for {item['title'][:50]}: HTTP {retry_exc.code}", file=sys.stderr)
                return None
            except Exception as retry_exc:
                print(f"WARN OpenRouter fallback failed for {item['title'][:50]}: {retry_exc}", file=sys.stderr)
                return None
        print(f"WARN OpenRouter failed for {item['title'][:50]}: HTTP {exc.code}", file=sys.stderr)
    except Exception as exc:
        print(f"WARN OpenRouter failed for {item['title'][:50]}: {exc}", file=sys.stderr)
    return None


def enrich_with_openrouter(items: list[dict]) -> dict:
    stats = {
        "enabled": bool(OPENROUTER_KEY),
        "attempted": 0,
        "enriched": 0,
        "model": OPENROUTER_MODEL if OPENROUTER_KEY else None,
    }
    if not OPENROUTER_KEY:
        return stats
    for item in items[:OPENROUTER_MAX_ITEMS]:
        stats["attempted"] += 1
        try:
            improved = call_openrouter(item)
        except OpenRouterRateLimited as exc:
            print(f"WARN {exc}; stopping enrichment for this run", file=sys.stderr)
            break
        if improved:
            item.update(improved)
            item["summary_engine"] = "openrouter"
            item["summary_model"] = OPENROUTER_MODEL
            stats["enriched"] += 1
    return stats


def build_weekly_trends(current: dict) -> list[dict]:
    totals: dict[str, dict] = {}
    files = sorted(HISTORY_DIR.glob("*.json"))[-6:]
    datasets = []
    for path in files:
        try:
            datasets.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    datasets.append(current)
    for data in datasets:
        for item in data.get("items", []):
            category = item.get("category") or "Signals"
            bucket = totals.setdefault(category, {"category": category, "items": 0, "critical": 0, "score": 0, "sources": set()})
            bucket["items"] += 1
            bucket["score"] += int(item.get("score") or 0)
            bucket["sources"].add(item.get("source") or "Unknown")
            if item.get("importance") == "Critical":
                bucket["critical"] += 1
    trends = []
    for bucket in totals.values():
        items = bucket["items"]
        trends.append({
            "category": bucket["category"],
            "items": items,
            "critical": bucket["critical"],
            "average_score": round(bucket["score"] / items, 1) if items else 0,
            "source_count": len(bucket["sources"]),
            "plain_english": trend_explanation(bucket["category"], items, bucket["critical"]),
        })
    trends.sort(key=lambda row: (row["critical"], row["items"], row["average_score"]), reverse=True)
    return trends[:8]


def trend_explanation(category: str, items: int, critical: int) -> str:
    if critical:
        return f"{category} produced {critical} critical signal{'s' if critical != 1 else ''}. This is worth watching closely this week."
    if items >= 5:
        return f"{category} is a busy area this week. Expect incremental product or research movement rather than one big headline."
    return f"{category} has a lighter signal this week. Useful context, but not the main priority."


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
        link = html.unescape((item.findtext("link") or "").strip())
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


def collect(coverage_date=None, allow_fallback: bool = True) -> dict:
    now = datetime.now(timezone.utc)
    target_date = coverage_date or (now - timedelta(days=1)).date()
    start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    items = []
    seen = set()
    feed_count = 0
    source_scores = []
    fallback_used = False
    for source in SOURCES:
        feed_items = parse_feed(source)
        feed_count += len(feed_items)
        selected_for_source = 0
        for item in feed_items:
            dt = datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
            key = re.sub(r"\W+", "", item["title"].lower())[:90]
            if key in seen:
                continue
            if start <= dt < end:
                seen.add(key)
                selected_for_source += 1
                items.append(item)
        source_scores.append(source_quality(source, feed_items, selected_for_source))
    if not items and allow_fallback:
        items = FALLBACK_ITEMS
        fallback_used = True
        source_scores = [{"name": "Fallback sample", "tier": 1, "feed_items_scanned": 0, "selected_items": len(items), "signal_ratio": 1, "quality_score": 25, "status": "fallback"}]
    items.sort(key=lambda x: (x["score"], x["published"]), reverse=True)
    items = items[:24]
    openrouter_stats = enrich_with_openrouter(items)
    for item in items:
        item.setdefault("summary_engine", "rules")
        item["briefing_quality_score"] = briefing_quality_score(item)
    average_quality = round(sum(item["briefing_quality_score"] for item in items) / len(items), 1) if items else 0
    categories = sorted({item["category"] for item in items})
    data = {
        "metadata": {
            "name": "AI Yesterday",
            "generated_at": now.isoformat().replace("+00:00", "Z"),
            "coverage_date": target_date.isoformat(),
            "source_count": len(SOURCES),
            "feed_items_scanned": feed_count,
            "item_count": len(items),
            "mode": "fallback_sample" if fallback_used else ("live" if items else "no_items"),
            "summary_engine": "openrouter" if openrouter_stats["enriched"] else "rules",
            "openrouter_enabled": openrouter_stats["enabled"],
            "openrouter_items_attempted": openrouter_stats["attempted"],
            "openrouter_items_enriched": openrouter_stats["enriched"],
            "openrouter_model": openrouter_stats["model"],
            "briefing_quality_score": average_quality,
        },
        "items": items,
        "categories": categories,
        "source_quality": sorted(source_scores, key=lambda row: row["quality_score"], reverse=True),
    }
    data["weekly_trends"] = build_weekly_trends(data)
    return data


def parse_iso_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def date_range(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def rebuild_history_index() -> None:
    archives = []
    for path in sorted(HISTORY_DIR.glob("20*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("metadata", {})
        except Exception:
            continue
        archives.append({
            "date": meta.get("coverage_date") or path.stem,
            "file": f"data/history/{path.name}",
            "item_count": meta.get("item_count", len(data.get("items", []))),
            "critical_count": sum(1 for item in data.get("items", []) if item.get("importance") == "Critical"),
            "mode": meta.get("mode", "unknown"),
            "generated_at": meta.get("generated_at"),
        })
    tmp_idx = HISTORY_DIR / "index.json.tmp"
    tmp_idx.write_text(json.dumps({"archives": archives}, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_idx.replace(HISTORY_DIR / "index.json")


def write_digest(data: dict, write_current: bool = True) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history_path = HISTORY_DIR / f"{data['metadata']['coverage_date']}.json"
    # Never overwrite the live digest with an empty result — keep the last real one visible
    if write_current and data["metadata"].get("item_count", 0) == 0:
        write_current = False
        print(f"INFO No items for {data['metadata']['coverage_date']} — keeping previous digest.json unchanged", file=sys.stderr)
    if write_current:
        tmp_out = OUT.with_suffix(".json.tmp")
        tmp_out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_out.replace(OUT)
    tmp_hist = history_path.with_suffix(".json.tmp")
    tmp_hist.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_hist.replace(history_path)
    rebuild_history_index()
    if write_current:
        print(f"Wrote {OUT} with {data['metadata']['item_count']} items ({data['metadata']['mode']})")
    print(f"Archived {history_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect AI Yesterday digest data.")
    parser.add_argument("--date", help="Coverage date to collect, format YYYY-MM-DD. Defaults to yesterday UTC.")
    parser.add_argument("--start", help="First coverage date for backfill, format YYYY-MM-DD.")
    parser.add_argument("--end", help="Last coverage date for backfill, format YYYY-MM-DD.")
    parser.add_argument("--history-only", action="store_true", help="Write only data/history/<date>.json, not data/digest.json.")
    parser.add_argument("--no-fallback", action="store_true", help="For backfills, write an empty no_items digest instead of sample data when no live items match.")
    args = parser.parse_args()

    if args.start or args.end:
        if not args.start or not args.end:
            parser.error("--start and --end must be used together")
        start = parse_iso_date(args.start)
        end = parse_iso_date(args.end)
        if end < start:
            parser.error("--end must be on or after --start")
        for target_date in date_range(start, end):
            data = collect(target_date, allow_fallback=not args.no_fallback)
            write_digest(data, write_current=not args.history_only)
        return

    target_date = parse_iso_date(args.date) if args.date else None
    data = collect(target_date, allow_fallback=not args.no_fallback)
    write_digest(data, write_current=not args.history_only)


if __name__ == "__main__":
    main()
