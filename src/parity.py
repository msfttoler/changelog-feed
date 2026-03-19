"""GitHub Copilot feature parity matrix across supported IDEs.

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

# True = full support, "partial" = preview / limited, False = not available
_CATEGORIES: list[tuple[str, list[tuple[str, dict[str, bool | str]]]]] = [
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
            "Copilot CLI (gh copilot)",
            {ide: "partial" if ide in ("VS Code", "VS Code Insiders") else False for ide in IDES},
        ),
        (
            "GitHub Actions Integration",
            {ide: False for ide in IDES},  # runs on GitHub, not in-IDE
        ),
        (
            "Copilot for Pull Requests",
            {ide: False for ide in IDES},  # GitHub.com feature
        ),
    ]),
]


def get_parity_matrix() -> dict:
    """Return the parity matrix as a JSON-serializable dict with categories."""
    categories = []
    for cat_name, features in _CATEGORIES:
        categories.append({
            "category": cat_name,
            "features": [
                {"name": name, "support": support}
                for name, support in features
            ],
        })
    return {
        "ides": IDES,
        "categories": categories,
    }
