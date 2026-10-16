# Changelog Feed

A static, GitHub Pages-ready changelog aggregator for **GitHub Copilot surfaces and supported IDEs**, including **GitHub Copilot App**. Entries are scored by importance and include a Copilot feature parity matrix.

## Sources

| Source | Feed | What it tracks |
|---|---|---|
| **GitHub Platform** | RSS | Copilot, Actions, Security, Enterprise, and more |
| **GitHub Copilot App** | GitHub Releases API | Official `github/app` releases, including new features, improvements, fixes, and prereleases |
| **VS Code** | Page scrape | Monthly release notes — editor, extensions, Copilot |
| **Visual Studio** | Page scrape | GA and Preview release notes |
| **JetBrains** | Blog RSS | IntelliJ, PyCharm, WebStorm, and all JetBrains IDEs |
| **Xcode** | Apple RSS | Xcode releases (filtered from Apple developer news) |
| **Neovim** | GitHub API | Neovim releases from `neovim/neovim` |
| **Eclipse** | Planet RSS | Eclipse IDE-related posts |

Items mentioning **Copilot** are automatically tagged across all sources for cross-cutting filtering. The **GitHub Copilot App** filter includes both app releases and app-related GitHub changelog announcements without duplicating those announcements or losing their source attribution.

App releases are fetched in one request (up to 100 releases), then filtered to the same 90-day window as other sources. Independent sources load concurrently with bounded network timeouts and a five-minute in-process cache. A failed source is logged and does not prevent other sources from building.

## Quick Start

```bash
pip install -r requirements.txt

# Build the static data
python -m src.build

# Preview locally
cd docs && python -m http.server
```

Open [http://localhost:8000](http://localhost:8000).

## GitHub Pages

1. Push to GitHub
2. Go to **Settings → Pages** → set source to **Deploy from branch**, branch `main`, folder `/docs`
3. The GitHub Actions workflow rebuilds `data.json` every 6 hours automatically

## Features

- **Importance scoring** — each entry gets a 0–100 score based on keywords (security, breaking changes, Copilot, new features, etc.)
- **Severity bands** — Critical (75+), High (50–74), Medium (25–49), Low (<25) with color-coded badges
- **Feature parity matrix** — table comparing GitHub Copilot App, VS Code, VS Code Insiders, Visual Studio, JetBrains, Neovim, Eclipse, and Xcode; horizontally scrollable on small screens
- **App workflows** — tracks parallel isolated sessions, session modes, BYOK, scheduled automations, canvases, and platform-limited computer use
- **Evidence-aware support** — app capabilities reference GitHub's documentation with a review date; `?` means unverified, not unsupported. Coverage percentages exclude unknown cells; limited support counts as half. IDE-only completions are not assumed to exist in the app, and app workflows are not assumed absent from IDEs
- **Filter by source or surface** — GitHub, Copilot, GitHub Copilot App, VS Code, Visual Studio, JetBrains, Xcode, Neovim, Eclipse; filters and search can be shared via URL
- **Search** — instant client-side filtering (press `/` to focus, `Esc` to clear)
- **Dark mode** — follows system preference
- **Zero dependencies at runtime** — the page is pure HTML/CSS/JS reading a static JSON file
- **Atom feed** — `docs/feed.xml` is rebuilt and published alongside `data.json` every six hours

The generated parity payload retains `ides` for compatibility and adds `surfaces` for the complete comparison. Entries can carry `surfaces` independently of their original `source`.

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q
python -m src.build
```

CI runs the test suite before rebuilding and publishing the static JSON and Atom feed. `docs/index.html` is the active frontend; `src/static/index.html` is a legacy, unused page.

## Project Structure

```
src/
  build.py      Entry point: python -m src.build
  main.py       Build logic (fetches feeds → scores → writes JSON)
  feeds.py      Concurrent feed fetchers for all 8 sources
  models.py     Pydantic model (ChangeEntry with score/severity)
  scorer.py     Keyword-based importance scoring
  parity.py     Copilot surface feature parity and evidence metadata
docs/
  index.html    Static page (served by GitHub Pages)
  data.json     Generated feed data (committed by CI)
  feed.xml      Generated Atom feed (committed by CI)
.github/
  workflows/
    build.yml   Rebuilds data.json every 6 hours
```
