import tkinter as tk
from tkinter import ttk

def setup_theme(root):
    """Setup dark theme for the Bitcoin educational application."""

    # Define colors - Updated for better contrast
    DARK_BG = "#1E1E1E"      # Dark background
    DARKER_BG = "#252526"    # Slightly darker for contrast
    ACCENT = "#61AFEF"       # Bright blue accent
    TEXT = "#FFFFFF"         # Pure white text
    ERROR_RED = "#FF3333"    # Bright red for errors
    SUCCESS_GREEN = "#4CAF50" # Bright green for success
    WARNING_YELLOW = "#FFC107" # Bright yellow for warnings

    # Configure root window
    root.configure(bg=DARK_BG)

    # Configure styles
    style = ttk.Style(root)

    # Configure main theme
    style.configure(
        "TFrame",
        background=DARK_BG
    )

    style.configure(
        "TLabel",
        background=DARK_BG,
        foreground=TEXT,
        font=("Segoe UI", 10)
    )

    style.configure(
        "Title.TLabel",
        font=("Segoe UI", 24, "bold"),
        foreground=ACCENT
    )

    style.configure(
        "Topic.TLabel",
        font=("Segoe UI", 14, "bold"),
        foreground=TEXT
    )

    # Button styling with better contrast
    style.configure(
        "TButton",
        background=ACCENT,
        foreground=TEXT,
        padding=(15, 8),
        font=("Segoe UI", 10, "bold")
    )

    style.map(
        "TButton",
        background=[("active", ACCENT), ("pressed", "#4B8BBF")],
        foreground=[("active", "#FFFFFF")]
    )

    # Notebook styling
    style.configure(
        "TNotebook",
        background=DARK_BG,
        tabmargins=[2, 5, 2, 0]
    )

    style.configure(
        "TNotebook.Tab",
        background=DARKER_BG,
        foreground=TEXT,
        padding=[20, 8],
        font=("Segoe UI", 11)
    )

    style.map(
        "TNotebook.Tab",
        background=[("selected", ACCENT)],
        foreground=[("selected", "#FFFFFF")]
    )

    # Configure text widget colors
    root.option_add("*Text.background", DARKER_BG)
    root.option_add("*Text.foreground", TEXT)
    root.option_add("*Text.font", ("Consolas", 11))

    # Entry widget with better contrast
    style.configure(
        "TEntry",
        fieldbackground=DARKER_BG,
        foreground=TEXT,
        padding=8,
        font=("Segoe UI", 11)
    )

    # Status message colors
    root.option_add("*success.foreground", SUCCESS_GREEN)
    root.option_add("*error.foreground", ERROR_RED)
    root.option_add("*warning.foreground", WARNING_YELLOW)