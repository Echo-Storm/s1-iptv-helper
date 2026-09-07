"""
Echo/S1 house style — shared dark+green QSS, matching Echo Audio Converter
and TorBox Manager EchoStorm Edition. See docs/DESIGN_SYSTEM.md.

Kept as a single module of color constants + a stylesheet-building function,
the same pattern TorBox_Manager/tbm/ui.py uses — no external .qss resource
file, no theming library.
"""

import os

# QSpinBox's ::up-arrow/::down-arrow subcontrols need a real image -- Qt's
# QSS engine doesn't support the usual CSS zero-size-box-plus-transparent-
# border triangle trick (confirmed: it renders as a plain filled square,
# not a triangle), and once any QSS touches the spin box at all, Qt stops
# falling back to drawing its own native arrow glyph too (renders nothing).
# Two tiny generated PNGs in assets/ are the reliable fix.
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets').replace('\\', '/')
SPIN_UP_ARROW = f"{_ASSETS_DIR}/spin_up.png"
SPIN_DOWN_ARROW = f"{_ASSETS_DIR}/spin_down.png"

COLOR_BG = "#181818"
COLOR_PANEL = "#1f1f1f"
COLOR_PANEL_ALT = "#232323"
COLOR_HEADER_BAR = "#2d1f00"
COLOR_ACCENT = "#7cb342"
COLOR_ACCENT_DIM = "#4a6b28"
COLOR_TEXT = "#e8e8e8"
COLOR_TEXT_MUTED = "#666666"
COLOR_BUTTON_BG = "#282828"
COLOR_BUTTON_HOVER = "#323232"
COLOR_BORDER = "#2a2a2a"
COLOR_BORDER_BRIGHT = "#3a3a3a"
COLOR_ROW_HOVER = "#252f1a"

FONT_UI_FAMILY = "Segoe UI"
FONT_UI_SIZE = 9
FONT_LOG_FAMILY = "Consolas"
FONT_LOG_SIZE = 8


