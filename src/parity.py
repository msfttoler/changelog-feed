"""GitHub Copilot feature parity matrix across supported surfaces.

Organised into named categories so the UI can render grouped sections.
Each category contains a list of (feature_name, support_dict) tuples.
"""

from __future__ import annotations

IDES = [
    "VS Code",
    "VS Code Insiders",
    "Visual Studio",
    "JetBrains",
    "Neovim",
    "Eclipse",
    "Xcode",
]

_APP = "GitHub Copilot App"
SURFACES = [*IDES, _APP]
_APP_DOCS = "https://docs.github.com/en/copilot/concepts/copilot-surfaces/github-copilot-app"

# Only documented capabilities are asserted; omitted features remain unverified.
_APP_SUPPORT: dict[str, bool | str] = {
    "Multi-file Edits": True,
    "Code Review": True,
    "Copilot Chat": True,
    "Agent Mode": True,
    "Model Selection (GPT-4o, Claude, etc.)": True,
    "Terminal Integration": True,
    "PR Description Generation": True,
    "MCP Server Support": True,
    "Custom Instructions (.instructions.md)": True,
    "Agent Skills (SKILL.md)": True,
    "Custom Agents (.agent.md / AGENTS.md)": True,
    "Tool Functions / Tool Calling": True,
    "Copilot CLI Integration": True,
    "Copilot for Pull Requests": True,
}

# True = supported, "partial" = limited, False = unavailable, None = unverified
Support = dict[str, bool | str | None]
_CATEGORIES: list[tuple[str, list[tuple[str, Support]]]] = [
    # ── Code Generation & Editing ────────────────────────────────────
    ("Code Generation & Editing", [
        (
            "Code Completions",
            {ide: True for ide in IDES},
        ),
        (
            "Next Edit Suggestions (NES)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": "partial", "JetBrains": "partial",
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Multi-file Edits",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": "partial", "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Inline Chat",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Code Review",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Test Generation",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": "partial",
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Documentation Generation",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Rename Suggestions",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
    ]),

    # ── Chat & Agent ─────────────────────────────────────────────────
    ("Chat & Agent", [
        (
            "Copilot Chat",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": True,
                "Neovim": "partial", "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Agent Mode",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": "partial", "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Vision / Image Understanding",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Chat Participants (@workspace, etc.)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": "partial", "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Model Selection (GPT-4o, Claude, etc.)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
    ]),

    # ── Context & Intelligence ───────────────────────────────────────
    ("Context & Intelligence", [
        (
            "Workspace / Codebase Indexing",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Terminal Integration",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Git Commit Message Generation",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "PR Description Generation",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Notebook / REPL Support",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": "partial",
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
    ]),

    # ── Extensibility & Customisation ────────────────────────────────
    ("Extensibility & Customization", [
        (
            "MCP Server Support",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": "partial", "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Custom Instructions (.instructions.md)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": True, "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Reusable Prompts (.prompt.md)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Agent Skills (SKILL.md)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Custom Agents (.agent.md / AGENTS.md)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Custom Modes",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": False, "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Chat Participant API (Extensions)",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": "partial", "JetBrains": False,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
        (
            "Tool Functions / Tool Calling",
            {
                "VS Code": True, "VS Code Insiders": True,
                "Visual Studio": "partial", "JetBrains": True,
                "Neovim": False, "Eclipse": False, "Xcode": False,
            },
        ),
    ]),

    # ── Copilot in the CLI / DevOps ──────────────────────────────────
    ("DevOps & CLI", [
        (
            "Copilot CLI Integration",
            {ide: "partial" if ide in ("VS Code", "VS Code Insiders") else False for ide in IDES},
        ),
        (
            "GitHub Actions Integration",
            {ide: False for ide in IDES},  # runs on GitHub, not in-IDE
        ),
        (
            "Copilot for Pull Requests",
            {ide: False for ide in IDES},
        ),
    ]),
    ("App Workflows", [
        (name, {surface: None for surface in IDES} | {_APP: status})
        for name, status in [
            ("Parallel Isolated Sessions / Worktrees", True),
            ("Interactive / Plan / Autopilot Modes", True),
            ("Bring Your Own Model (BYOK)", True),
            ("Scheduled Automations", True),
            ("Shared Agent Canvases", True),
            ("Desktop Computer Use", "partial"),
        ]
    ]),
]


def get_parity_matrix() -> dict:
    """Return the parity matrix as a JSON-serializable dict with categories."""
    categories = []
    for cat_name, features in _CATEGORIES:
        categories.append({
            "category": cat_name,
            "features": [
                {"name": name, "support": {_APP: _APP_SUPPORT.get(name), **support}}
                for name, support in features
            ],
        })
    return {
        "ides": IDES,
        "surfaces": SURFACES,
        "categories": categories,
        "surface_details": {
            _APP: {
                "url": _APP_DOCS,
                "reviewed_at": "2026-10-16",
                "note": "Documented app capabilities; unknown cells are not verified. "
                        "Computer use is limited to local macOS and Windows sessions.",
            },
        },
    }
