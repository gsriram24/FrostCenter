# ui/theme.py
"""Color palette, CSS theme, and widget helper functions."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

# --- Color palette (spec: Design Spec > Color Palette) ---
BG_MAIN = "#12121e"
BG_CARD = "#1a1a2e"
BG_ELEVATED = "#2d2d44"
BORDER = "#2d2d44"
TEXT_PRIMARY = "#cccccc"
TEXT_SECONDARY = "#888888"
TEXT_MUTED = "#666666"
CPU_COLOR = "#ff4655"
GPU_COLOR = "#00d4ff"
WARNING_COLOR = "#ff8c00"
SUCCESS_COLOR = "#00e57a"


def hex_to_rgba(hex_color, alpha=1.0):
    """Convert '#rrggbb' to (r, g, b, a) floats for Cairo."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return (r, g, b, alpha)


# Pre-computed Cairo RGBA tuples
CPU_RGBA = hex_to_rgba(CPU_COLOR)
GPU_RGBA = hex_to_rgba(GPU_COLOR)
WARNING_RGBA = hex_to_rgba(WARNING_COLOR)
BG_MAIN_RGBA = hex_to_rgba(BG_MAIN)
BG_CARD_RGBA = hex_to_rgba(BG_CARD)
BORDER_RGBA = hex_to_rgba(BORDER)
TEXT_MUTED_RGBA = hex_to_rgba(TEXT_MUTED)
GRID_RGBA = hex_to_rgba(BG_ELEVATED, 0.5)


