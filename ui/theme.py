import tkinter as tk
from tkinter import ttk

def setup_theme(root):
    """Setup custom theme for the Bitcoin educational application."""
    
    # Define colors
    BITCOIN_ORANGE = "#F7931A"
    DARK_GRAY = "#2D2D2D"
    LIGHT_GRAY = "#F5F5F5"
    WHITE = "#FFFFFF"
    
    # Configure styles
    style = ttk.Style(root)
    
    # Configure main theme
    style.configure(
        "TFrame",
        background=WHITE
    )
    
    style.configure(
        "TLabel",
        background=WHITE,
        foreground=DARK_GRAY,
        font=("Helvetica", 10)
    )
    
    style.configure(
        "Title.TLabel",
        font=("Helvetica", 24, "bold"),
        foreground=BITCOIN_ORANGE
    )
    
    style.configure(
        "Topic.TLabel",
        font=("Helvetica", 14, "bold"),
        foreground=DARK_GRAY
    )
    
    style.configure(
        "TButton",
        background=BITCOIN_ORANGE,
        foreground=WHITE,
        padding=(10, 5),
        font=("Helvetica", 10)
    )
    
    style.configure(
        "TNotebook",
        background=WHITE,
        tabmargins=[2, 5, 2, 0]
    )
    
    style.configure(
        "TNotebook.Tab",
        background=LIGHT_GRAY,
        foreground=DARK_GRAY,
        padding=[10, 2],
        font=("Helvetica", 10)
    )
    
    style.map(
        "TNotebook.Tab",
        background=[("selected", BITCOIN_ORANGE)],
        foreground=[("selected", WHITE)]
    )
    
    # Configure text widget
    root.option_add("*Text.background", LIGHT_GRAY)
    root.option_add("*Text.foreground", DARK_GRAY)
    root.option_add("*Text.font", ("Courier", 10))

