# AI Yesterday - Daily AI Briefing

[![Live Site](https://img.shields.io/badge/Live%20Site-sahirvhora.github.io%2Fai--yesterday-gold)](https://sahirvhora.github.io/ai-yesterday/)
[![Updated](https://img.shields.io/badge/Updated-Daily-blue)](https://sahirvhora.github.io/ai-yesterday/)
[![Signals](https://img.shields.io/badge/Curated-Daily-green)](https://sahirvhora.github.io/ai-yesterday/)
[![Sources](https://img.shields.io/badge/Sources-9%20feeds-purple)](https://sahirvhora.github.io/ai-yesterday/)
[![AI Summary](https://img.shields.io/badge/Summary-OpenRouter%20AI-teal)](https://sahirvhora.github.io/ai-yesterday/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**A daily AI briefing that translates yesterday's most useful AI developments into plain-English summaries, importance flags, source links and searchable history.**

**[Open the briefing -](https://sahirvhora.github.io/ai-yesterday/)**

---

## What It Does

AI moves too fast for normal people to track manually. AI Yesterday collects high-signal RSS feeds from trusted sources every day, ranks stories by likely importance, and converts technical headlines into plain-English explanations:

| Feature | What It Means |
|---------|--------------|
| **Plain-English summaries** | Every story is translated into clear, jargon-free language |
| **Importance flags** | Critical, High, Medium or Low - so you know what's worth your attention |
| **Source links** | Every item links back to the original article |
| **Searchable history** | All past digests archived by date, searchable from the page |
| **Weekly trends** | See which categories are heating up over the past 7 days |
| **Category pages** | Browse by Models, Products, Research, Business, or Policy |
| **Source quality scores** | Each RSS feed is scored so noisy sources are visible |

**[Read yesterday's briefing -](https://sahirvhora.github.io/ai-yesterday/)**

---

## Preview

![AI Yesterday social preview](preview.png)

Three premium social preview variants are included:

- `preview-linear.png` - dark Linear-style command centre (active as `preview.png`)
- `preview-vercel.png` - clean white Vercel-style launch card
- `preview-superhuman.png` - luxury purple Superhuman-style editorial card

---

## Why It Exists

Building on the same idea as my [Year 4 Prep](https://sahirvhora.github.io/year4-prep/) project - information you need, organised automatically, so you don't have to hunt for it yourself. AI news is the same problem: too many sources, too little signal, and nobody curating it with a non-technical reader in mind.

The site runs as a static GitHub Pages page with no backend. A scheduled GitHub Action collects, scores, enriches (via OpenRouter), and archives the digest daily.

---

## Files

| File | Purpose |
|------|---------|
| `index.html` | Single-file premium UI (dark/light theme, search, archive) |
| `preview.png` | Active 1280x640 social preview image (Linear variant) |
| `preview-linear.png` | Dark Linear-style preview variant |
| `preview-vercel.png` | Clean white Vercel-style preview variant |
| `preview-superhuman.png` | Purple Superhuman-style preview variant |
| `scripts/collect_ai_news.py` | Collector, scorer, history archiver, OpenRouter enricher |
| `scripts/generate_preview.py` | Preview image generator using Pillow |
| `data/digest.json` | Latest daily digest |
| `data/history/*.json` | Archived daily snapshots |

---

## Run Locally

```bash
python3 scripts/collect_ai_news.py
python3 -m http.server 8777
```

Then open `http://localhost:8777`.

---

## Optional OpenRouter Enrichment

Set environment variables before running the collector:

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="openrouter/free"
python3 scripts/collect_ai_news.py
```

For GitHub Actions, add `OPENROUTER_API_KEY` as a repository secret. The scheduled workflow enriches top items and stops on rate limits so it does not burn through the free quota. No key = falls back to rules-based summaries.

---

## Generate Preview Images

```bash
pip install pillow
python3 scripts/generate_preview.py
```

---

## Data Sources

Feeds monitored daily for new signals. Source quality is scored and visible on the site.

*Hacker News AI, MIT Technology Review AI, Ars Technica AI, VentureBeat AI, The Verge AI, OpenAI, Hugging Face, Google DeepMind, arXiv AI*

---

*Powered by GitHub Actions and OpenRouter. Built because busy humans deserve to understand AI without drowning in AI news.*