_CSS = f"""
window {{
    background-color: {BG_MAIN};
}}
button {{
    text-shadow: none;
    box-shadow: none;
    -gtk-icon-shadow: none;
    background-image: none;
    background-color: {BG_ELEVATED};
    border: 1px solid transparent;
    color: {TEXT_SECONDARY};
}}
button:hover {{
    background-image: none;
    background-color: rgba(45, 45, 68, 0.8);
    color: {TEXT_PRIMARY};
}}
button:active, button:checked {{
    background-image: none;
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
}}
.sidebar {{
    background-color: {BG_CARD};
}}
.sidebar-btn {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    padding: 12px 20px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
    text-shadow: none;
    box-shadow: none;
}}
.sidebar-btn:hover {{
    background-color: {BG_ELEVATED};
    text-shadow: none;
}}
.sidebar-btn.active {{
    color: {CPU_COLOR};
    font-weight: 600;
    background-color: rgba(255, 70, 85, 0.08);
    border-left-color: {CPU_COLOR};
    text-shadow: none;
}}
.card {{
    background-color: {BG_CARD};
    border-radius: 10px;
    border: 1px solid {BORDER};
    padding: 16px;
}}
.profile-btn {{
    background-color: {BG_ELEVATED};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 16px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
.profile-btn:hover {{
    background-color: rgba(255, 70, 85, 0.15);
}}
.profile-btn.active {{
    background-color: rgba(255, 70, 85, 0.13);
    border-color: {CPU_COLOR};
    color: {CPU_COLOR};
    font-weight: 600;
}}
.boost-btn {{
    background-color: {BG_ELEVATED};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 16px;
    color: {WARNING_COLOR};
    font-size: 12px;
}}
.boost-btn.active {{
    background-color: rgba(255, 140, 0, 0.13);
    border-color: {WARNING_COLOR};
    font-weight: 600;
}}
.threshold-btn {{
    background-color: {BG_ELEVATED};
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 14px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
.threshold-btn.active {{
    background-color: rgba(255, 140, 0, 0.13);
    border-color: {WARNING_COLOR};
    color: {WARNING_COLOR};
    font-weight: 600;
}}
switch {{
    background-color: {TEXT_MUTED};
    background-image: none;
    border: none;
    border-radius: 14px;
    min-width: 48px;
    min-height: 26px;
    padding: 2px;
}}
switch slider {{
    background-color: white;
    background-image: none;
    border-radius: 50%;
    border: none;
    min-width: 22px;
    min-height: 22px;
}}
switch:checked {{
    background-color: {WARNING_COLOR};
    background-image: none;
}}
switch:checked slider {{
    background-color: white;
    background-image: none;
}}
switch:disabled {{
    opacity: 0.4;
}}
.profile-indicator {{
    background-color: rgba(255, 70, 85, 0.13);
    border: 1px solid rgba(255, 70, 85, 0.4);
    border-radius: 6px;
    padding: 6px 12px;
    color: {CPU_COLOR};
    font-size: 12px;
}}
.accent-btn {{
    background-color: rgba(0, 212, 255, 0.14);
    border: 1px solid rgba(0, 212, 255, 0.5);
    border-radius: 8px;
    padding: 8px 16px;
    color: {GPU_COLOR};
    font-weight: 600;
    font-size: 12px;
}}
.accent-btn:hover {{
    background-color: rgba(0, 212, 255, 0.25);
    border-color: {GPU_COLOR};
    color: #ffffff;
}}
.secondary-btn {{
    background-color: {BG_ELEVATED};
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 16px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
}}
.secondary-btn:hover {{
    background-color: rgba(45, 45, 68, 0.85);
    color: #ffffff;
}}
.pill-link {{
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    color: #a0a0b0;
    font-size: 11px;
    padding: 5px 12px;
    box-shadow: none;
    text-shadow: none;
    background-image: none;
}}
.pill-link:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(78, 205, 196, 0.8);
    color: #ffffff;
}}
.pill-link label {{
    color: inherit;
    text-decoration: none;
}}
linkbutton, linkbutton > label, linkbutton:link, linkbutton:visited {{
    text-decoration: none;
    color: inherit;
    box-shadow: none;
    text-shadow: none;
}}
.mono-box {{
    background-color: {BG_MAIN};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-family: monospace;
    font-size: 11px;
    padding: 10px;
}}
.badge-warning {{
    background-color: rgba(255, 140, 0, 0.14);
    border: 1px solid rgba(255, 140, 0, 0.5);
    border-radius: 6px;
    padding: 4px 10px;
    color: {WARNING_COLOR};
    font-size: 11px;
    font-weight: 600;
}}
.sidebar-verify-btn {{
    background-color: rgba(0, 212, 255, 0.08);
    border: 1px solid rgba(0, 212, 255, 0.35);
    border-radius: 6px;
    padding: 6px 10px;
    color: {GPU_COLOR};
    font-size: 11px;
    font-weight: 600;
    box-shadow: none;
    text-shadow: none;
    background-image: none;
}}
.sidebar-verify-btn:hover {{
    background-color: rgba(0, 212, 255, 0.20);
    border-color: {GPU_COLOR};
    color: #ffffff;
}}
.sidebar-star-btn {{
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    padding: 5px 10px;
    color: {TEXT_SECONDARY};
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
    background-image: none;
}}
.sidebar-star-btn:hover {{
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 204, 0, 0.6);
    color: #ffcc00;
}}
""".encode()


def apply_theme(window):
    """Load the dark CSS theme onto the given window's screen."""
    provider = Gtk.CssProvider()
    provider.load_from_data(_CSS)
    screen = window.get_screen()
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def make_label(text, color=TEXT_PRIMARY, size=12, bold=False, uppercase=False):
    """Create a styled Gtk.Label."""
    import html
    label = Gtk.Label()
    weight = "bold" if bold else "normal"
    display = text.upper() if uppercase else text
    safe_text = html.escape(display)
    markup = f'<span foreground="{color}" font_desc="{size}" weight="{weight}">{safe_text}</span>'
    label.set_markup(markup)
    label.set_halign(Gtk.Align.START)
    label.set_valign(Gtk.Align.CENTER)
    return label


def make_card():
    """Create a Gtk.Box styled as a card container."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.get_style_context().add_class("card")
    return box
