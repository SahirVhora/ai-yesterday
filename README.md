# AI Yesterday

![AI Yesterday social preview](preview.png)

A premium daily AI briefing page that turns fast-moving artificial intelligence news into plain-English summaries, importance flags, source links and searchable history.

Live site: https://sahirvhora.github.io/ai-yesterday/

## What it does

- Collects yesterday's AI news from high-signal RSS feeds
- Ranks stories by likely importance: Critical, High, Medium or Low
- Converts technical headlines into plain-English summaries
- Explains why each item matters for busy non-specialists
- Keeps dated history in JSON so trends can be traced back
- Runs as a static GitHub Pages site with no backend

## Why it exists

AI is moving too quickly for normal people to track manually. AI Yesterday is designed as a calm daily briefing: fewer links, better context, and clear impact labels.

## Files

- `index.html` - single-file premium UI
- `preview.png` - 1280x640 social preview image
- `scripts/collect_ai_news.py` - stdlib collector and scorer
- `scripts/generate_preview.py` - optional preview image generator using Pillow
- `data/digest.json` - latest daily digest
- `.github/workflows/daily-digest.yml` - scheduled update job

## Run locally

```bash
python3 scripts/collect_ai_news.py
python3 -m http.server 8777
```

Then open `http://localhost:8777`.

## Generate the preview image

```bash
uv run --with pillow python scripts/generate_preview.py
```

## Roadmap

- Add OpenRouter-powered layman summaries from article text
- Add weekly trend view
- Add source quality scoring
- Add category pages for models, products, policy and research
- Add newsletter or Telegram delivery option
