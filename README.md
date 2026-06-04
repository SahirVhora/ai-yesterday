# AI Yesterday

![AI Yesterday social preview](preview.png)

A premium daily AI briefing page that turns fast-moving artificial intelligence news into plain-English summaries, importance flags, source links and searchable history.

Live site: https://sahirvhora.github.io/ai-yesterday/

## What it does

- Collects yesterday's AI news from high-signal RSS feeds
- Ranks stories by likely importance: Critical, High, Medium or Low
- Converts technical headlines into plain-English summaries
- Optionally upgrades summaries using OpenRouter when `OPENROUTER_API_KEY` is available
- Explains why each item matters for busy non-specialists
- Keeps dated history in JSON so trends can be traced back
- Shows a rolling weekly trend view by category
- Scores source quality so noisy or unavailable feeds are visible
- Provides category pages for models, products, research, business and policy
- Runs as a static GitHub Pages site with no backend

## Preview variants

The repo includes three premium social preview variants:

- `preview-linear.png` - dark Linear-style command centre, currently used as `preview.png`
- `preview-vercel.png` - clean white Vercel-style launch card
- `preview-superhuman.png` - luxury purple Superhuman-style editorial card

## Why it exists

AI is moving too quickly for normal people to track manually. AI Yesterday is designed as a calm daily briefing: fewer links, better context, and clear impact labels.

## Files

- `index.html` - single-file premium UI
- `preview.png` - active 1280x640 social preview image
- `preview-linear.png`, `preview-vercel.png`, `preview-superhuman.png` - premium preview variants
- `scripts/collect_ai_news.py` - stdlib collector, scorer, history archiver and optional OpenRouter enricher
- `scripts/generate_preview.py` - preview image generator using Pillow
- `data/digest.json` - latest daily digest
- `data/history/*.json` - archived daily snapshots
- `.github/workflows/daily-digest.yml` - scheduled update job

## Run locally

```bash
python3 scripts/collect_ai_news.py
python3 -m http.server 8777
```

Then open `http://localhost:8777`.

## Optional OpenRouter summaries

Set an API key before running the collector:

```bash
export OPENROUTER_API_KEY="..."
export OPENROUTER_MODEL="meta-llama/llama-3.1-8b-instruct:free"
python3 scripts/collect_ai_news.py
```

If no key is present, the collector falls back to rules-based summaries.

## Generate preview images

```bash
uv run --with pillow python scripts/generate_preview.py
```

## Roadmap status

Done:

- OpenRouter-ready layman summaries
- Weekly trend view
- Source quality scoring
- Category pages
- Multiple premium social preview PNGs

Next:

- Add newsletter or Telegram delivery option
- Add deeper article body extraction
- Add per-source mute and boost configuration
