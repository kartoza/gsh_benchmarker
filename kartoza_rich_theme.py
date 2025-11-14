#!/usr/bin/env python3
"""
Kartoza Rich Theme Configuration
Import this module to apply Kartoza colors to rich console output
"""

from rich.theme import Theme
from rich.console import Console

# Kartoza brand colors
KARTOZA_COLORS = {
    "highlight1": "#DF9E2F",  # yellow/orange
    "highlight2": "#569FC6",  # blue  
    "highlight3": "#8A8B8B",  # grey
    "highlight4": "#06969A",  # teal
    "alert": "#CC0403",       # red
}

# Rich theme using Kartoza colors
KARTOZA_THEME = Theme({
    "info": KARTOZA_COLORS["highlight2"],      # blue for info
    "warning": KARTOZA_COLORS["highlight1"],   # yellow/orange for warnings
    "error": KARTOZA_COLORS["alert"],          # red for errors
    "success": KARTOZA_COLORS["highlight4"],   # teal for success
    "muted": KARTOZA_COLORS["highlight3"],     # grey for muted text
    "primary": KARTOZA_COLORS["highlight2"],   # blue for primary content
    "secondary": KARTOZA_COLORS["highlight1"], # yellow/orange for secondary
    "accent": KARTOZA_COLORS["highlight4"],    # teal for accents
    "header": f"bold {KARTOZA_COLORS['highlight4']}", # bold teal for headers
    "title": f"bold {KARTOZA_COLORS['highlight2']}",  # bold blue for titles
})

# Pre-configured console with Kartoza theme
console = Console(theme=KARTOZA_THEME)

# Convenience functions
def print_info(text):
    console.print(text, style="info")

def print_warning(text):
    console.print(text, style="warning")
    
def print_error(text):
    console.print(text, style="error")
    
def print_success(text):
    console.print(text, style="success")
    
def print_header(text):
    console.print(text, style="header")
    
def print_title(text):
    console.print(text, style="title")