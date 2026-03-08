"""
Skill Deck v2 — RPG-style inventory for Claude Code skills.
Click = copy command to clipboard. Sub-modes as clickable ability buttons.
Custom packs editable via skills.json.

v2: Role/Plugin filters, Marketplace browser, Pack Builder, Collapsible sidebar.
"""
import sys
import ctypes

APP_ID = 'claude.skilldeck'
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except AttributeError:
    pass  # Non-Windows

import json
import os
import subprocess
import tkinter as tk
from pathlib import Path

SKILL_DIR = Path(__file__).parent
SKILLS_FILE = SKILL_DIR / "skills.json"
CONFIG_FILE = SKILL_DIR / "config.json"
PLUGINS_DIR = Path.home() / ".claude" / "plugins"

# ── Labels (edit to localize) ────────────────────────────────
LABELS = {
    "title":           "Skill Deck",
    "sorts":           "sorts",
    "sorts_learned":   "sorts appris",
    "sorts_custom":    "sorts custom",
    "copied":          "copie !",
    "copy_hint":       "Clic = copier  |  Sous-mode = copier le sous-mode",
    "empty_detail":    "Selectionne un sort pour voir les details",
    "builder_title":   "CONSTRUCTEUR DE PACK",
    "builder_name":    "Nom:",
    "builder_icon":    "Icone:",
    "builder_empty":   "(vide — clic sur les sorts pour ajouter)",
    "builder_save":    "  Sauvegarder  ",
    "builder_cancel":  "  Annuler  ",
    "builder_enter":   " + Constructeur",
    "builder_exit":    " ✕ Quitter constructeur",
    "edit_file":       " ✎  Editer skills.json",
    "reload":          " ↻  Recharger",
    "marketplace_btn": " 🏪  Parcourir les plugins",
    "installed":       "INSTALLE",
    "available":       "DISPONIBLE",
    "plugins_mkt":     "plugins marketplace",
}

# ── Theme (Cream / Pastel / Soft) ─────────────────────────────
T = {
    "bg":          "#f5f0e8",
    "sidebar":     "#ede7dc",
    "card":        "#ffffff",
    "card_hover":  "#f9f5ef",
    "card_select": "#e8dfd3",
    "border":      "#d9d0c3",
    "text":        "#3d3529",
    "text2":       "#7a6f60",
    "text_dim":    "#a99e8e",
    "accent":      "#7c6bb0",
    "green":       "#5a9a6e",
    "red":         "#c05a50",
    "detail_bg":   "#ede7dc",
}

RARITY_COLORS = {
    "legendary": "#c8782a",
    "epic":      "#8b5cad",
    "rare":      "#4a7fb5",
    "uncommon":  "#5a9a6e",
    "common":    "#8a8078",
}
RARITY_LABELS = {
    "legendary": "LEGENDAIRE",
    "epic":      "EPIQUE",
    "rare":      "RARE",
    "uncommon":  "PEU COMMUN",
    "common":    "COMMUN",
}
RARITY_ORDER = {"legendary": 0, "epic": 1, "rare": 2, "uncommon": 3, "common": 4}

ROLE_COLORS = {
    "agent":     "#8b5cad",
    "workflow":  "#4a7fb5",
    "devtool":   "#c05a50",
    "security":  "#5a9a6e",
    "meta":      "#b08840",
    "knowledge": "#5a8fa0",
}

ROLE_INFO = {
    "agent":     {"icon": "⚔", "label": "Agents",     "color": "#8b5cad"},
    "workflow":  {"icon": "↻", "label": "Workflows",   "color": "#4a7fb5"},
    "devtool":   {"icon": "⚒", "label": "Dev Tools",   "color": "#c05a50"},
    "security":  {"icon": "🛡", "label": "Securite",   "color": "#5a9a6e"},
    "meta":      {"icon": "⚙", "label": "Meta",        "color": "#b08840"},
    "knowledge": {"icon": "📖", "label": "Savoir",     "color": "#5a8fa0"},
}

SOURCE_INFO = {
    "all":    {"icon": "◈", "label": "Tous",    "color": "#7c6bb0"},
    "custom": {"icon": "★", "label": "Custom",  "color": "#8b5cad"},
    "plugin": {"icon": "⚙", "label": "Plugins", "color": "#5a9a6e"},
    "native": {"icon": "▶", "label": "Natifs",  "color": "#8a8078"},
}

FONT = "Segoe UI" if sys.platform == "win32" else "Helvetica"
FONT_MONO = "Cascadia Code" if sys.platform == "win32" else "Courier"
UI_DEFAULTS = {"opacity": 92, "window_x": None, "window_y": None,
               "collapsed": {"SOURCES": False, "PACKS": False, "ROLES": True,
                              "PAR PLUGIN": True, "MARKETPLACE": True}}
FILE_WATCH_INTERVAL = 2000  # ms between checks
EMOJI_PALETTE = ["⚔", "🛡", "🔧", "🐛", "🚀", "☀", "⚡", "🧪", "📋", "💾", "🎯", "◆"]


# ── Data ──────────────────────────────────────────────────────

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = {**UI_DEFAULTS, **json.load(f)}
            # Ensure collapsed has all keys
            defaults = UI_DEFAULTS["collapsed"]
            cfg["collapsed"] = {**defaults, **cfg.get("collapsed", {})}
            # Theme override
            if "theme" in cfg:
                T.update(cfg["theme"])
            return cfg
    return dict(UI_DEFAULTS)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def default_data():
    return {
        "skills": [
            {"command": "/commit", "name": "Commit", "icon": "💾",
             "description": "Create well-structured git commits with optional amend and fixup",
             "source": "custom", "role": "workflow", "rarity": "rare", "invocation": "slash",
             "submodes": [
                 {"cmd": "/commit --amend", "label": "--amend", "desc": "Amend last commit"},
                 {"cmd": "/commit --fixup", "label": "--fixup", "desc": "Fixup commit for rebase"},
             ]},
        ],
        "packs": {},
    }


