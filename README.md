# Changelog Feed

A static, GitHub Pages-ready changelog aggregator for every **GitHub Copilot-supported IDE**. Entries are scored by importance and include a Copilot feature parity matrix across all IDEs.

## Sources

| Source | Feed | What it tracks |
|---|---|---|
| **GitHub Platform** | RSS | Copilot, Actions, Security, Enterprise, and more |
| **VS Code** | Page scrape | Monthly release notes — editor, extensions, Copilot |
| **Visual Studio** | Page scrape | GA and Preview release notes |
| **JetBrains** | Blog RSS | IntelliJ, PyCharm, WebStorm, and all JetBrains IDEs |
| **Xcode** | Apple RSS | Xcode releases (filtered from Apple developer news) |
| **Neovim** | GitHub API | Neovim releases from `neovim/neovim` |
| **Eclipse** | Planet RSS | Eclipse IDE-related posts |

Items mentioning **Copilot** are automatically tagged across all sources for cross-cutting filtering.

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
- **Feature parity matrix** — always-visible table showing Copilot feature support across VS Code, VS Code Insiders, Visual Studio, JetBrains, Neovim, Eclipse, and Xcode
- **Filter by source** — GitHub, Copilot, VS Code, Visual Studio, JetBrains, Xcode, Neovim, Eclipse
- **Search** — instant client-side filtering (press `/` to focus, `Esc` to clear)
- **Dark mode** — follows system preference
- **Zero dependencies at runtime** — the page is pure HTML/CSS/JS reading a static JSON file

## Project Structure

```
src/
  build.py      Entry point: python -m src.build
  main.py       Build logic (fetches feeds → scores → writes JSON)
  feeds.py      Feed fetchers for all 7 sources
  models.py     Pydantic model (ChangeEntry with score/severity)
  scorer.py     Keyword-based importance scoring
  parity.py     Copilot feature parity matrix data
docs/
  index.html    Static page (served by GitHub Pages)
  data.json     Generated feed data (committed by CI)
.github/
  workflows/
    build.yml   Rebuilds data.json every 6 hours
```