def build_stylesheet():
    return f"""
    QWidget {{
        background-color: {COLOR_BG};
        color: {COLOR_TEXT};
        font-family: "{FONT_UI_FAMILY}";
        font-size: {FONT_UI_SIZE}pt;
    }}

    QMainWindow, QDialog {{
        background-color: {COLOR_BG};
    }}

    /* ---- Sidebar ------------------------------------------------------ */
    QLabel[role="section"] {{
        color: {COLOR_ACCENT};
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding-top: 6px;
    }}

    /* Distinct panel, matching the sibling apps' left sidebar treatment --
       previously this had no background/border at all and blended straight
       into the window, which read as unfinished next to Echo Audio
       Converter / TorBox Manager. */
    QWidget[role="sidebar"] {{
        background-color: {COLOR_PANEL};
        border-right: 1px solid {COLOR_BORDER_BRIGHT};
    }}
    QWidget[role="sidebar"] QPushButton {{
        text-align: left;
        padding-left: 10px;
        border-left: 2px solid transparent;
    }}
    QWidget[role="sidebar"] QPushButton:hover {{
        border-left: 2px solid {COLOR_ACCENT};
    }}
    QWidget[role="sidebar"] QPushButton[role="primary"]:hover {{
        border-left: 2px solid {COLOR_ACCENT};
    }}

    /* ---- Banner --------------------------------------------------------
       Fixed-height header bar with a bright top/bottom border, matching
       the sibling apps' actual rendered header treatment (both define an
       unused "amber header bar" color token but never apply it -- the
       real look in both is a panel-colored bar with accent borders, which
       is what this matches). Previously this widget had a role set but no
       matching QSS rule at all, so it had no background/border and just
       blended into the rest of the window. */
    QWidget[role="banner"] {{
        background-color: {COLOR_PANEL};
        border-top: 1px solid {COLOR_ACCENT};
        border-bottom: 2px solid {COLOR_ACCENT};
    }}

    QLabel[role="banner-title"] {{
        color: #c8c8c8;
        font-weight: 700;
        font-size: 20pt;
        letter-spacing: 5px;
    }}

    QLabel[role="banner-sep"] {{
        color: {COLOR_ACCENT_DIM};
        font-size: 16pt;
        font-weight: 100;
        padding: 0 6px;
    }}

    QLabel[role="banner-tag"] {{
        color: {COLOR_TEXT_MUTED};
        font-size: 8pt;
        font-weight: 600;
        letter-spacing: 1px;
    }}

    QFrame[role="banner-line"] {{
        background-color: {COLOR_ACCENT_DIM};
        max-height: 1px;
        min-height: 1px;
    }}

    /* ---- Donate (Ko-fi) ------------------------------------------------
       Flat, text-only button in the status bar -- same treatment Echo
       Audio Converter uses for its own Ko-fi link. */
    QPushButton#donateBtn {{
        background: transparent;
        border: none;
        color: {COLOR_ACCENT};
        font-weight: 600;
        letter-spacing: 1px;
        padding: 2px 8px;
    }}
    QPushButton#donateBtn:hover {{
        color: #9dd35a;
        text-decoration: underline;
    }}

    /* ---- Buttons ----------------------------------------------------- */
    QPushButton {{
        background-color: {COLOR_BUTTON_BG};
        border: 1px solid {COLOR_BORDER_BRIGHT};
        border-radius: 3px;
        padding: 6px 12px;
        color: {COLOR_TEXT};
    }}
    QPushButton:hover {{
        background-color: {COLOR_BUTTON_HOVER};
        border-color: {COLOR_ACCENT};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_ACCENT_DIM};
    }}
    QPushButton:disabled {{
        background-color: #252525;
        border-color: #353535;
        color: #606060;
    }}
    QPushButton[role="primary"] {{
        background-color: {COLOR_ACCENT_DIM};
        border-color: {COLOR_ACCENT};
        color: {COLOR_ACCENT};
        font-weight: 600;
    }}
    QPushButton[role="primary"]:hover {{
        background-color: #3e5a2e;
    }}

    /* ---- Tabs ---------------------------------------------------------- */
    QTabWidget::pane {{
        border: 1px solid {COLOR_BORDER};
        top: -1px;
    }}
    QTabBar {{
        qproperty-drawBase: 0;
    }}
    QTabBar::tab {{
        background: {COLOR_PANEL};
        color: {COLOR_TEXT_MUTED};
        padding: 9px 22px;
        margin-right: 3px;
        border: 1px solid {COLOR_BORDER_BRIGHT};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {COLOR_ACCENT_DIM};
        color: {COLOR_ACCENT};
        border: 1px solid {COLOR_ACCENT};
        border-bottom: none;
    }}
    QTabBar::tab:hover:!selected {{
        background: {COLOR_BUTTON_HOVER};
        color: {COLOR_TEXT};
    }}

    /* ---- Trees / tables ------------------------------------------------ */
    QTreeWidget, QTableWidget, QListWidget {{
        background-color: {COLOR_PANEL};
        alternate-background-color: {COLOR_PANEL_ALT};
        border: 1px solid {COLOR_BORDER};
        outline: 0;
    }}
    QHeaderView::section {{
        background-color: {COLOR_PANEL};
        color: {COLOR_ACCENT};
        padding: 4px 6px;
        border: none;
        border-bottom: 1px solid {COLOR_BORDER_BRIGHT};
        font-weight: 600;
    }}
    QTreeWidget::item:hover, QTableWidget::item:hover {{
        background-color: {COLOR_ROW_HOVER};
    }}
    QTreeWidget::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
        background-color: {COLOR_ACCENT_DIM};
        color: {COLOR_TEXT};
    }}

    /* ---- Inputs ------------------------------------------------------- */
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {COLOR_PANEL_ALT};
        border: 1px solid {COLOR_BORDER_BRIGHT};
        border-radius: 3px;
        padding: 4px 6px;
        color: {COLOR_TEXT};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border-color: {COLOR_ACCENT};
    }}

    /* QSpinBox needs its up/down sub-controls defined explicitly once it
       has any border/padding of its own -- as soon as a stylesheet touches
       a QAbstractSpinBox at all, Qt stops drawing the native step buttons
       and expects the stylesheet to lay them out. Without these rules the
       buttons still exist but their hit-region collapses into the corner
       radius/border and clicks land on the frame instead (the up button
       "doesn't work" symptom) -- explicit geometry + arrows fixes both the
       visuals and the click target. */
    QSpinBox {{
        padding-right: 16px;   /* room for the button column so text doesn't run under it */
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        subcontrol-origin: border;
        width: 16px;
        border-left: 1px solid {COLOR_BORDER_BRIGHT};
        background-color: {COLOR_BUTTON_BG};
    }}
    QSpinBox::up-button {{
        subcontrol-position: top right;
        border-top-right-radius: 3px;
        border-bottom: 1px solid {COLOR_BORDER_BRIGHT};
    }}
    QSpinBox::down-button {{
        subcontrol-position: bottom right;
        border-bottom-right-radius: 3px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {COLOR_BUTTON_HOVER};
    }}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
        background-color: {COLOR_ACCENT_DIM};
    }}
    QSpinBox::up-arrow {{
        image: url({SPIN_UP_ARROW});
        width: 8px;
        height: 8px;
    }}
    QSpinBox::down-arrow {{
        image: url({SPIN_DOWN_ARROW});
        width: 8px;
        height: 8px;
    }}

    /* ---- Log / status strip -------------------------------------------- */
    QPlainTextEdit[role="log"], QTextEdit[role="log"] {{
        background-color: #101010;
        color: {COLOR_TEXT_MUTED};
        border: 1px solid {COLOR_BORDER};
        font-family: "{FONT_LOG_FAMILY}";
        font-size: {FONT_LOG_SIZE}pt;
    }}

    QStatusBar {{
        background-color: {COLOR_PANEL};
        color: {COLOR_TEXT_MUTED};
        border-top: 1px solid {COLOR_BORDER};
    }}

    QScrollBar:vertical {{
        background: {COLOR_BG};
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLOR_BORDER_BRIGHT};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLOR_ACCENT_DIM};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
