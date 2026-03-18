"""GitHub Copilot feature parity matrix across supported IDEs."""

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

# True = full support, "partial" = preview/limited, False = not available
_MATRIX: list[tuple[str, dict[str, bool | str]]] = [
    (
        "Code Completions",
        {ide: True for ide in IDES},
    ),
    (
        "Copilot Chat",
        {
            "VS Code": True, "VS Code Insiders": True,
            "Visual Studio": True, "JetBrains": True,
            "Neovim": "partial", "Eclipse": False, "Xcode": False,
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
        "Agent Mode",
        {
            "VS Code": True, "VS Code Insiders": True,
            "Visual Studio": "partial", "JetBrains": True,
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
        "MCP Support",
        {
            "VS Code": True, "VS Code Insiders": True,
            "Visual Studio": False, "JetBrains": True,
            "Neovim": False, "Eclipse": False, "Xcode": False,
        },
    ),
    (
        "Custom Instructions",
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
        "Workspace Context",
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
        "Vision",
        {
            "VS Code": True, "VS Code Insiders": True,
            "Visual Studio": False, "JetBrains": True,
            "Neovim": False, "Eclipse": False, "Xcode": False,
        },
    ),
    (
        "Next Edit Suggestions",
        {
            "VS Code": True, "VS Code Insiders": True,
            "Visual Studio": "partial", "JetBrains": "partial",
            "Neovim": False, "Eclipse": False, "Xcode": False,
        },
    ),
]


def get_parity_matrix() -> dict:
    """Return the parity matrix as a JSON-serializable dict."""
    return {
        "ides": IDES,
        "features": [
            {"name": name, "support": support}
            for name, support in _MATRIX
        ],
    }