def load_skills():
    if SKILLS_FILE.exists():
        try:
            with open(SKILLS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    data = default_data()
    with open(SKILLS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def load_marketplace_data():
    """Load all marketplace plugin data from local files."""
    result = []
    installed = set()
    install_counts = {}

    # Parse installed plugins
    installed_file = PLUGINS_DIR / "installed_plugins.json"
    if installed_file.exists():
        try:
            with open(installed_file, encoding="utf-8") as f:
                data = json.load(f)
            for key in data.get("plugins", {}):
                installed.add(key)
        except (json.JSONDecodeError, KeyError):
            pass

    # Parse install counts
    counts_file = PLUGINS_DIR / "install-counts-cache.json"
    if counts_file.exists():
        try:
            with open(counts_file, encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("counts", []):
                install_counts[entry["plugin"]] = entry.get("unique_installs", 0)
        except (json.JSONDecodeError, KeyError):
            pass

    # Parse known marketplaces
    mkt_file = PLUGINS_DIR / "known_marketplaces.json"
    if not mkt_file.exists():
        return result
    try:
        with open(mkt_file, encoding="utf-8") as f:
            marketplaces = json.load(f)
    except (json.JSONDecodeError, KeyError):
        return result

    for mkt_name, mkt_info in marketplaces.items():
        catalog_path = Path(mkt_info.get("installLocation", "")) / ".claude-plugin" / "marketplace.json"
        if not catalog_path.exists():
            continue
        try:
            with open(catalog_path, encoding="utf-8") as f:
                catalog = json.load(f)
        except (json.JSONDecodeError, KeyError):
            continue

        for plugin in catalog.get("plugins", []):
            pname = plugin.get("name", "")
            key = f"{pname}@{mkt_name}"
            result.append({
                "name": pname,
                "description": plugin.get("description", ""),
                "category": plugin.get("category", ""),
                "marketplace": mkt_name,
                "installed": key in installed,
                "version": plugin.get("version", ""),
                "install_count": install_counts.get(key, 0),
            })

    result.sort(key=lambda p: (not p["installed"], -p["install_count"], p["name"]))
    return result


# ── Helpers ───────────────────────────────────────────────────

def apply_bg(widget, color):
    try:
        widget.configure(bg=color)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        apply_bg(child, color)


def bind_recursive(widget, event, callback):
    widget.bind(event, callback)
    for child in widget.winfo_children():
        bind_recursive(child, event, callback)


def format_count(n):
    if n >= 1000:
        return f"{n/1000:.0f}k"
    return str(n)


def open_file(path):
    """Cross-platform file opener."""
    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', path])
    else:
        subprocess.run(['xdg-open', path])


# ── Main App ──────────────────────────────────────────────────

class SkillDeck:
    def __init__(self, root):
        self.root = root
        self.root.title(LABELS["title"])
        self.root.configure(bg=T["bg"])
        self.root.minsize(740, 520)

        self.config = load_config()
        self.data = load_skills()
        self.skills = self.data.get("skills", [])
        self.packs = self.data.get("packs", {})

        self.current_source = "all"
        self.current_pack = None
        self.current_role = None
        self.current_plugin = None
        self.selected_skill = None
        self.marketplace_mode = False
        self.marketplace_data = []
        self.builder_mode = False
        self.builder_pack = {"name": "", "icon": "⚔", "description": "", "commands": []}
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.skill_widgets = []
        self._copy_job = None
        self._skip_next_watch = False

        # Collapsible section state
        self.collapsed = self.config.get("collapsed", UI_DEFAULTS["collapsed"])
        self.section_frames = {}

        self.root.attributes("-alpha", self.config.get("opacity", 92) / 100)
        self.root.attributes("-topmost", True)

        # Icon
        ico_path = SKILL_DIR / "skill-deck.ico"
        if ico_path.exists():
            self.root.iconbitmap(str(ico_path))

        self._build_ui()

        # Position
        self.root.update_idletasks()
        cx, cy = self.config.get("window_x"), self.config.get("window_y")
        if cx is not None and cy is not None:
            self.root.geometry(f"+{cx}+{cy}")
        else:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            self.root.geometry(f"+{(self.root.winfo_screenwidth()-w)//2}+{(self.root.winfo_screenheight()-h)//2}")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._filter("all")

        # File watcher
        self._last_mtime = SKILLS_FILE.stat().st_mtime if SKILLS_FILE.exists() else 0
        self._watch_file()

    def _on_close(self):
        self.config["window_x"] = self.root.winfo_x()
        self.config["window_y"] = self.root.winfo_y()
        self.config["collapsed"] = self.collapsed
        save_config(self.config)
        self.root.destroy()

    # ── Build UI ──────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self.root, bg=T["bg"], pady=8)
        title_bar.pack(fill="x", padx=16)

        tk.Label(title_bar, text=f"⚔  {LABELS['title']}",
                 font=(FONT, 16, "bold"), fg=T["text"], bg=T["bg"]).pack(side="left")

        self.count_label = tk.Label(title_bar, text="",
                                    font=(FONT, 9), fg=T["text_dim"], bg=T["bg"])
        self.count_label.pack(side="right", padx=(0, 8))

        # Opacity slider
        self.opacity_var = tk.IntVar(value=self.config.get("opacity", 92))
        tk.Scale(title_bar, from_=30, to=100, orient="horizontal",
                 variable=self.opacity_var, bg=T["bg"], fg=T["text_dim"],
                 troughcolor=T["border"], highlightthickness=0,
                 sliderrelief="flat", showvalue=False, length=60, width=8,
                 command=self._on_opacity).pack(side="right")

        # Main split
        main = tk.Frame(self.root, bg=T["bg"])
        main.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self._build_sidebar(main)
        self._build_content(main)

    # ── Collapsible Section Helper ────────────────────────

    def _make_section(self, parent, title):
        """Create a collapsible section with header + content frame."""
        is_collapsed = self.collapsed.get(title, False)
        chevron = "▸" if is_collapsed else "▾"

        header = tk.Label(parent, text=f"{chevron} {title}", font=(FONT, 8, "bold"),
                          fg=T["text_dim"], bg=T["sidebar"], anchor="w", cursor="hand2")
        header.pack(fill="x", pady=(6, 2))
        header.bind("<Button-1>", lambda e, t=title: self._toggle_section(t))

        content = tk.Frame(parent, bg=T["sidebar"])
        if not is_collapsed:
            content.pack(fill="x", after=header)

        self.section_frames[title] = (header, content)
        return content

    def _toggle_section(self, title):
        if title not in self.section_frames:
            return
        header, content = self.section_frames[title]
        is_collapsed = self.collapsed.get(title, False)
        if is_collapsed:
            content.pack(fill="x", after=header)
            self.collapsed[title] = False
            header.configure(text=f"▾ {title}")
        else:
            content.pack_forget()
            self.collapsed[title] = True
            header.configure(text=f"▸ {title}")
        self.config["collapsed"] = self.collapsed
        save_config(self.config)

    # ── Sidebar ───────────────────────────────────────────

    def _build_sidebar(self, parent):
        # Scrollable sidebar
        sidebar_outer = tk.Frame(parent, bg=T["sidebar"], width=180)
        sidebar_outer.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        sidebar_outer.grid_propagate(False)
        sidebar_outer.grid_rowconfigure(0, weight=1)
        sidebar_outer.grid_columnconfigure(0, weight=1)

        self.sidebar_canvas = tk.Canvas(sidebar_outer, bg=T["sidebar"],
                                        highlightthickness=0, bd=0, width=170)
        self.sidebar_canvas.grid(row=0, column=0, sticky="nsew")

        self.sidebar_inner = tk.Frame(self.sidebar_canvas, bg=T["sidebar"], padx=8, pady=4)
        self.sidebar_canvas_window = self.sidebar_canvas.create_window(
            (0, 0), window=self.sidebar_inner, anchor="nw")

        self.sidebar_inner.bind("<Configure>",
            lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.bind("<Configure>",
            lambda e: self.sidebar_canvas.itemconfigure(self.sidebar_canvas_window, width=e.width))

        # Sidebar mousewheel
        self.sidebar_canvas.bind("<Enter>",
            lambda e: self.sidebar_canvas.bind_all("<MouseWheel>", self._on_sidebar_wheel))
        self.sidebar_canvas.bind("<Leave>",
            lambda e: self.sidebar_canvas.unbind_all("<MouseWheel>"))

        sidebar = self.sidebar_inner

        # ── SOURCES ──
        src_content = self._make_section(sidebar, "SOURCES")
        self.source_buttons = {}
        for key, info in SOURCE_INFO.items():
            count = len(self.skills) if key == "all" else sum(1 for s in self.skills if s["source"] == key)
            btn = tk.Label(src_content,
                           text=f" {info['icon']}  {info['label']}  ({count})",
                           font=(FONT, 10), fg=info["color"], bg=T["sidebar"],
                           anchor="w", padx=6, pady=3, cursor="hand2")
            btn.pack(fill="x", pady=1)
            btn.bind("<Button-1>", lambda e, k=key: self._filter(k))
            self.source_buttons[key] = btn

        # ── PACKS ──
        pack_content = self._make_section(sidebar, "PACKS")
        self.pack_buttons = {}
        for name, pack in self.packs.items():
            btn = tk.Label(pack_content,
                           text=f" {pack['icon']}  {name}",
                           font=(FONT, 10), fg="#c8782a", bg=T["sidebar"],
                           anchor="w", padx=6, pady=3, cursor="hand2")
            btn.pack(fill="x", pady=1)
            btn.bind("<Button-1>", lambda e, n=name: self._filter_pack(n))
            self.pack_buttons[name] = btn

        # Builder toggle button (under packs)
        self.builder_btn = tk.Label(pack_content,
                                     text=LABELS["builder_enter"],
                                     font=(FONT, 9, "bold"), fg=T["accent"], bg=T["sidebar"],
                                     anchor="w", padx=6, pady=3, cursor="hand2")
        self.builder_btn.pack(fill="x", pady=(4, 1))
        self.builder_btn.bind("<Button-1>", lambda e: self._toggle_builder())

        # ── ROLES ──
        role_content = self._make_section(sidebar, "ROLES")
        self.role_buttons = {}
        for role, info in ROLE_INFO.items():
            count = sum(1 for s in self.skills if s.get("role") == role)
            btn = tk.Label(role_content,
                           text=f" {info['icon']}  {info['label']}  ({count})",
                           font=(FONT, 10), fg=info["color"], bg=T["sidebar"],
                           anchor="w", padx=6, pady=3, cursor="hand2")
            btn.pack(fill="x", pady=1)
            btn.bind("<Button-1>", lambda e, r=role: self._filter_role(r))
            self.role_buttons[role] = btn

        # ── PAR PLUGIN ──
        plugin_content = self._make_section(sidebar, "PAR PLUGIN")
        self.plugin_buttons = {}
        plugin_names = sorted(set(s.get("plugin_name", "") for s in self.skills if s.get("plugin_name")))
        for pname in plugin_names:
            count = sum(1 for s in self.skills if s.get("plugin_name") == pname)
            btn = tk.Label(plugin_content,
                           text=f" ⚙  {pname}  ({count})",
                           font=(FONT, 9), fg=T["green"], bg=T["sidebar"],
                           anchor="w", padx=6, pady=2, cursor="hand2")
            btn.pack(fill="x", pady=1)
            btn.bind("<Button-1>", lambda e, n=pname: self._filter_plugin(n))
            self.plugin_buttons[pname] = btn

        # ── MARKETPLACE ──
        mkt_content = self._make_section(sidebar, "MARKETPLACE")
        self.mkt_btn = tk.Label(mkt_content,
                                 text=LABELS["marketplace_btn"],
                                 font=(FONT, 10, "bold"), fg=T["accent"], bg=T["sidebar"],
                                 anchor="w", padx=6, pady=4, cursor="hand2")
        self.mkt_btn.pack(fill="x", pady=1)
        self.mkt_btn.bind("<Button-1>", lambda e: self._enter_marketplace())

        # ── Bottom utils ──
        tk.Frame(sidebar, bg=T["border"], height=1).pack(fill="x", pady=6)

        edit_btn = tk.Label(sidebar, text=LABELS["edit_file"],
                            font=(FONT, 9), fg=T["text2"], bg=T["sidebar"],
                            anchor="w", padx=6, pady=3, cursor="hand2")
        edit_btn.pack(fill="x", pady=1)
        edit_btn.bind("<Button-1>", lambda e: open_file(str(SKILLS_FILE)))

        reload_btn = tk.Label(sidebar, text=LABELS["reload"],
                              font=(FONT, 9), fg=T["text2"], bg=T["sidebar"],
                              anchor="w", padx=6, pady=3, cursor="hand2")
        reload_btn.pack(fill="x", pady=1)
        reload_btn.bind("<Button-1>", lambda e: self._reload_data())

        # Stats
        total = len(self.skills)
        custom = sum(1 for s in self.skills if s["source"] == "custom")
        self.stats_label = tk.Label(
            sidebar, text=f"{total} {LABELS['sorts_learned']}\n{custom} {LABELS['sorts_custom']}",
            font=(FONT, 9), fg=T["text_dim"], bg=T["sidebar"], justify="left")
        self.stats_label.pack(anchor="w", pady=(6, 0))

    def _on_sidebar_wheel(self, event):
        self.sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_content(self, parent):
        content = tk.Frame(parent, bg=T["bg"])
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)

        # Search bar
        search_frame = tk.Frame(content, bg=T["card"], padx=10, pady=6)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        tk.Label(search_frame, text="🔍", font=(FONT, 10),
                 fg=T["text_dim"], bg=T["card"]).pack(side="left")
        self.search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=(FONT, 11), bg=T["card"], fg=T["text"],
            insertbackground=T["text"], relief="flat", bd=0)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8)

        # Scrollable skill list
        list_frame = tk.Frame(content, bg=T["bg"])
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.list_canvas = tk.Canvas(list_frame, bg=T["bg"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical",
                                 command=self.list_canvas.yview,
                                 bg=T["border"], troughcolor=T["bg"],
                                 width=8)
        self.list_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.grid(row=0, column=1, sticky="ns")
        self.list_canvas.grid(row=0, column=0, sticky="nsew")

        self.scroll_frame = tk.Frame(self.list_canvas, bg=T["bg"])
        self.canvas_window = self.list_canvas.create_window(
            (0, 0), window=self.scroll_frame, anchor="nw")

        self.scroll_frame.bind("<Configure>",
            lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>",
            lambda e: self.list_canvas.itemconfigure(self.canvas_window, width=e.width))

        # Mousewheel
        self.list_canvas.bind("<Enter>",
            lambda e: self.list_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.list_canvas.bind("<Leave>",
            lambda e: self.list_canvas.unbind_all("<MouseWheel>"))

        # Detail panel
        self.detail_frame = tk.Frame(content, bg=T["detail_bg"], height=170, padx=14, pady=10)
        self.detail_frame.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.detail_frame.grid_propagate(False)
        self.detail_visible = True
        self._show_detail_empty()

    def _on_mousewheel(self, event):
        self.list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # Hide detail panel on scroll to free space — but NOT in builder mode
        if not self.builder_mode and self.detail_visible and self.selected_skill:
            self._hide_detail()

    def _hide_detail(self):
        self.detail_frame.grid_remove()
        self.detail_visible = False

    def _show_detail_panel(self):
        if not self.detail_visible:
            self.detail_frame.grid()
            self.detail_visible = True

    # ── Filtering ─────────────────────────────────────────

    def _clear_filters(self):
        self.current_source = None
        self.current_pack = None
        self.current_role = None
        self.current_plugin = None
        self.marketplace_mode = False

    def _filter(self, source):
        self._clear_filters()
        self.current_source = source
        self._update_sidebar_hl()
        self._refresh_list()

    def _filter_pack(self, pack_name):
        if self.current_pack == pack_name:
            self._filter("all")
            return
        self._clear_filters()
        self.current_pack = pack_name
        self._update_sidebar_hl()
        self._refresh_list()

    def _filter_role(self, role):
        if self.current_role == role:
            self._filter("all")
            return
        self._clear_filters()
        self.current_role = role
        self._update_sidebar_hl()
        self._refresh_list()

    def _filter_plugin(self, plugin_name):
        if self.current_plugin == plugin_name:
            self._filter("all")
            return
        self._clear_filters()
        self.current_plugin = plugin_name
        self._update_sidebar_hl()
        self._refresh_list()

    def _enter_marketplace(self):
        self._clear_filters()
        self.marketplace_mode = True
        if not self.marketplace_data:
            self.marketplace_data = load_marketplace_data()
        self._update_sidebar_hl()
        self._refresh_marketplace()

    def _update_sidebar_hl(self):
        for key, btn in self.source_buttons.items():
            active = key == self.current_source and not self.current_pack and not self.current_role and not self.current_plugin and not self.marketplace_mode
            btn.configure(bg=T["card_select"] if active else T["sidebar"])
        for name, btn in self.pack_buttons.items():
            btn.configure(bg=T["card_select"] if name == self.current_pack else T["sidebar"])
        for role, btn in self.role_buttons.items():
            btn.configure(bg=T["card_select"] if role == self.current_role else T["sidebar"])
        for pname, btn in self.plugin_buttons.items():
            btn.configure(bg=T["card_select"] if pname == self.current_plugin else T["sidebar"])
        self.mkt_btn.configure(bg=T["card_select"] if self.marketplace_mode else T["sidebar"])

    def _get_filtered(self):
        search = self.search_var.get().lower().strip()

        if self.current_pack and self.current_pack in self.packs:
            cmds = set(self.packs[self.current_pack]["commands"])
            pool = [s for s in self.skills if s["command"] in cmds]
        elif self.current_role:
            pool = [s for s in self.skills if s.get("role") == self.current_role]
        elif self.current_plugin:
            pool = [s for s in self.skills if s.get("plugin_name") == self.current_plugin]
        elif self.current_source and self.current_source != "all":
            pool = [s for s in self.skills if s["source"] == self.current_source]
        else:
            pool = list(self.skills)

        if search:
            pool = [s for s in pool
                    if search in s["name"].lower()
                    or search in s["command"].lower()
                    or search in s.get("description", "").lower()]

        pool.sort(key=lambda s: (RARITY_ORDER.get(s.get("rarity", "common"), 5), s["name"]))
        return pool

    def _refresh_list(self):
        if self.marketplace_mode:
            self._refresh_marketplace()
            return

        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.skill_widgets.clear()

        skills = self._get_filtered()
        for skill in skills:
            self._build_skill_card(self.scroll_frame, skill)

        # Re-highlight selected
        if self.selected_skill:
            for s, card in self.skill_widgets:
                if s["command"] == self.selected_skill["command"]:
                    apply_bg(card, T["card_select"])

        shown, total = len(skills), len(self.skills)
        label = f"{shown}/{total}" if shown != total else str(total)
        self.count_label.configure(text=f"{label} {LABELS['sorts']}")
        self.list_canvas.yview_moveto(0)

    def _refresh_marketplace(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.skill_widgets.clear()

        search = self.search_var.get().lower().strip()
        plugins = self.marketplace_data
        if search:
            plugins = [p for p in plugins
                       if search in p["name"].lower()
                       or search in p.get("description", "").lower()
                       or search in p.get("category", "").lower()]

        for plugin in plugins:
            self._build_marketplace_card(self.scroll_frame, plugin)

        self.count_label.configure(text=f"{len(plugins)} {LABELS['plugins_mkt']}")
        self.list_canvas.yview_moveto(0)

    def _reload_data(self):
        self.data = load_skills()
        self.skills = self.data.get("skills", [])
        self.packs = self.data.get("packs", {})
        self._update_stats()
        self._refresh_list()

    def _update_stats(self):
        total = len(self.skills)
        custom = sum(1 for s in self.skills if s["source"] == "custom")
        self.stats_label.configure(text=f"{total} {LABELS['sorts_learned']}\n{custom} {LABELS['sorts_custom']}")
        for key, btn in self.source_buttons.items():
            info = SOURCE_INFO[key]
            count = len(self.skills) if key == "all" else sum(1 for s in self.skills if s["source"] == key)
            btn.configure(text=f" {info['icon']}  {info['label']}  ({count})")

    def _watch_file(self):
        try:
            if SKILLS_FILE.exists():
                mtime = SKILLS_FILE.stat().st_mtime
                if mtime != self._last_mtime:
                    self._last_mtime = mtime
                    if self._skip_next_watch:
                        self._skip_next_watch = False
                    else:
                        self._reload_data()
        except OSError:
            pass
        self.root.after(FILE_WATCH_INTERVAL, self._watch_file)

    # ── Skill Card ────────────────────────────────────────

    def _build_skill_card(self, parent, skill):
        rarity = skill.get("rarity", "common")
        rc = RARITY_COLORS.get(rarity, "#9d9d9d")
        role = skill.get("role", "meta")
        role_c = ROLE_COLORS.get(role, "#FF9F0A")
        is_sel = self.selected_skill and self.selected_skill["command"] == skill["command"]
        bg = T["card_select"] if is_sel else T["card"]

        card = tk.Frame(parent, bg=bg, cursor="hand2", pady=7, padx=0)
        card.pack(fill="x", pady=2, padx=4)

        inner = tk.Frame(card, bg=bg)
        inner.pack(fill="x")

        # Rarity bar
        tk.Frame(inner, bg=rc, width=4).pack(side="left", fill="y", padx=(0, 10))

        # Content column
        col = tk.Frame(inner, bg=bg)
        col.pack(side="left", fill="x", expand=True)

        # Row 1: icon + name + badges
        row1 = tk.Frame(col, bg=bg)
        row1.pack(fill="x")

        tk.Label(row1, text=skill.get("icon", "?"), font=(FONT, 13),
                 fg=T["text"], bg=bg).pack(side="left", padx=(0, 6))
        tk.Label(row1, text=skill["name"], font=(FONT, 11, "bold"),
                 fg=rc, bg=bg).pack(side="left")

        # Builder mode: + or - button
        if self.builder_mode:
            in_pack = skill["command"] in self.builder_pack["commands"]
            bld_text = " - " if in_pack else " + "
            bld_color = T["red"] if in_pack else T["green"]
            bld_btn = tk.Label(row1, text=bld_text, font=(FONT, 10, "bold"),
                               fg=bld_color, bg=bg, cursor="hand2", padx=4)
            bld_btn.pack(side="right", padx=(4, 8))
            if in_pack:
                bld_btn.bind("<Button-1>", lambda e, s=skill: self._builder_remove(s))
            else:
                bld_btn.bind("<Button-1>", lambda e, s=skill: self._builder_add(s))

        # Badges (right side)
        inv = skill.get("invocation", "slash")
        inv_text = "SLASH" if inv == "slash" else "AUTO"
        inv_color = T["accent"] if inv == "slash" else T["text_dim"]
        tk.Label(row1, text=inv_text, font=(FONT, 7, "bold"),
                 fg=inv_color, bg=bg).pack(side="right", padx=(4, 8))
        tk.Label(row1, text=role.upper(), font=(FONT, 7, "bold"),
                 fg=role_c, bg=bg).pack(side="right", padx=2)

        # Row 2: description
        tk.Label(col, text=skill.get("description", ""), font=(FONT, 9),
                 fg=T["text2"], bg=bg, anchor="w").pack(fill="x", pady=(1, 0))

        # Row 3: sub-modes preview
        submodes = skill.get("submodes", [])
        if submodes:
            preview = "  ".join(f"·{s['label']}" for s in submodes[:8])
            tk.Label(col, text=preview, font=(FONT_MONO, 8),
                     fg=T["text_dim"], bg=bg, anchor="w").pack(fill="x", pady=(2, 0))

        # Click binding
        if self.builder_mode:
            bind_recursive(card, "<Button-1>", lambda e, s=skill: self._builder_toggle(s))
        else:
            bind_recursive(card, "<Button-1>", lambda e, s=skill: self._select_skill(s))
        self.skill_widgets.append((skill, card))

    # ── Marketplace Card ──────────────────────────────────

    def _build_marketplace_card(self, parent, plugin):
        installed = plugin.get("installed", False)
        bg = T["card"]
        border_color = T["green"] if installed else T["border"]

        card = tk.Frame(parent, bg=bg, cursor="hand2", pady=7, padx=0)
        card.pack(fill="x", pady=2, padx=4)

        inner = tk.Frame(card, bg=bg)
        inner.pack(fill="x")

        # Status bar
        tk.Frame(inner, bg=border_color, width=4).pack(side="left", fill="y", padx=(0, 10))

        col = tk.Frame(inner, bg=bg)
        col.pack(side="left", fill="x", expand=True)

        # Row 1: name + badges
        row1 = tk.Frame(col, bg=bg)
        row1.pack(fill="x")

        tk.Label(row1, text="⚙", font=(FONT, 13), fg=T["text"], bg=bg).pack(side="left", padx=(0, 6))
        tk.Label(row1, text=plugin["name"], font=(FONT, 11, "bold"),
                 fg=T["green"] if installed else T["text"], bg=bg).pack(side="left")

        # Install count
        count = plugin.get("install_count", 0)
        if count > 0:
            tk.Label(row1, text=f"▲ {format_count(count)}", font=(FONT, 7),
                     fg=T["text_dim"], bg=bg).pack(side="right", padx=(4, 8))

        # Badge
        badge_text = LABELS["installed"] if installed else LABELS["available"]
        badge_color = T["green"] if installed else T["text_dim"]
        tk.Label(row1, text=badge_text, font=(FONT, 7, "bold"),
                 fg=badge_color, bg=bg).pack(side="right", padx=2)

        # Marketplace
        tk.Label(row1, text=plugin.get("marketplace", ""), font=(FONT, 7),
                 fg=T["text_dim"], bg=bg).pack(side="right", padx=4)

        # Row 2: description
        desc = plugin.get("description", "")
        if len(desc) > 120:
            desc = desc[:117] + "..."
        tk.Label(col, text=desc, font=(FONT, 9),
                 fg=T["text2"], bg=bg, anchor="w").pack(fill="x", pady=(1, 0))

        # Row 3: category
        cat = plugin.get("category", "")
        if cat:
            tk.Label(col, text=cat.upper(), font=(FONT, 7), fg=T["text_dim"],
                     bg=bg, anchor="w").pack(fill="x", pady=(2, 0))

        # Click = copy install command (if not installed)
        if not installed:
            cmd = f"claude plugins install {plugin['name']} from {plugin['marketplace']}"
            bind_recursive(card, "<Button-1>", lambda e, c=cmd: self._copy(c))
        else:
            bind_recursive(card, "<Button-1>", lambda e, p=plugin: self._show_marketplace_detail(p))

    def _show_marketplace_detail(self, plugin):
        self._show_detail_panel()
        for w in self.detail_frame.winfo_children():
            w.destroy()

        header = tk.Frame(self.detail_frame, bg=T["detail_bg"])
        header.pack(fill="x")

        tk.Label(header, text=f"⚙  {plugin['name']}",
                 font=(FONT, 13, "bold"), fg=T["green"],
                 bg=T["detail_bg"]).pack(side="left")
        tk.Label(header, text=LABELS["installed"],
                 font=(FONT, 9, "bold"), fg=T["green"],
                 bg=T["detail_bg"]).pack(side="right")

        tk.Label(self.detail_frame, text=plugin.get("description", ""),
                 font=(FONT, 9), fg=T["text2"],
                 bg=T["detail_bg"], anchor="w", wraplength=500, justify="left"
                 ).pack(fill="x", pady=(2, 4))

        info = f"Marketplace: {plugin['marketplace']}  |  Category: {plugin.get('category', '?')}  |  {format_count(plugin.get('install_count', 0))} installs"
        tk.Label(self.detail_frame, text=info, font=(FONT, 8),
                 fg=T["text_dim"], bg=T["detail_bg"]).pack(anchor="w")

    # ── Selection & Copy ──────────────────────────────────

    def _select_skill(self, skill):
        self.selected_skill = skill

        for s, card in self.skill_widgets:
            target = T["card_select"] if s["command"] == skill["command"] else T["card"]
            apply_bg(card, target)

        self._show_detail_panel()
        self._copy(skill["command"])
        self._show_detail(skill)

    def _copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._show_copy_feedback(text)

    def _show_copy_feedback(self, text):
        if self._copy_job:
            self.root.after_cancel(self._copy_job)
        if hasattr(self, "copy_label") and self.copy_label.winfo_exists():
            self.copy_label.configure(text=f"✓  {text}  {LABELS['copied']}", fg=T["green"])
            self._copy_job = self.root.after(
                1800, lambda: self.copy_label.configure(
                    text=LABELS["copy_hint"], fg=T["text_dim"])
                if self.copy_label.winfo_exists() else None)

    # ── Detail Panel ──────────────────────────────────────

    def _show_detail_empty(self):
        for w in self.detail_frame.winfo_children():
            w.destroy()
        tk.Label(self.detail_frame,
                 text=LABELS["empty_detail"],
                 font=(FONT, 10), fg=T["text_dim"], bg=T["detail_bg"]).pack(pady=30)

    def _show_detail(self, skill):
        for w in self.detail_frame.winfo_children():
            w.destroy()

        rarity = skill.get("rarity", "common")
        rc = RARITY_COLORS.get(rarity, "#9d9d9d")

        # Header
        header = tk.Frame(self.detail_frame, bg=T["detail_bg"])
        header.pack(fill="x")

        tk.Label(header, text=f"{skill.get('icon', '?')}  {skill['name']}",
                 font=(FONT, 13, "bold"), fg=rc,
                 bg=T["detail_bg"]).pack(side="left")
        tk.Label(header, text=RARITY_LABELS.get(rarity, ""),
                 font=(FONT, 9, "bold"), fg=rc,
                 bg=T["detail_bg"]).pack(side="right")

        # Command
        tk.Label(self.detail_frame, text=skill["command"],
                 font=(FONT_MONO, 11), fg=T["accent"],
                 bg=T["detail_bg"], anchor="w").pack(fill="x", pady=(2, 0))

        # Description
        tk.Label(self.detail_frame, text=skill.get("description", ""),
                 font=(FONT, 9), fg=T["text2"],
                 bg=T["detail_bg"], anchor="w", wraplength=500, justify="left"
                 ).pack(fill="x", pady=(2, 4))

        # Sub-modes
        submodes = skill.get("submodes", [])
        if submodes:
            sub_frame = tk.Frame(self.detail_frame, bg=T["detail_bg"])
            sub_frame.pack(fill="x", pady=(2, 0))

            for sm in submodes:
                btn = tk.Frame(sub_frame, bg=T["border"], padx=8, pady=4, cursor="hand2")
                btn.pack(side="left", padx=(0, 6), pady=2)

                tk.Label(btn, text=sm["label"], font=(FONT_MONO, 9, "bold"),
                         fg=T["accent"], bg=T["border"]).pack(anchor="w")
                tk.Label(btn, text=sm["desc"], font=(FONT, 7),
                         fg=T["text2"], bg=T["border"]).pack(anchor="w")

                bind_recursive(btn, "<Button-1>",
                               lambda e, cmd=sm["cmd"]: self._copy(cmd))

        # Copy feedback
        self.copy_label = tk.Label(
            self.detail_frame,
            text=LABELS["copy_hint"],
            font=(FONT, 8), fg=T["text_dim"], bg=T["detail_bg"])
        self.copy_label.pack(anchor="e", pady=(6, 0))

    # ── Pack Builder ──────────────────────────────────────

    def _toggle_builder(self):
        if self.builder_mode:
            self._exit_builder()
        else:
            self._enter_builder()

    def _enter_builder(self):
        self.builder_mode = True
        self.builder_pack = {"name": "", "icon": "⚔", "description": "", "commands": []}
        self.builder_btn.configure(text=LABELS["builder_exit"], fg=T["red"])
        self._show_builder_panel()
        self._refresh_list()

    def _exit_builder(self):
        self.builder_mode = False
        self.builder_pack = {"name": "", "icon": "⚔", "description": "", "commands": []}
        self.builder_btn.configure(text=LABELS["builder_enter"], fg=T["accent"])
        self._show_detail_empty()
        self._refresh_list()

    def _exit_builder_mode_silent(self):
        """Exit builder without refreshing (caller handles it)."""
        self.builder_mode = False
        self.builder_pack = {"name": "", "icon": "⚔", "description": "", "commands": []}
        self.builder_btn.configure(text=LABELS["builder_enter"], fg=T["accent"])

    def _builder_toggle(self, skill):
        cmd = skill["command"]
        if cmd in self.builder_pack["commands"]:
            self.builder_pack["commands"].remove(cmd)
        else:
            self.builder_pack["commands"].append(cmd)
        self._show_builder_panel()
        self._refresh_list()

    def _builder_add(self, skill):
        cmd = skill["command"]
        if cmd not in self.builder_pack["commands"]:
            self.builder_pack["commands"].append(cmd)
        self._show_builder_panel()
        self._refresh_list()

    def _builder_remove(self, skill):
        cmd = skill["command"]
        if cmd in self.builder_pack["commands"]:
            self.builder_pack["commands"].remove(cmd)
        self._show_builder_panel()
        self._refresh_list()

    def _show_builder_panel(self):
        # Preserve name from entry if it exists
        if hasattr(self, 'builder_name_var') and self.builder_name_var:
            self.builder_pack["name"] = self.builder_name_var.get()
        for w in self.detail_frame.winfo_children():
            w.destroy()

        # Increase height for builder
        self.detail_frame.configure(height=200)

        # Title
        tk.Label(self.detail_frame, text=LABELS["builder_title"],
                 font=(FONT, 10, "bold"), fg=T["accent"],
                 bg=T["detail_bg"]).pack(anchor="w")

        # Name field
        name_row = tk.Frame(self.detail_frame, bg=T["detail_bg"])
        name_row.pack(fill="x", pady=(4, 2))
        tk.Label(name_row, text=LABELS["builder_name"], font=(FONT, 9), fg=T["text2"],
                 bg=T["detail_bg"]).pack(side="left")
        self.builder_name_var = tk.StringVar(value=self.builder_pack.get("name", ""))
        name_entry = tk.Entry(name_row, textvariable=self.builder_name_var,
                              font=(FONT, 10), bg=T["card"], fg=T["text"],
                              insertbackground=T["text"], relief="flat", bd=1, width=25)
        name_entry.pack(side="left", padx=8)

        # Icon selector
        icon_row = tk.Frame(self.detail_frame, bg=T["detail_bg"])
        icon_row.pack(fill="x", pady=2)
        tk.Label(icon_row, text=LABELS["builder_icon"], font=(FONT, 9), fg=T["text2"],
                 bg=T["detail_bg"]).pack(side="left")
        self._builder_icon_var = self.builder_pack.get("icon", "⚔")
        for emoji in EMOJI_PALETTE:
            ebtn = tk.Label(icon_row, text=emoji, font=(FONT, 12),
                            bg=T["detail_bg"], cursor="hand2", padx=2)
            if emoji == self._builder_icon_var:
                ebtn.configure(bg=T["card_select"])
            ebtn.pack(side="left", padx=1)
            ebtn.bind("<Button-1>", lambda e, em=emoji: self._builder_set_icon(em))

        # Skills in pack
        skills_row = tk.Frame(self.detail_frame, bg=T["detail_bg"])
        skills_row.pack(fill="x", pady=2)
        cmds = self.builder_pack.get("commands", [])
        names = []
        for cmd in cmds:
            match = next((s for s in self.skills if s["command"] == cmd), None)
            names.append(match["name"] if match else cmd)
        preview = ", ".join(names) if names else LABELS["builder_empty"]
        tk.Label(skills_row, text=f"Sorts ({len(cmds)}): {preview}",
                 font=(FONT, 8), fg=T["text2"], bg=T["detail_bg"],
                 wraplength=450, justify="left").pack(anchor="w")

        # Buttons
        btn_row = tk.Frame(self.detail_frame, bg=T["detail_bg"])
        btn_row.pack(fill="x", pady=(6, 0))

        save_btn = tk.Label(btn_row, text=LABELS["builder_save"], font=(FONT, 10, "bold"),
                            fg="#fff", bg=T["green"], cursor="hand2", padx=10, pady=4)
        save_btn.pack(side="left", padx=(0, 8))
        save_btn.bind("<Button-1>", lambda e: self._builder_save())

        cancel_btn = tk.Label(btn_row, text=LABELS["builder_cancel"], font=(FONT, 10),
                              fg=T["text2"], bg=T["border"], cursor="hand2", padx=10, pady=4)
        cancel_btn.pack(side="left")
        cancel_btn.bind("<Button-1>", lambda e: self._exit_builder())

    def _builder_set_icon(self, emoji):
        self.builder_pack["icon"] = emoji
        self._builder_icon_var = emoji
        self._show_builder_panel()

    def _builder_save(self):
        name = self.builder_name_var.get().strip()
        if not name:
            return
        cmds = self.builder_pack.get("commands", [])
        if not cmds:
            return

        self.packs[name] = {
            "icon": self.builder_pack.get("icon", "⚔"),
            "description": f"Pack custom: {name}",
            "commands": cmds,
        }
        self.data["packs"] = self.packs

        # Save to file with watch guard
        self._skip_next_watch = True
        with open(SKILLS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        self._last_mtime = SKILLS_FILE.stat().st_mtime

        # Rebuild sidebar packs
        self._exit_builder()
        self._rebuild_sidebar_packs()

    def _rebuild_sidebar_packs(self):
        """Rebuild pack buttons after adding/modifying a pack."""
        _, pack_content = self.section_frames.get("PACKS", (None, None))
        if pack_content is None:
            return

        # Remove old pack buttons (keep builder button)
        for name, btn in self.pack_buttons.items():
            btn.destroy()
        self.pack_buttons.clear()

        # Re-insert before builder button
        for name, pack in self.packs.items():
            btn = tk.Label(pack_content,
                           text=f" {pack['icon']}  {name}",
                           font=(FONT, 10), fg="#c8782a", bg=T["sidebar"],
                           anchor="w", padx=6, pady=3, cursor="hand2")
            btn.pack(fill="x", pady=1, before=self.builder_btn)
            btn.bind("<Button-1>", lambda e, n=name: self._filter_pack(n))
            self.pack_buttons[name] = btn

    # ── Opacity ───────────────────────────────────────────

    def _on_opacity(self, value):
        val = int(value)
        self.config["opacity"] = val
        self.root.attributes("-alpha", val / 100)
        save_config(self.config)


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    SkillDeck(root)
    root.mainloop()
