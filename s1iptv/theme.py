"""
Echo/S1 house style — shared dark+green QSS, matching Echo Audio Converter
and TorBox Manager EchoStorm Edition. See docs/DESIGN_SYSTEM.md.

Kept as a single module of color constants + a stylesheet-building function,
the same pattern TorBox_Manager/tbm/ui.py uses — no external .qss resource
file, no theming library.
"""

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

    /* ---- Sidebar section labels ------------------------------------ */
    QLabel[role="section"] {{
        color: {COLOR_ACCENT};
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding-top: 6px;
    }}

    QLabel[role="banner-title"] {{
        color: {COLOR_ACCENT};
        font-weight: 700;
        font-size: 16pt;
        letter-spacing: 3px;
    }}

    QLabel[role="banner-tag"] {{
        color: {COLOR_TEXT_MUTED};
        font-size: 8pt;
        letter-spacing: 1px;
    }}

    QFrame[role="banner-line"] {{
        background-color: {COLOR_ACCENT_DIM};
        max-height: 1px;
        min-height: 1px;
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
    QTabBar::tab {{
        background: transparent;
        color: {COLOR_TEXT_MUTED};
        padding: 6px 16px;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {COLOR_ACCENT};
        border-bottom: 2px solid {COLOR_ACCENT};
    }}
    QTabBar::tab:hover:!selected {{
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
    QLineEdit:focus, QComboBox:focus {{
        border-color: {COLOR_ACCENT};
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
