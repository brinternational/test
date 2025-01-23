import tkinter as tk
from tkinter import ttk

def setup_theme(root):
    """Setup dark theme for the Bitcoin educational application."""

    # Define colors - Updated for better contrast
    DARK_BG = "#1E1E1E"  # Dark background
    DARKER_BG = "#252526"  # Slightly lighter than background
    ACCENT = "#569CD6"    # Soft blue accent
    TEXT = "#FFFFFF"      # White text for better contrast
    SECONDARY_TEXT = "#CCCCCC"  # Light grey for secondary text

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
        font=("Segoe UI", 20, "bold"),
        foreground=ACCENT
    )

    style.configure(
        "Topic.TLabel",
        font=("Segoe UI", 12, "bold"),
        foreground=TEXT
    )

    style.configure(
        "TButton",
        background=DARKER_BG,
        foreground=TEXT,
        padding=(10, 5),
        font=("Segoe UI", 10)
    )

    style.map(
        "TButton",
        background=[("active", ACCENT)],
        foreground=[("active", "#FFFFFF")]
    )

    style.configure(
        "TNotebook",
        background=DARK_BG,
        tabmargins=[2, 5, 2, 0]
    )

    style.configure(
        "TNotebook.Tab",
        background=DARKER_BG,
        foreground=TEXT,
        padding=[15, 5],
        font=("Segoe UI", 10)
    )

    style.map(
        "TNotebook.Tab",
        background=[("selected", ACCENT)],
        foreground=[("selected", "#FFFFFF")]
    )

    # Configure text widget colors
    root.option_add("*Text.background", DARKER_BG)
    root.option_add("*Text.foreground", TEXT)
    root.option_add("*Text.font", ("Consolas", 10))

    # Entry widget configuration
    style.configure(
        "TEntry",
        fieldbackground=DARKER_BG,
        foreground=TEXT,
        padding=5
    )