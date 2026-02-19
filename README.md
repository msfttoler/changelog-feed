# changelog-feed

A **platform-wide CSA signal engine** that monitors GitHub, Visual Studio, and VS Code changelogs, uses AI to classify relevance for Cloud Solution Architects, and posts only high-value items into Microsoft Teams.

## Architecture

```
[Scheduler / Webhook]
        ↓
[Feed Ingestion]           – GitHub changelog RSS, VS Code release notes, Visual Studio release notes
        ↓
[Normalizer + Dedupe]      – SQLite-backed state store prevents re-posting
        ↓
[Rule Engine]              – Deterministic hard rules (security, breaking changes, deprecations always post; UI polish never posts)
        ↓
[AI Classifier]            – OpenAI / Azure OpenAI rates CSA relevance with structured output
        ↓
[Post Decision Engine]     – Combines rule + AI signal to decide what to post
        ↓
[Teams Workflow Webhook]   – Adaptive Card message to a Teams channel
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys and Teams webhook URL
```

### 3. Run

```bash
# Dry run (ingest + classify, no posting)
python -m src.main --dry-run

# Live run
python -m src.main
```

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (standard OpenAI) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment name |
| `OPENAI_MODEL` | Model name for OpenAI (default: `gpt-4o`) |
| `TEAMS_WEBHOOK_URL` | Teams Workflows webhook URL |
| `MIN_RELEVANCE` | Minimum relevance to post: `high` (default), `medium`, or `low` |
| `STATE_DB_PATH` | SQLite state file path (default: `.changelog_feed_state.db`) |

## Signal Sources

| Source | Feed |
|---|---|
| **GitHub Platform** | RSS feed from `github.blog/changelog` – covers Copilot, Actions, Security, Enterprise |
| **VS Code** | Monthly release notes pages – parsed into per-section items |
| **Visual Studio** | Microsoft Learn release notes pages – GA and Preview channels |

## AI Classification

Items not covered by hard rules are sent to the AI classifier, which returns structured output:

```json
{
  "csa_relevance": "high | medium | low",
  "why_it_matters": "One sentence for a CSA",
  "customer_impact": "none | situational | broad",
  "conversation_trigger": true,
  "categories": ["security", "copilot"],
  "confidence": 0.92
}
```

AI supplies **inputs** (scoring + explanation), not the final posting decision.

## Deterministic Guardrails

**Always post** (no AI veto): security fixes, CVEs, breaking changes, deprecations, retirements, end-of-life notices, enterprise policy changes.

**Never post**: UI polish, emoji packs, typo fixes, dark mode changes, minor cosmetic updates.

## Teams Message Format

```
🔴 GitHub Platform Update – Security

**What changed:**
• Critical vulnerability patched in token scoping

**Why this matters for CSAs:**
• Impacts enterprise security posture and compliance reviews

**Customer impact:**
• Broad – affects most customers

**Tags:** `security` `breaking-change`

🔗 Read more (rule: always post)
```

## Running Tests

```bash
pip install responses pytest pytest-mock
pytest tests/ -v
```

## Deployment

The pipeline is a single Python call (`run_pipeline()`) and runs cleanly as:

- **Azure Function** (timer trigger for scheduled runs, HTTP trigger for on-demand)
- **Container App** with a cron sidecar
- **GitHub Actions** workflow on a schedule
