# AI Yesterday

A premium daily AI briefing page.

What it does:

- Collects yesterday's AI news from high-signal RSS feeds
- Ranks stories by likely importance
- Converts technical headlines into plain-English summaries
- Shows why each item matters
- Keeps a dated history in JSON so trends can be traced back
- Runs as a static GitHub Pages site with no backend

Files:

- `index.html` - single-file premium UI
- `scripts/collect_ai_news.py` - stdlib collector and scorer
- `data/digest.json` - latest daily digest
- `.github/workflows/daily-digest.yml` - scheduled update job

Run locally:

```bash
python3 scripts/collect_ai_news.py
python3 -m http.server 8777
```

Then open `http://localhost:8777`.

Deployment idea:

1. Create a private repo during development.
2. Enable GitHub Pages when ready to share.
3. GitHub Actions updates `data/digest.json` every morning.
4. Optional later upgrade: add an OpenRouter or OpenAI key to generate better layman summaries from article text.
