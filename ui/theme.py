import tkinter as tk
from tkinter import ttk

def setup_theme(root):
    """Setup light theme for the Bitcoin educational application."""

    # Define colors - Updated for better readability
    GREY_BG = "#E0E0E0"      # Light grey background
    DARKER_GREY = "#C0C0C0"  # Slightly darker for contrast
    ACCENT = "#2196F3"       # Blue accent
    TEXT = "#000000"         # Black text
    ERROR_RED = "#D32F2F"    # Dark red for errors
    SUCCESS_GREEN = "#388E3C" # Dark green for success
    WARNING_YELLOW = "#F57F17" # Dark yellow for warnings

    # Configure root window
    root.configure(bg=GREY_BG)

    # Configure styles
    style = ttk.Style(root)

    # Configure main theme
    style.configure(
        "TFrame",
        background=GREY_BG
    )

    style.configure(
        "TLabel",
        background=GREY_BG,
        foreground=TEXT,
        font=("Segoe UI", 10)
    )

    style.configure(
        "Title.TLabel",
        font=("Segoe UI", 10, "bold"),
        foreground=ACCENT,
        background=GREY_BG
    )

    style.configure(
        "Topic.TLabel",
        font=("Segoe UI", 10, "bold"),
        foreground=TEXT,
        background=GREY_BG
    )

    # Info label for instance details
    style.configure(
        "Info.TLabel",
        font=("Segoe UI", 10),
        foreground=TEXT,
        background=GREY_BG
    )

    # Button styling with better contrast
    style.configure(
        "TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        padding=(10, 5),
        font=("Segoe UI", 10)
    )

    # Action button for instance control
    style.configure(
        "Action.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        padding=(10, 5),
        font=("Segoe UI", 10, "bold")
    )

    style.map(
        "TButton",
        background=[("active", ACCENT), ("pressed", "#1976D2")],
        foreground=[("active", "#FFFFFF")]
    )

    # Notebook styling
    style.configure(
        "TNotebook",
        background=GREY_BG,
        tabmargins=[2, 5, 2, 0]
    )

    style.configure(
        "TNotebook.Tab",
        background=DARKER_GREY,
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
    root.option_add("*Text.background", "#FFFFFF")
    root.option_add("*Text.foreground", TEXT)
    root.option_add("*Text.font", ("Consolas", 10))

    # Entry widget with better contrast
    style.configure(
        "TEntry",
        fieldbackground="#FFFFFF",
        foreground=TEXT,
        padding=5,
        font=("Segoe UI", 10)
    )

    # Treeview for instance list
    style.configure(
        "Treeview",
        background="#FFFFFF",
        fieldbackground="#FFFFFF",
        foreground=TEXT,
        font=("Segoe UI", 10)
    )

    style.configure(
        "Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        padding=5
    )

    # Status message colors
    root.option_add("*success.foreground", SUCCESS_GREEN)
    root.option_add("*error.foreground", ERROR_RED)
    root.option_add("*warning.foreground", WARNING_YELLOW)