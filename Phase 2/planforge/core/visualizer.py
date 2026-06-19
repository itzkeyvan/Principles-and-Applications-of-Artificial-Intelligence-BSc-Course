
from __future__ import annotations
import json
import textwrap
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from .loader import load_problem
from .models import Rect
from .validator import validate_assignment
from .quality import layout_quality_score
from .geometry import touches_boundary, shared_wall_length, adjacency_graph, used_area

APP_BG = '#f3f6fb'
SIDEBAR_BG = '#0f172a'
SIDEBAR_PANEL = '#17213a'
CARD_BG = '#ffffff'
INK = '#102033'
MUTED = '#66758a'
ACCENT = '#2563eb'
ACCENT_DARK = '#1d4ed8'
GOOD = '#16a34a'
BAD = '#dc2626'
WARN = '#f59e0b'
WALL = '#172033'
DOOR = '#b7793a'
WINDOW = '#0284c7'
UNUSED = '#fee2e2'
CANVAS_BG = '#f7f9fc'
GRID = '#edf2f7'
PANEL_LINE = '#d7e0ed'

ROOM_COLORS = {
    'hall': '#e9eef7',
    'living': '#cfe8ff',
    'kitchen': '#ffe8a8',
    'bedroom': '#d9f5df',
    'bath': '#dbeafe',
    'laundry': '#eadcff',
    'closet': '#f1e8d8',
    'storage': '#eadfce',
    'balcony': '#d5f7ee',
    'office': '#ffd7e8',
}

ICONS = {
    'hall': '↔',
    'living': '●',
    'kitchen': '▣',
    'bedroom': '▢',
    'bath': '◌',
    'laundry': '◍',
    'closet': '□',
    'storage': '▤',
    'balcony': '☼',
    'office': '✎',
}


def _install_app_icon(root: tk.Tk):
    """Install a small generated PlanForge icon without external assets."""
    try:
        img = tk.PhotoImage(width=32, height=32)
        img.put('#0f172a', to=(0, 0, 32, 32))
        img.put('#14b8a6', to=(6, 5, 18, 27))
        img.put('#38bdf8', to=(14, 5, 26, 16))
        img.put('#22c55e', to=(14, 16, 26, 27))
        img.put('#0f172a', to=(11, 10, 20, 15))
        img.put('#0f172a', to=(11, 17, 20, 22))
        root.iconphoto(False, img)
        root._planforge_icon = img
    except Exception:
        pass


def run_app(default_example: str | None = None):
    root = tk.Tk()
    root.title('PlanForge Studio')
    _install_app_icon(root)
    root.geometry('1600x950')
    root.minsize(1280, 820)
    # Open maximized/full-screen-style by default while keeping normal window controls.
    try:
        root.state('zoomed')  # Windows
    except tk.TclError:
        try:
            root.attributes('-zoomed', True)  # Linux/X11
        except tk.TclError:
            pass
    PlanForgeApp(root, default_example)
    root.mainloop()


class ModernButton(tk.Frame):
    def __init__(self, master, text, command, bg=ACCENT, fg='white', hover=None):
        super().__init__(master, bg=master['bg'])
        self.command = command
        self.bg_normal = bg
        self.bg_hover = hover or ACCENT_DARK
        self.canvas = tk.Canvas(self, height=40, highlightthickness=0, bg=master['bg'], cursor='hand2')
        self.canvas.pack(fill=tk.X, expand=True)
        self.text = text
        self.fg = fg
        self.canvas.bind('<Button-1>', lambda e: self.command())
        self.canvas.bind('<Enter>', lambda e: self._draw(self.bg_hover))
        self.canvas.bind('<Leave>', lambda e: self._draw(self.bg_normal))
        self.canvas.bind('<Configure>', lambda e: self._draw(self.bg_normal))

    def _draw(self, color):
        self.canvas.delete('all')
        w = max(2, self.canvas.winfo_width())
        self.canvas.create_rectangle(0, 0, w, 40, fill=color, outline=color)
        self.canvas.create_text(w / 2, 20, text=self.text, fill=self.fg, font=('Segoe UI', 10, 'bold'))




class ModernScrollbar(tk.Canvas):
    """A small themed scrollbar that matches the dark JSON editor."""
    def __init__(self, master, orient='vertical', command=None, thickness=10):
        self.orient = orient
        self.command = command
        self.thickness = thickness
        width = thickness if orient == 'vertical' else 1
        height = 1 if orient == 'vertical' else thickness
        super().__init__(master, width=width, height=height, bg='#07111f', highlightthickness=0, bd=0, cursor='hand2')
        self.first = 0.0
        self.last = 1.0
        self.dragging = False
        self.drag_offset = 0
        self.track = '#0b1728'
        self.thumb = '#64748b'
        self.thumb_hover = '#64748b'
        self.current_thumb = self.thumb
        self.bind('<Configure>', lambda e: self._draw())
        self.bind('<Enter>', lambda e: self._set_hover(True))
        self.bind('<Leave>', lambda e: self._set_hover(False))
        self.bind('<Button-1>', self._click)
        self.bind('<B1-Motion>', self._drag)
        self.bind('<ButtonRelease-1>', lambda e: setattr(self, 'dragging', False))

    def _set_hover(self, hover):
        self.current_thumb = self.thumb_hover if hover else self.thumb
        self._draw()

    def set(self, first, last):
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(0.0, min(1.0, float(last)))
        self._draw()

    def _axis_size(self):
        return self.winfo_height() if self.orient == 'vertical' else self.winfo_width()

    def _thumb_bounds(self):
        size = max(1, self._axis_size())
        min_len = 28 if self.orient == 'vertical' else 34
        span = max(min_len, int((self.last - self.first) * size))
        span = min(span, size)
        start = int(self.first * size)
        if start + span > size:
            start = max(0, size - span)
        return start, start + span

    def _draw(self):
        self.delete('all')
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        radius = 4
        self.create_rectangle(0, 0, w, h, fill=self.track, outline=self.track)
        if self.last - self.first >= 0.999:
            # Still show a subtle rail so users know the JSON area is scroll-aware.
            self.create_rectangle(3, 3, max(3, w-3), max(3, h-3), fill='#132035', outline='#132035')
            return
        start, end = self._thumb_bounds()
        if self.orient == 'vertical':
            self.create_rectangle(2, start + 2, w - 2, end - 2, fill=self.current_thumb, outline=self.current_thumb)
        else:
            self.create_rectangle(start + 2, 2, end - 2, h - 2, fill=self.current_thumb, outline=self.current_thumb)

    def _position_fraction(self, event):
        size = max(1, self._axis_size())
        coord = event.y if self.orient == 'vertical' else event.x
        start, end = self._thumb_bounds()
        span = max(1, end - start)
        if start <= coord <= end:
            self.dragging = True
            self.drag_offset = coord - start
            return None
        return max(0.0, min(1.0, (coord - span / 2) / size))

    def _click(self, event):
        frac = self._position_fraction(event)
        if frac is not None and self.command:
            self.command('moveto', frac)

    def _drag(self, event):
        if not self.dragging or not self.command:
            return
        size = max(1, self._axis_size())
        coord = event.y if self.orient == 'vertical' else event.x
        start, end = self._thumb_bounds()
        span = max(1, end - start)
        frac = max(0.0, min(1.0, (coord - self.drag_offset) / max(1, size - span)))
        # Convert thumb travel to text view fraction.
        visible = max(0.001, self.last - self.first)
        max_first = max(0.0, 1.0 - visible)
        self.command('moveto', min(max_first, frac * max_first))


class PlanForgeApp:
    def __init__(self, root: tk.Tk, default_example: str | None):
        self.root = root
        self.root.configure(bg=APP_BG)
        self._setup_style()
        base = Path(__file__).resolve().parents[1] / 'examples'
        preferred_order = {
            'easy_apartment.json': 0,
            'medium_apartment.json': 1,
            'hard_apartment.json': 2,
            'bonus_challenge_apartment.json': 3,
            'unsat_apartment.json': 4,
        }
        self.examples = sorted(base.glob('*.json'), key=lambda p: (preferred_order.get(p.name, 99), p.name))
        self.examples_by_name = {p.name: p for p in self.examples}
        self.problem = None
        self.problem_path: Path | None = None
        self.assignment = None
        self.report = None
        self.current_json_text = ''
        self.scale = 56
        self.margin_x = 58
        self.margin_y = 104
        self.visual_mode_active = False
        self.dfs_zoom = 1.0
        self.dfs_pan_x = 0.0
        self.dfs_pan_y = 0.0
        self.dfs_manual_view = False
        self.dfs_dragging = False
        self.dfs_last_xy = None
        self.dfs_graph_region = None
        self.visual_trace_finished = False
        self._build_ui()
        target = Path(default_example) if default_example else (self.examples[0] if self.examples else None)
        if target:
            self.load_example(target)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('TCombobox', padding=8, fieldbackground='white', background='white', foreground=INK)
        style.map('TCombobox', fieldbackground=[('readonly', 'white')])

    def _build_ui(self):
        container = tk.Frame(self.root, bg=APP_BG)
        container.pack(fill=tk.BOTH, expand=True)

        shell = tk.Frame(container, bg=APP_BG)
        shell.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.sidebar = tk.Frame(shell, bg=SIDEBAR_BG, width=340)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        main = tk.Frame(shell, bg=APP_BG)
        main.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self._build_sidebar()
        self._build_main(main)

    def _build_sidebar(self):
        top = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        top.pack(fill=tk.X, padx=18, pady=(18, 10))
        tk.Label(top, text='PlanForge', bg=SIDEBAR_BG, fg='white', font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        tk.Label(top, text='CSP room-layout studio', bg=SIDEBAR_BG, fg='#aab7cf', font=('Segoe UI', 10)).pack(anchor='w', pady=(2, 0))

        # Scrollable sidebar with a visible, themed scrollbar.  The sidebar can
        # grow when status messages are long, but lower controls such as
        # "View JSON" must always remain reachable.
        side_scroll_shell = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        side_scroll_shell.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.side_canvas = tk.Canvas(side_scroll_shell, bg=SIDEBAR_BG, highlightthickness=0, bd=0)
        self.side_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.side_scrollbar = ModernScrollbar(side_scroll_shell, orient='vertical', command=self.side_canvas.yview, thickness=13)
        self.side_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 3), pady=(0, 4))
        self.side_canvas.configure(yscrollcommand=self.side_scrollbar.set)
        self.side_content = tk.Frame(self.side_canvas, bg=SIDEBAR_BG)
        self.side_window = self.side_canvas.create_window(0, 0, anchor='nw', window=self.side_content)
        self.side_content.bind('<Configure>', lambda e: self.side_canvas.configure(scrollregion=self.side_canvas.bbox('all')))
        self.side_canvas.bind('<Configure>', lambda e: self.side_canvas.itemconfigure(self.side_window, width=e.width))

        def _side_wheel(e):
            self.side_canvas.yview_scroll(int(-1*(getattr(e, 'delta', 0)/120)) if getattr(e, 'delta', 0) else (-3 if getattr(e, 'num', None) == 4 else 3), 'units')
            return 'break'
        self.side_canvas.bind('<MouseWheel>', _side_wheel)
        self.side_canvas.bind('<Button-4>', _side_wheel)
        self.side_canvas.bind('<Button-5>', _side_wheel)
        self.side_content.bind('<MouseWheel>', _side_wheel)
        self.side_content.bind('<Button-4>', _side_wheel)
        self.side_content.bind('<Button-5>', _side_wheel)

        self.file_card = self._side_card('Problem file')
        controls = tk.Frame(self.file_card, bg=SIDEBAR_PANEL)
        controls.pack(fill=tk.X, padx=16, pady=(0, 16))
        controls.grid_columnconfigure(0, weight=1)

        self.example_var = tk.StringVar()
        self.combo = ttk.Combobox(
            controls,
            textvariable=self.example_var,
            state='readonly',
            values=[p.name for p in self.examples]
        )
        self.combo.grid(row=0, column=0, sticky='ew', pady=(0, 10), ipady=2)
        self.combo.bind('<<ComboboxSelected>>', self._on_example_selected)

        solve_btn = ModernButton(controls, 'Solve layout', self.solve, bg=ACCENT)
        solve_btn.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        grade_btn = ModernButton(controls, 'Run public grade', self.run_public_grade, bg='#0f766e', hover='#115e59')
        grade_btn.grid(row=2, column=0, sticky='ew', pady=(0, 10))

        visual_row = tk.Frame(controls, bg=SIDEBAR_PANEL)
        visual_row.grid(row=3, column=0, sticky='ew', pady=(0, 10))
        visual_row.grid_columnconfigure(1, weight=1)
        tk.Label(visual_row, text='Delay', bg=SIDEBAR_PANEL, fg='#cbd5e1', font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w')
        self.delay_var = tk.StringVar(value='80')
        delay_entry = tk.Entry(visual_row, textvariable=self.delay_var, bg='#0b1324', fg='white', insertbackground='white', relief='flat', justify='center', font=('Segoe UI', 9))
        delay_entry.grid(row=0, column=1, sticky='ew', padx=(8, 6), ipady=5)
        tk.Label(visual_row, text='ms', bg=SIDEBAR_PANEL, fg='#94a3b8', font=('Segoe UI', 9)).grid(row=0, column=2, sticky='e')

        visual_btn = ModernButton(controls, 'Visual solve', self.visual_solve, bg='#7c3aed', hover='#6d28d9')
        visual_btn.grid(row=4, column=0, sticky='ew')

        self.result_card = self._side_card('Run status')
        self.status_badge = tk.Label(self.result_card, text='READY', bg='#1e293b', fg='#cbd5e1', font=('Segoe UI', 10, 'bold'), padx=10, pady=4)
        self.status_badge.pack(anchor='w', padx=16, pady=(0, 8))
        self.result_body = tk.Label(self.result_card, text='Choose a JSON file and run the solver.', bg=SIDEBAR_PANEL, fg='#cbd5e1', font=('Segoe UI', 10), justify='left', anchor='w', wraplength=285)
        self.result_body.pack(fill=tk.X, padx=16, pady=(0, 16))

        self.metrics_card = self._side_card('Metrics')
        grid = tk.Frame(self.metrics_card, bg=SIDEBAR_PANEL)
        grid.pack(fill=tk.X, padx=12, pady=(0, 14))
        self.metric_score = self._metric(grid, 'Score', '— / 100', 0, 0)
        self.metric_valid = self._metric(grid, 'Valid', '—', 0, 1)
        self.metric_nodes = self._metric(grid, 'Nodes', '—', 1, 0)
        self.metric_time = self._metric(grid, 'Runtime', '—', 1, 1)


        json_card = self._side_card('Selected JSON')
        json_body = tk.Frame(json_card, bg=SIDEBAR_PANEL)
        json_body.pack(fill=tk.X, padx=16, pady=(0, 16))
        self.json_file_label = tk.Label(
            json_body,
            text='No JSON selected',
            bg=SIDEBAR_PANEL,
            fg='#cbd5e1',
            font=('Segoe UI', 9),
            anchor='w'
        )
        self.json_file_label.pack(fill=tk.X, pady=(0, 8))
        self.view_json_btn = ModernButton(
            json_body,
            'View JSON',
            self._open_json_window,
            bg='#1e293b',
            hover='#334155'
        )
        self.view_json_btn.pack(fill=tk.X)

        # Signature is part of the scrollable sidebar content, not a fixed footer;
        # this keeps the sidebar usable on smaller screens and makes the visible
        # scrollbar meaningful.
        self._build_signature_card()

        # Make mouse-wheel scrolling work no matter which sidebar child is under
        # the cursor. Tkinter does not automatically propagate wheel events from
        # labels/buttons/entries to the canvas on all platforms.
        for child in self.side_content.winfo_children():
            self._bind_sidebar_mousewheel_recursive(child)

    def _build_signature_card(self):
        parent = getattr(self, 'side_content', self.sidebar)
        footer = tk.Frame(parent, bg=SIDEBAR_BG)
        footer.pack(fill=tk.X, padx=18, pady=(0, 14))
        sep = tk.Frame(footer, bg='#26354f', height=1)
        sep.pack(fill=tk.X, pady=(2, 8))
        tk.Label(
            footer,
            text='Designed by Saleh · @msmahdinejad',
            bg=SIDEBAR_BG,
            fg='#94a3b8',
            font=('Segoe UI', 9),
            anchor='center'
        ).pack(fill=tk.X)

    def _bind_sidebar_mousewheel_recursive(self, widget):
        def _side_wheel(e):
            delta = getattr(e, 'delta', 0)
            if delta:
                units = int(-1 * (delta / 120))
            else:
                units = -3 if getattr(e, 'num', None) == 4 else 3
            self.side_canvas.yview_scroll(units, 'units')
            return 'break'
        try:
            widget.bind('<MouseWheel>', _side_wheel)
            widget.bind('<Button-4>', _side_wheel)
            widget.bind('<Button-5>', _side_wheel)
        except Exception:
            pass
        for child in getattr(widget, 'winfo_children', lambda: [])():
            self._bind_sidebar_mousewheel_recursive(child)

    def _side_card(self, title: str) -> tk.Frame:
        parent = getattr(self, 'side_content', self.sidebar)
        card = tk.Frame(parent, bg=SIDEBAR_PANEL, highlightthickness=1, highlightbackground='#24324a')
        card.pack(fill=tk.X, padx=18, pady=(0, 12))
        tk.Label(card, text=title, bg=SIDEBAR_PANEL, fg='white', font=('Segoe UI', 11, 'bold')).pack(anchor='w', padx=14, pady=(12, 10))
        return card

    def _metric(self, parent, label, value, row, col):
        card = tk.Frame(parent, bg='#0b1324', highlightbackground='#26354f', highlightthickness=1)
        card.grid(row=row, column=col, sticky='nsew', padx=4, pady=4)
        parent.columnconfigure(col, weight=1)
        tk.Label(card, text=label.upper(), bg='#0b1324', fg='#8fa3c0', font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=10, pady=(8, 0))
        val = tk.Label(card, text=value, bg='#0b1324', fg='white', font=('Segoe UI', 15, 'bold'))
        val.pack(anchor='w', padx=10, pady=(2, 10))
        return val

    def _build_main(self, parent):
        top = tk.Frame(parent, bg=APP_BG)
        top.pack(fill=tk.X, padx=16, pady=(10, 4))
        tk.Label(top, text='Apartment Preview', bg=APP_BG, fg=INK, font=('Segoe UI', 21, 'bold')).pack(side=tk.LEFT)
        self.canvas_shell = tk.Frame(parent, bg=APP_BG)
        self.canvas_shell.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.canvas = tk.Canvas(self.canvas_shell, bg=CANVAS_BG, highlightthickness=1, highlightbackground='#d8e2ef')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Configure>', lambda e: self._redraw_current())
        self.canvas.bind('<MouseWheel>', self._on_graph_mousewheel)
        self.canvas.bind('<Button-4>', self._on_graph_mousewheel)
        self.canvas.bind('<Button-5>', self._on_graph_mousewheel)
        self.canvas.bind('<ButtonPress-1>', self._on_graph_press)
        self.canvas.bind('<B1-Motion>', self._on_graph_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_graph_release)
        # Clear text/dropdown focus when user clicks elsewhere; this prevents the
        # combobox or delay entry from keeping a distracting caret/selection.
        self.root.bind_all('<Button-1>', self._clear_control_focus, add='+')


    def _clear_control_focus(self, event):
        try:
            widget = event.widget
            if isinstance(widget, (tk.Entry, tk.Text, ttk.Combobox)):
                return
            self.root.after(1, self.root.focus_set)
            if hasattr(self, 'combo'):
                try:
                    self.combo.selection_clear()
                except Exception:
                    pass
        except Exception:
            pass

    def _in_dfs_graph(self, x, y):
        region = getattr(self, 'dfs_graph_region', None)
        if not region:
            return False
        gx, gy, gw, gh = region
        return gx <= x <= gx + gw and gy <= y <= gy + gh

    def _on_graph_mousewheel(self, event):
        if not self._in_dfs_graph(event.x, event.y):
            return
        if getattr(event, 'num', None) == 5 or getattr(event, 'delta', 0) < 0:
            factor = 0.78
        else:
            factor = 1.18
        old = max(0.003, min(8.0, self.dfs_zoom))
        new = max(0.003, min(8.0, old * factor))
        factor = new / old
        gx, gy, gw, gh = self.dfs_graph_region
        cx = event.x - (gx + gw / 2)
        cy = event.y - (gy + gh / 2)
        self.dfs_pan_x = cx - factor * (cx - self.dfs_pan_x)
        self.dfs_pan_y = cy - factor * (cy - self.dfs_pan_y)
        self.dfs_zoom = new
        self.dfs_manual_view = True
        self._redraw_current()
        return 'break'

    def _on_graph_press(self, event):
        if self._in_dfs_graph(event.x, event.y):
            self.dfs_dragging = True
            self.dfs_last_xy = (event.x, event.y)
            self.dfs_manual_view = True
            return 'break'

    def _on_graph_drag(self, event):
        if not self.dfs_dragging or not self.dfs_last_xy:
            return
        last_x, last_y = self.dfs_last_xy
        self.dfs_pan_x += event.x - last_x
        self.dfs_pan_y += event.y - last_y
        self.dfs_last_xy = (event.x, event.y)
        self._redraw_current()
        return 'break'

    def _on_graph_release(self, event):
        self.dfs_dragging = False
        self.dfs_last_xy = None

    def _redraw_current(self):
        if getattr(self, 'visual_mode_active', False) and getattr(self, 'current_visual_event', None) is not None:
            try:
                self._show_trace_step(self.current_visual_event, self.current_visual_index, self.current_visual_total)
                return
            except Exception:
                pass
        if self.assignment and self.problem:
            try:
                self.draw_assignment(self.assignment)
            except Exception:
                pass
        elif self.problem:
            try:
                self.clear_canvas(draw_shell=True)
            except Exception:
                pass

    def _set_json_text(self, text: str):
        self.current_json_text = text or ''
        if hasattr(self, 'json_file_label'):
            name = self.problem_path.name if self.problem_path else 'Selected problem'
            lines = self.current_json_text.count('\n') + 1 if self.current_json_text else 0
            self.json_file_label.config(text=f'{name} · {lines} lines')

    def _open_json_window(self):
        if not self.current_json_text:
            messagebox.showinfo('Selected JSON', 'No JSON file has been loaded yet.')
            return
        win = tk.Toplevel(self.root)
        title = self.problem_path.name if self.problem_path else 'Selected JSON'
        win.title(f'PlanForge — {title}')
        win.geometry('760x620')
        win.minsize(560, 420)
        win.configure(bg='#0b1220')
        header = tk.Frame(win, bg='#0b1220')
        header.pack(fill=tk.X, padx=18, pady=(16, 8))
        tk.Label(header, text=title, bg='#0b1220', fg='white', font=('Segoe UI', 15, 'bold')).pack(side=tk.LEFT)
        tk.Label(header, text='scrollable JSON preview', bg='#0b1220', fg='#94a3b8', font=('Segoe UI', 9)).pack(side=tk.RIGHT, pady=(5, 0))
        frame = tk.Frame(win, bg='#07111f', highlightthickness=1, highlightbackground='#26354f')
        frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
        text = tk.Text(
            frame,
            wrap='none',
            font=('Cascadia Mono', 10),
            bg='#07111f',
            fg='#dbeafe',
            insertbackground='#dbeafe',
            selectbackground='#1e3a8a',
            relief='flat',
            padx=14,
            pady=14,
            borderwidth=0
        )
        text.grid(row=0, column=0, sticky='nsew')
        yscroll = ModernScrollbar(frame, orient='vertical', command=text.yview, thickness=10)
        yscroll.grid(row=0, column=1, sticky='ns', padx=(3, 3), pady=5)
        xscroll = ModernScrollbar(frame, orient='horizontal', command=text.xview, thickness=10)
        xscroll.grid(row=1, column=0, sticky='ew', padx=5, pady=(3, 3))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        text.insert(tk.END, self.current_json_text)
        text.config(state='disabled')

    def _set_status(self, badge: str, body: str, kind: str = 'neutral'):
        colors = {
            'neutral': ('#1e293b', '#cbd5e1'),
            'good': ('#dcfce7', '#166534'),
            'bad': ('#fee2e2', '#991b1b'),
            'warn': ('#fef3c7', '#92400e'),
            'blue': ('#dbeafe', '#1d4ed8'),
        }
        bg, fg = colors.get(kind, colors['neutral'])
        self.status_badge.config(text=badge, bg=bg, fg=fg)
        self.result_body.config(text=body)

    def _reset_metrics(self):
        self.metric_score.config(text='— / 100', fg='white')
        self.metric_valid.config(text='—', fg='white')
        self.metric_nodes.config(text='—', fg='white')
        self.metric_time.config(text='—', fg='white')

    def _on_example_selected(self, event=None):
        # Do not rely on Combobox.current(); after focus/scroll events Tk can
        # report a stale index on some platforms.  Use the selected filename.
        name = self.example_var.get()
        path = self.examples_by_name.get(name)
        if path is not None:
            self.load_example(path)

    def load_example(self, path: Path):
        try:
            self.problem = load_problem(path)
            self.problem_path = path
            self.assignment = None
            self.report = None
            self.example_var.set(path.name)
            raw = json.loads(path.read_text(encoding='utf-8'))
            self._set_json_text(json.dumps(raw, indent=2, ensure_ascii=False))
            self._set_status('READY', 'Press Solve layout to run the student solver. Use View selected JSON to inspect the problem file.', 'blue')
            self._reset_metrics()
            self.clear_canvas(draw_shell=True)
        except Exception as e:
            messagebox.showerror('Load error', str(e))

    def solve(self):
        try:
            self.root.focus_set()
        except Exception:
            pass
        self.visual_mode_active = False
        if not self.problem:
            return
        try:
            from planforge.core.engine import solve_with_report
            assignment, report = solve_with_report(self.problem, max_solutions=50000, max_nodes=2000000)
            meta = report.to_dict()
            self.report = report
            score = meta.get('layout_score')
            valid = meta.get('status') == 'valid' and assignment is not None
            self.metric_score.config(text=f'{score:.1f} / 100' if isinstance(score, (int, float)) else '0 / 100', fg=('#86efac' if valid else '#fca5a5'))
            self.metric_valid.config(text='VALID' if valid else 'INVALID', fg=('#86efac' if valid else '#fca5a5'))
            self.metric_nodes.config(text=str(meta.get('nodes', '—')))
            self.metric_time.config(text=f"{meta.get('runtime_sec', 0):.3f}s")
            if not valid:
                lines = [f"Status: {meta.get('status')}", f"Score: {score if score is not None else 0} / 100"]
                if meta.get('error'):
                    lines.append(f"Error: {meta.get('error')}")
                if meta.get('validation_errors'):
                    lines.append('Validation errors:')
                    lines.extend([f'• {e}' for e in meta.get('validation_errors')])
                self._set_status('REJECTED', '\n'.join(lines), 'bad')
                self.clear_canvas(draw_shell=True)
                return
            quality_score, quality_notes = layout_quality_score(self.problem, assignment)
            used = sum(r.area for r in assignment.values())
            total = self.problem.width * self.problem.height
            body = '\n'.join([
                'Validation: passed',
                f'Layout score: {quality_score:.1f} / 100',
                f'Coverage: {used}/{total} cells ({used/total:.0%})',
                f"Student objective: {meta.get('best_score'):.2f}" if isinstance(meta.get('best_score'), (int, float)) else 'Student objective: n/a',
                f"Solutions seen: {meta.get('solutions_seen')}",
                f"Backtracks: {meta.get('backtracks')}",
            ])
            self._set_status('ACCEPTED', body, 'good')
            self.assignment = assignment
            self.draw_assignment(assignment)
        except NotImplementedError as e:
            self._set_status('TODO', str(e), 'bad')
            self.clear_canvas(draw_shell=True)
        except Exception as e:
            messagebox.showerror('Solver error', str(e))


    def _get_visual_delay(self) -> int:
        try:
            delay = int(self.delay_var.get())
        except Exception:
            delay = 80
        return max(0, min(1500, delay))

    def visual_solve(self):
        try:
            self.root.focus_set()
        except Exception:
            pass
        self.visual_mode_active = True
        """Run the real student solver once with tracing enabled, then animate the recorded trace."""
        if not self.problem:
            return
        try:
            from planforge.core.engine import solve_with_report
            delay = self._get_visual_delay()
            self.visual_trace_finished = False
            self.dfs_manual_view = False
            self.dfs_zoom = 1.0
            self.dfs_pan_x = 0.0
            self.dfs_pan_y = 0.0
            self._set_status('TRACING', 'Running the student solver and recording the real backtracking trace...', 'blue')
            self.root.update_idletasks()
            assignment, report = solve_with_report(
                self.problem,
                max_solutions=50000,
                max_nodes=2000000,
                trace=True,
                max_trace_events=2500,
            )
            self.visual_trace = report.trace_events or []
            self.visual_final_assignment = assignment
            self.visual_report = report
            self.report = report
            if not self.visual_trace:
                self._set_status('NO TRACE', 'No visual trace was recorded. Add ctx.on_select_variable, ctx.on_assign and ctx.on_unassign calls inside student/solver.py.', 'warn')
                if assignment:
                    self.assignment = assignment
                    self.draw_assignment(assignment)
                return
            self.metric_score.config(text='visualizing', fg='#c4b5fd')
            self.metric_valid.config(text='TRACE', fg='#c4b5fd')
            self.metric_nodes.config(text=str(report.nodes))
            self.metric_time.config(text=f'{report.runtime_sec:.3f}s')
            self._set_status('VISUAL SOLVE', f'Replaying {len(self.visual_trace)} recorded search events. Delay： {delay} ms', 'blue')
            self._animate_trace(0, delay)
        except Exception as e:
            messagebox.showerror('Visual solver error', str(e))

    def _animate_trace(self, index: int, delay: int):
        trace = getattr(self, 'visual_trace', [])
        if index >= len(trace):
            final_assignment = getattr(self, 'visual_final_assignment', None)
            report = getattr(self, 'visual_report', None)
            if final_assignment:
                self.visual_trace_finished = True
                self.dfs_manual_view = False
                self.assignment = final_assignment
                final_event = {
                    'type': 'solution',
                    'assignment': {k: v.as_tuple() for k, v in final_assignment.items()},
                    'nodes': getattr(report, 'nodes', 0) if report else 0,
                    'backtracks': getattr(report, 'backtracks', 0) if report else 0,
                    'solutions_seen': getattr(report, 'solutions_seen', 0) if report else 0,
                    'pruned_values': getattr(report, 'pruned_values', 0) if report else 0,
                    'variable': 'best solution',
                    'final': True,
                }
                self._show_trace_step(final_event, max(0, len(trace) - 1), max(1, len(trace)))
                if report:
                    score = report.layout_score if report.layout_score is not None else 0
                    self.metric_score.config(text=f'{score:.1f} / 100', fg='#86efac')
                    self.metric_valid.config(text='VALID', fg='#86efac')
                    self.metric_nodes.config(text=str(report.nodes))
                    self.metric_time.config(text=f'{report.runtime_sec:.3f}s')
                    self._set_status('TRACE DONE', f'Final layout and DFS search tree displayed. Solutions seen: {report.solutions_seen}\nBacktracks: {report.backtracks}\nPruned values: {report.pruned_values}', 'good')
            else:
                self._set_status('NO SOLUTION', 'The recorded search finished without a valid solution.', 'bad')
                self.clear_canvas(draw_shell=True)
            return
        event = trace[index]
        self._show_trace_step(event, index, len(trace))
        self.root.after(delay, lambda: self._animate_trace(index + 1, delay))

    def _assignment_from_trace(self, event) -> dict[str, Rect]:
        assignment = {}
        for name, data in (event.get('assignment') or {}).items():
            try:
                assignment[name] = Rect(*data)
            except Exception:
                pass
        return assignment

    def _show_trace_step(self, event, index: int, total: int):
        self.current_visual_event = event
        self.current_visual_index = index
        self.current_visual_total = total
        assignment = self._assignment_from_trace(event)
        self.clear_canvas(draw_shell=True)
        p = self.problem
        m, top, s = self.margin_x, self.margin_y, self.scale
        latest = event.get('variable')
        for name in p.variables:
            if name not in assignment:
                continue
            r = assignment[name]
            color = self._room_color(name)
            x1, y1 = m + r.x*s, top + r.y*s
            x2, y2 = m + r.x2*s, top + r.y2*s
            outline = '#7c3aed' if name == latest else WALL
            width = 5 if name == latest else 3
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=outline, width=width)
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2 - 6, text=name, fill=INK, font=('Segoe UI', 12, 'bold'), width=max(60, x2-x1-10))
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2 + 14, text=f'{r.w}×{r.h} • {r.area} m²', fill=MUTED, font=('Segoe UI', 8))
            self._draw_windows(name, r, m, top, s)
        if assignment:
            self._draw_doors(assignment, m, top, s)
        self._draw_entrance(m, top, s)
        self._draw_trace_panel(event, index, total)

    def _build_dfs_tree(self, upto_index: int):
        """Build a board-style DFS tree from the recorded solver trace.

        Assign events create child nodes. Backtracking closes existing nodes.
        Pruning is shown explicitly as small leaf nodes attached to the current
        DFS state, so students can see where forward checking / AC-3 removed
        values without pretending that pruning is a normal assignment branch.
        """
        trace = getattr(self, 'visual_trace', [])[:upto_index + 1]
        nodes = [{
            'id': 0,
            'parent': None,
            'depth': 0,
            'label': 'root',
            'detail': 'start',
            'type': 'root',
            'event_index': -1,
            'solution': False,
            'closed': False,
            'pruned': False,
            'dead': False,
        }]
        children: dict[int, list[int]] = {0: []}
        stack = [0]
        current_node = 0
        best_solution_node = None
        best_score = float('-inf')

        def add_leaf(parent: int, label: str, detail: str, typ: str, i: int):
            node_id = len(nodes)
            nodes.append({
                'id': node_id,
                'parent': parent,
                'depth': nodes[parent]['depth'] + 1 if 0 <= parent < len(nodes) else 1,
                'label': label,
                'detail': detail,
                'type': typ,
                'event_index': i,
                'solution': typ == 'solution',
                'closed': typ in {'prune', 'dead'},
                'pruned': typ == 'prune',
                'dead': typ == 'dead',
            })
            children.setdefault(parent, []).append(node_id)
            children.setdefault(node_id, [])
            return node_id

        for i, ev in enumerate(trace):
            et = ev.get('type')
            if et == 'assign':
                parent = stack[-1] if stack else 0
                value = ev.get('value')
                if value and len(value) == 4:
                    detail = f"{ev.get('variable', '?')}={value[0]},{value[1]} {value[2]}×{value[3]}"
                else:
                    detail = str(ev.get('variable') or 'assign')
                node_id = len(nodes)
                node = {
                    'id': node_id,
                    'parent': parent,
                    'depth': len(stack),
                    'label': str(ev.get('variable') or f'n{node_id}'),
                    'detail': detail,
                    'type': 'assign',
                    'event_index': i,
                    'solution': False,
                    'closed': False,
                    'pruned': False,
                    'dead': False,
                }
                nodes.append(node)
                children.setdefault(parent, []).append(node_id)
                children.setdefault(node_id, [])
                stack.append(node_id)
                current_node = node_id
            elif et == 'solution':
                current_node = stack[-1] if stack else current_node
                nodes[current_node]['solution'] = True
                nodes[current_node]['type'] = 'solution'
                try:
                    score = float(ev.get('score', 0))
                except Exception:
                    score = 0.0
                if score >= best_score:
                    best_score = score
                    best_solution_node = current_node
            elif et == 'prune':
                parent = stack[-1] if stack else current_node
                count = ev.get('count', 0)
                add_leaf(parent, 'prune', f'−{count} values', 'prune', i)
                current_node = parent
            elif et == 'unassign':
                if len(stack) > 1:
                    popped = stack.pop()
                    nodes[popped]['closed'] = True
                current_node = stack[-1] if stack else 0
            elif et == 'backtrack':
                current_node = stack[-1] if stack else current_node
                if current_node < len(nodes) and current_node != 0:
                    nodes[current_node]['closed'] = True
            elif et == 'select':
                pass

        active = set(stack)
        return nodes, children, active, current_node, best_solution_node

    def _layout_tree_positions(self, nodes, children, visible_ids, plot_x, plot_y, plot_w, plot_h):
        """Return logical top-down tree positions before viewport zoom/pan."""
        if not visible_ids:
            return {}
        max_depth = max(1, max(nodes[i]['depth'] for i in visible_ids))
        next_leaf = 0
        x_units: dict[int, float] = {}

        def dfs(node_id: int):
            nonlocal next_leaf
            kids = [c for c in children.get(node_id, []) if c in visible_ids]
            if not kids:
                x_units[node_id] = float(next_leaf)
                next_leaf += 1
                return x_units[node_id]
            child_xs = [dfs(c) for c in kids]
            x_units[node_id] = sum(child_xs) / len(child_xs)
            return x_units[node_id]

        root_id = 0 if 0 in visible_ids else min(visible_ids)
        dfs(root_id)
        leaf_count = max(1, next_leaf)
        logical_w = max(plot_w, (leaf_count - 1) * 86 + 80)
        logical_h = max(plot_h, max_depth * 92 + 70)
        denom = max(1.0, float(max(x_units.values() or [0])))
        positions = {}
        for node_id, xu in x_units.items():
            depth = nodes[node_id]['depth']
            x = 40 + (logical_w - 80) * (xu / denom if denom else 0.5)
            y = 32 + (logical_h - 64) * (depth / max_depth)
            positions[node_id] = (x, y)
        return positions

    def _choose_tree_visible_ids(self, nodes, children, active, current_node, best_solution_node):
        # During animation, focus on the active DFS branch and its local siblings.
        # At the end, zoom out to the whole recorded tree.
        final_view = bool(getattr(self, 'visual_trace_finished', False))
        if final_view or len(nodes) <= 120:
            return set(range(len(nodes)))
        visible_ids = {0} | set(active)
        cur = current_node
        while cur is not None and 0 <= cur < len(nodes):
            visible_ids.add(cur)
            parent = nodes[cur].get('parent')
            if parent is not None:
                visible_ids.add(parent)
                siblings = children.get(parent, [])
                if cur in siblings:
                    pos = siblings.index(cur)
                    visible_ids.update(siblings[max(0, pos - 3):pos + 4])
            cur = nodes[cur].get('parent')
        # Keep recently generated branches visible near the current search front.
        visible_ids.update(n['id'] for n in nodes[-35:])
        if best_solution_node is not None:
            cur = best_solution_node
            while cur is not None:
                visible_ids.add(cur)
                cur = nodes[cur].get('parent')
        return {i for i in visible_ids if 0 <= i < len(nodes)}

    def _fit_tree_view(self, positions, focus_ids, plot_w, plot_h, final_view=False):
        if not positions:
            return 1.0, 0.0, 0.0
        pts = [positions[i] for i in focus_ids if i in positions] or list(positions.values())
        min_x = min(x for x, _ in pts)
        max_x = max(x for x, _ in pts)
        min_y = min(y for _, y in pts)
        max_y = max(y for _, y in pts)
        bw = max(1.0, max_x - min_x)
        bh = max(1.0, max_y - min_y)
        pad = 260 if final_view else 72
        zoom = min((plot_w - 42) / (bw + pad), (plot_h - 42) / (bh + pad))
        # In final view, allow a much smaller scale so even very wide DFS trees
        # can fully fit inside the bottom viewport. Manual wheel zoom uses the
        # same low minimum, so the user can zoom out beyond the automatic fit.
        zoom = max(0.001 if final_view else 0.12, min(2.2 if not final_view else 1.0, zoom))
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        pan_x = -cx * zoom
        pan_y = -cy * zoom
        return zoom, pan_x, pan_y

    def _clip_line_to_rect(self, x1, y1, x2, y2, rx, ry, rw, rh):
        """Cohen-Sutherland clipping so DFS edges never bleed out of the viewport."""
        xmin, ymin, xmax, ymax = rx, ry, rx + rw, ry + rh
        INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8
        def code(x, y):
            c = INSIDE
            if x < xmin: c |= LEFT
            elif x > xmax: c |= RIGHT
            if y < ymin: c |= TOP
            elif y > ymax: c |= BOTTOM
            return c
        c1, c2 = code(x1, y1), code(x2, y2)
        while True:
            if not (c1 | c2):
                return x1, y1, x2, y2
            if c1 & c2:
                return None
            c = c1 or c2
            if c & TOP:
                x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1 or 1e-9); y = ymin
            elif c & BOTTOM:
                x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1 or 1e-9); y = ymax
            elif c & RIGHT:
                y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1 or 1e-9); x = xmax
            else:
                y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1 or 1e-9); x = xmin
            if c == c1:
                x1, y1 = x, y; c1 = code(x1, y1)
            else:
                x2, y2 = x, y; c2 = code(x2, y2)

    def _draw_dfs_tree(self, gx, gy, gw, gh, index: int):
        nodes, children, active, current_node, best_solution_node = self._build_dfs_tree(index)
        self.canvas.create_rectangle(gx, gy, gx + gw, gy + gh, fill='#f8fafc', outline='#e2e8f0')
        self.canvas.create_text(gx + 12, gy + 10, anchor='nw', text='DFS search tree', fill=INK, font=('Segoe UI', 11, 'bold'))
        self.canvas.create_text(gx + gw - 12, gy + 12, anchor='ne', text='wheel: zoom · drag: pan · final view fits all', fill=MUTED, font=('Segoe UI', 8))
        plot_x = gx + 12
        plot_y = gy + 40
        plot_w = gw - 24
        plot_h = gh - 92
        self.dfs_graph_region = (plot_x, plot_y, plot_w, plot_h)
        if plot_h < 150:
            return

        final_view = bool(getattr(self, 'visual_trace_finished', False))
        visible_ids = self._choose_tree_visible_ids(nodes, children, active, current_node, best_solution_node)
        positions = self._layout_tree_positions(nodes, children, visible_ids, 0, 0, max(620, plot_w), max(360, plot_h))

        focus_ids = set(range(len(nodes))) if final_view else ({0} | set(active) | {current_node})
        if not self.dfs_manual_view:
            self.dfs_zoom, self.dfs_pan_x, self.dfs_pan_y = self._fit_tree_view(positions, focus_ids, plot_w, plot_h, final_view=final_view)

        zoom = self.dfs_zoom
        cx = plot_x + plot_w / 2
        cy = plot_y + plot_h / 2

        def tr(pos):
            x, y = pos
            return (cx + self.dfs_pan_x + x * zoom, cy + self.dfs_pan_y + y * zoom)

        def inside(x, y, pad=0):
            return (plot_x + pad <= x <= plot_x + plot_w - pad and plot_y + pad <= y <= plot_y + plot_h - pad)

        self.canvas.create_rectangle(plot_x, plot_y, plot_x + plot_w, plot_y + plot_h, fill='#ffffff', outline='#e2e8f0')

        # Edges are clipped to the viewport: no overflow outside the graph card.
        for node_id in sorted(visible_ids):
            parent = nodes[node_id].get('parent')
            if parent in positions and node_id in positions:
                x1, y1 = tr(positions[parent])
                x2, y2 = tr(positions[node_id])
                clipped = self._clip_line_to_rect(x1, y1, x2, y2, plot_x, plot_y, plot_w, plot_h)
                if not clipped:
                    continue
                cx1, cy1, cx2, cy2 = clipped
                n = nodes[node_id]
                on_active_path = node_id in active and parent in active
                if n.get('pruned'):
                    color, width, dash = '#0ea5e9', 1.6, (3, 2)
                elif n.get('solution'):
                    color, width, dash = GOOD, 2.4, None
                elif n.get('closed'):
                    color, width, dash = '#f59e0b', 1.3, None
                elif on_active_path:
                    color, width, dash = '#7c3aed', 2.6, None
                else:
                    color, width, dash = '#cbd5e1', 1.0, None
                self.canvas.create_line(cx1, cy1, cx2, cy2, fill=color, width=width, dash=dash)

        # Nodes.
        for node_id in sorted(visible_ids):
            if node_id not in positions:
                continue
            n = nodes[node_id]
            x, y = tr(positions[node_id])
            radius_for_bounds = 10
            if not inside(x, y, pad=radius_for_bounds):
                continue
            if node_id == 0:
                fill, outline, r, shape = '#0f172a', '#0f172a', 7, 'circle'
            elif n.get('solution'):
                fill, outline, r, shape = GOOD, GOOD, 8, 'circle'
            elif n.get('pruned'):
                fill, outline, r, shape = '#e0f2fe', '#0ea5e9', 7, 'diamond'
            elif node_id == current_node:
                fill, outline, r, shape = '#7c3aed', '#7c3aed', 8, 'circle'
            elif node_id in active:
                fill, outline, r, shape = '#ede9fe', '#7c3aed', 7, 'circle'
            elif n.get('closed'):
                fill, outline, r, shape = '#f59e0b', '#d97706', 7, 'circle'
            else:
                fill, outline, r, shape = '#e2e8f0', '#64748b', 5, 'circle'
            if shape == 'diamond':
                self.canvas.create_polygon(x, y-r, x+r, y, x, y+r, x-r, y, fill=fill, outline=outline, width=2)
            else:
                self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill, outline=outline, width=2 if node_id in active or node_id == current_node else 1)
            if n.get('pruned'):
                # Pruned leaves are shown by shape/color only; text labels made dense trees unreadable.
                pass
            elif n.get('closed') and not n.get('solution') and node_id != current_node:
                self.canvas.create_text(x, y, text='↩', fill='white', font=('Segoe UI', 8, 'bold'))
            if node_id == current_node or node_id == best_solution_node or node_id == 0:
                label = 'root' if node_id == 0 else n['label']
                tx, ty = x, y + r + 5
                if inside(tx, ty, pad=16):
                    self.canvas.create_text(tx, ty, anchor='n', text=label[:12], fill=INK, font=('Segoe UI', 7, 'bold'))

        # Re-draw viewport border last for a clean clipped look.
        self.canvas.create_rectangle(plot_x, plot_y, plot_x + plot_w, plot_y + plot_h, fill='', outline='#cbd5e1')

        # Compact legend stays under the graph.  Detailed counters are already
        # shown in the right Visual Solve panel, so the bottom area remains clean.
        legend_y = gy + gh - 27
        legend_items = [
            ('current', '#7c3aed', 'circle'),
            ('solution', GOOD, 'circle'),
            ('backtracked', '#f59e0b', 'circle'),
            ('pruned', '#0ea5e9', 'diamond'),
        ]
        lx = gx + 12
        for label, color, shape in legend_items:
            if shape == 'diamond':
                self.canvas.create_polygon(lx + 6, legend_y, lx + 12, legend_y + 6, lx + 6, legend_y + 12, lx, legend_y + 6, fill='#e0f2fe', outline=color, width=2)
            else:
                self.canvas.create_oval(lx, legend_y, lx + 12, legend_y + 12, fill=color, outline=color)
            self.canvas.create_text(lx + 18, legend_y + 6, anchor='w', text=label, fill=MUTED, font=('Segoe UI', 8))
            lx += 118

    def _draw_trace_panel(self, event, index: int, total: int):
        """Draw a compact visual-solve summary on the right and a wide DFS tree
        below the floor plan.  The wide bottom area matches how DFS is usually
        taught: root at the top, branches spreading horizontally, and the active
        path highlighted while the plan above changes step by step.
        """
        p = self.problem
        m, top, s = self.margin_x, self.margin_y, self.scale
        plan_w = p.width * s
        plan_h = p.height * s
        canvas_w = max(900, self.canvas.winfo_width())
        canvas_h = max(650, self.canvas.winfo_height())

        # Right card keeps the same role as normal solve: short, readable status.
        x = m + plan_w + 18
        y0 = top
        card_w = max(260, min(330, canvas_w - x - 18))
        card_h = plan_h
        self.canvas.create_rectangle(x, y0, x + card_w, y0 + card_h, fill='white', outline=PANEL_LINE, width=1)
        y = y0 + 14
        self.canvas.create_text(x + 16, y, anchor='nw', text='Visual solve', fill=INK, font=('Segoe UI', 13, 'bold'))
        self.canvas.create_text(x + card_w - 16, y + 2, anchor='ne', text=f'{index + 1}/{total}', fill=MUTED, font=('Segoe UI', 9, 'bold'))
        y += 28
        event_type = str(event.get('type', 'event')).upper()
        color = {'ASSIGN': '#7c3aed', 'SOLUTION': GOOD, 'BACKTRACK': WARN, 'PRUNE': '#0ea5e9', 'SELECT': ACCENT, 'UNASSIGN': '#64748b'}.get(event_type, INK)
        self.canvas.create_text(x + 16, y, anchor='nw', text=event_type, fill=color, font=('Segoe UI', 17, 'bold'))
        y += 34
        var = event.get('variable') or '—'
        self.canvas.create_text(x + 16, y, anchor='nw', text=f'Variable: {var}', fill=MUTED, font=('Segoe UI', 9))
        y += 18
        self.canvas.create_text(x + 16, y, anchor='nw', text=f'Assigned rooms: {len(event.get("assignment") or {})} / {len(p.variables)}', fill=MUTED, font=('Segoe UI', 9))
        y += 28

        metrics = [
            ('Nodes', event.get('nodes', 0)),
            ('Backtracks', event.get('backtracks', 0)),
            ('Solutions', event.get('solutions_seen', 0)),
            ('Pruned', event.get('pruned_values', 0)),
        ]
        metric_w = (card_w - 42) / 2
        for i, (label, val) in enumerate(metrics):
            col = i % 2
            row = i // 2
            cxm = x + 16 + col * (metric_w + 10)
            cy = y + row * 42
            self.canvas.create_rectangle(cxm, cy, cxm + metric_w, cy + 34, fill='#f8fafc', outline='#e2e8f0')
            self.canvas.create_text(cxm + 7, cy + 5, anchor='nw', text=label, fill=MUTED, font=('Segoe UI', 7, 'bold'))
            self.canvas.create_text(cxm + 7, cy + 18, anchor='nw', text=str(val), fill=INK, font=('Segoe UI', 10, 'bold'))
        y += 94

        # Useful compact state instead of repeating the graph legend.
        self.canvas.create_line(x + 16, y, x + card_w - 16, y, fill='#e2e8f0')
        y += 12
        progress = (index + 1) / max(1, total)
        active_assignment = event.get('assignment') or {}
        state_lines = [
            f"Progress: {progress:.0%}",
            f"Recorded events: {index + 1} / {total}",
            f"Current depth: {len(active_assignment)}",
        ]
        if event.get('type') == 'prune':
            state_lines.append(f"Last prune: {event.get('count', 0)} values")
        elif event.get('type') == 'backtrack':
            state_lines.append('Last action: closing a branch')
        elif event.get('type') == 'solution':
            state_lines.append('Last action: valid solution found')
        for line in state_lines:
            self.canvas.create_text(x + 16, y, anchor='nw', text=line, fill=MUTED, font=('Segoe UI', 8))
            y += 18

        py = y0 + card_h - 18
        self.canvas.create_rectangle(x + 16, py, x + card_w - 16, py + 8, fill='#e2e8f0', outline='')
        self.canvas.create_rectangle(x + 16, py, x + 16 + (card_w - 32) * progress, py + 8, fill='#7c3aed', outline='')

        # Use the otherwise empty bottom space for a wide DFS tree.
        graph_x = m
        graph_y = top + plan_h + 18
        graph_w = max(360, canvas_w - graph_x - 20)
        graph_h = max(210, canvas_h - graph_y - 22)
        self._draw_dfs_tree(graph_x, graph_y, graph_w, graph_h, index)

    def run_public_grade(self):
        try:
            from planforge.grader.public_grader import grade_current_project, format_report
            report = grade_current_project()
            self._set_status('PUBLIC GRADE', format_report(report), 'neutral')
        except Exception as e:
            messagebox.showerror('Public grader error', str(e))

    def clear_canvas(self, draw_shell: bool = False):
        self.canvas.delete('all')
        if draw_shell and self.problem:
            self._draw_shell()

    def _canvas_geometry(self):
        p = self.problem
        cw = max(1000, self.canvas.winfo_width())
        ch = max(700, self.canvas.winfo_height())
        gap = 16
        left = 22
        top = 26
        right_pad = 14
        bottom_pad = 14

        # Normal solve: plan + right result card use almost all height.
        # Visual solve: reserve the lower third as a wide DFS-tree viewport.
        if getattr(self, 'visual_mode_active', False):
            panel_w = 300
            graph_h = max(245, min(360, int(ch * 0.34)))
            avail_h = max(260, ch - top - graph_h - 30 - bottom_pad)
        else:
            panel_w = 300
            graph_h = 0
            avail_h = max(360, ch - top - bottom_pad)

        avail_w = max(360, cw - left - panel_w - gap - right_pad)
        s = max(28, min(104, int(min(avail_w / p.width, avail_h / p.height))))
        self.scale = s
        self.margin_x = left
        self.margin_y = top
        self.visual_graph_height = graph_h
        return left, top, s, panel_w, gap

    def _draw_shell(self):
        p = self.problem
        m, top, s, panel_w, gap = self._canvas_geometry()
        plan_w = p.width * s
        plan_h = p.height * s
        w = max(self.canvas.winfo_width(), m + plan_w + gap + panel_w + 42)
        h = max(self.canvas.winfo_height(), top + plan_h + (getattr(self, 'visual_graph_height', 0) or 0) + 80)
        self.canvas.config(scrollregion=(0, 0, w, h))
        self.canvas.create_rectangle(0, 0, w, h, fill=CANVAS_BG, outline='')
        # Floor plan: no decorative outer card; only a clean drafting-board surface.
        self.canvas.create_rectangle(m, top, m+plan_w, top+plan_h, fill='#ffffff', outline=PANEL_LINE, width=1)
        for x in range(p.width + 1):
            self.canvas.create_line(m+x*s, top, m+x*s, top+plan_h, fill=GRID)
        for y in range(p.height + 1):
            self.canvas.create_line(m, top+y*s, m+plan_w, top+y*s, fill=GRID)
        self.canvas.create_rectangle(m, top, m+plan_w, top+plan_h, fill='', outline=WALL, width=4)
        self._draw_entrance(m, top, s)

    def _draw_entrance(self, m, top, s):
        p = self.problem
        ex, ey = p.entrance
        px = m + ex * s
        py = top + ey * s
        self.canvas.create_oval(px-6, py-6, px+6, py+6, fill=ACCENT, outline='white', width=2)
        self.canvas.create_text(px + 16, py - 12, anchor='w', text='Entrance', fill=ACCENT, font=('Segoe UI', 10, 'bold'))

    def _room_color(self, name: str) -> str:
        key = name.lower()
        for k, c in ROOM_COLORS.items():
            if k in key:
                return c
        return '#e2e8f0'

    def _icon(self, name: str) -> str:
        key = name.lower()
        for k, i in ICONS.items():
            if k in key:
                return i
        return '□'

    def draw_assignment(self, assignment):
        self.clear_canvas(draw_shell=True)
        p = self.problem
        m, top, s = self.margin_x, self.margin_y, self.scale
        occupied = [[False for _ in range(p.width)] for __ in range(p.height)]
        for r in assignment.values():
            for yy in range(r.y, r.y2):
                for xx in range(r.x, r.x2):
                    if 0 <= xx < p.width and 0 <= yy < p.height:
                        occupied[yy][xx] = True
        for yy in range(p.height):
            for xx in range(p.width):
                if not occupied[yy][xx]:
                    x1, y1 = m + xx*s, top + yy*s
                    self.canvas.create_rectangle(x1, y1, x1+s, y1+s, fill=UNUSED, outline='#fecaca')
                    self.canvas.create_line(x1+8, y1+8, x1+s-8, y1+s-8, fill='#fca5a5')
                    self.canvas.create_line(x1+s-8, y1+8, x1+8, y1+s-8, fill='#fca5a5')
        for name in p.variables:
            if name not in assignment:
                continue
            r = assignment[name]
            color = self._room_color(name)
            x1, y1 = m + r.x*s, top + r.y*s
            x2, y2 = m + r.x2*s, top + r.y2*s
            rw, rh = x2 - x1, y2 - y1
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=WALL, width=3)
            if rw >= 46 and rh >= 42:
                self.canvas.create_text(x1+10, y1+8, anchor='nw', text=self._icon(name), fill=INK, font=('Segoe UI Symbol', 17, 'bold'))
            # Small rooms get a compact label so names no longer collide with borders.
            if rw < 70 or rh < 52 or r.area <= 3:
                label_font = ('Segoe UI', 8, 'bold')
                area_font = ('Segoe UI', 7)
                label_text = name if len(name) <= 8 else name[:7] + '…'
                self.canvas.create_text((x1+x2)/2, (y1+y2)/2 - 5, text=label_text, fill=INK, font=label_font, width=max(34, rw-8))
                self.canvas.create_text((x1+x2)/2, (y1+y2)/2 + 10, text=f'{r.area} m²', fill=MUTED, font=area_font)
            else:
                font_size = 12 if r.area < 10 else 13
                self.canvas.create_text((x1+x2)/2, (y1+y2)/2 - 8, text=name, fill=INK, font=('Segoe UI', font_size, 'bold'), width=max(60, rw-12))
                self.canvas.create_text((x1+x2)/2, (y1+y2)/2 + 15, text=f'{r.w}×{r.h} • {r.area} m²', fill=MUTED, font=('Segoe UI', 9))
            self._draw_windows(name, r, m, top, s)
        self._draw_doors(assignment, m, top, s)
        self._draw_entrance(m, top, s)
        self._draw_score_panel(assignment, m, top, s)

    def _draw_windows(self, name, r, m, top, s):
        if not touches_boundary(r, self.problem.width, self.problem.height):
            return
        key = name.lower()
        if not any(tag in key for tag in ['living', 'bedroom', 'kitchen', 'balcony', 'office', 'study']):
            return
        seg = max(20, int(s * 0.48))
        xmid = m + (r.x + r.w / 2) * s
        ymid = top + (r.y + r.h / 2) * s
        if r.y == 0:
            self.canvas.create_line(xmid-seg/2, top+1, xmid+seg/2, top+1, fill=WINDOW, width=6)
        if r.y2 == self.problem.height:
            y = top + r.y2*s - 1
            self.canvas.create_line(xmid-seg/2, y, xmid+seg/2, y, fill=WINDOW, width=6)
        if r.x == 0:
            self.canvas.create_line(m+1, ymid-seg/2, m+1, ymid+seg/2, fill=WINDOW, width=6)
        if r.x2 == self.problem.width:
            x = m + r.x2*s - 1
            self.canvas.create_line(x, ymid-seg/2, x, ymid+seg/2, fill=WINDOW, width=6)

    def _draw_doors(self, assignment, m, top, s):
        graph = adjacency_graph(assignment)
        drawn = set()
        for a, neighbors in graph.items():
            for b in neighbors:
                key = tuple(sorted((a, b)))
                if key in drawn:
                    continue
                drawn.add(key)
                ra, rb = assignment[a], assignment[b]
                if shared_wall_length(ra, rb) <= 0:
                    continue
                if ra.x2 == rb.x or rb.x2 == ra.x:
                    x = m + (ra.x2 if ra.x2 == rb.x else rb.x2) * s
                    y1 = top + max(ra.y, rb.y) * s
                    y2 = top + min(ra.y2, rb.y2) * s
                    cy = (y1+y2)/2
                    self.canvas.create_line(x, cy-15, x, cy+15, fill='white', width=8)
                    self.canvas.create_line(x, cy-15, x, cy+15, fill=DOOR, width=3)
                elif ra.y2 == rb.y or rb.y2 == ra.y:
                    y = top + (ra.y2 if ra.y2 == rb.y else rb.y2) * s
                    x1 = m + max(ra.x, rb.x) * s
                    x2 = m + min(ra.x2, rb.x2) * s
                    cx = (x1+x2)/2
                    self.canvas.create_line(cx-15, y, cx+15, y, fill='white', width=8)
                    self.canvas.create_line(cx-15, y, cx+15, y, fill=DOOR, width=3)

    def _draw_score_panel(self, assignment, m, top, s):
        p = self.problem
        score, qnotes = layout_quality_score(p, assignment)
        used = used_area(list(assignment.values()))
        total = p.width * p.height
        coverage = used / total if total else 0
        plan_w = p.width * s
        plan_h = p.height * s
        x = m + plan_w + 26
        y0 = top
        card_w = 292
        card_h = max(360, plan_h)

        # Clean, fixed-height side panel. It uses the same height as the plan so
        # text never falls outside the box and the panel feels visually attached
        # to the canvas.
        self.canvas.create_rectangle(x, y0, x + card_w, y0 + card_h, fill='white', outline=PANEL_LINE, width=1)

        y = y0 + 18
        self.canvas.create_text(x + 18, y, anchor='nw', text='Result summary', fill=INK, font=('Segoe UI', 15, 'bold'))
        y += 48

        color = GOOD if score >= 80 else WARN if score >= 60 else BAD
        self.canvas.create_text(x + 18, y, anchor='nw', text=f'{score:.1f}', fill=color, font=('Segoe UI', 31, 'bold'))
        self.canvas.create_text(x + 102, y + 14, anchor='nw', text='/ 100', fill=MUTED, font=('Segoe UI', 13, 'bold'))
        y += 62

        # Two compact status chips.
        self.canvas.create_rectangle(x + 18, y, x + 136, y + 31, fill='#f1f5f9', outline='#e2e8f0')
        self.canvas.create_text(x + 30, y + 8, anchor='nw', text=f'Coverage {coverage:.0%}', fill=INK, font=('Segoe UI', 9, 'bold'))
        self.canvas.create_rectangle(x + 150, y, x + 274, y + 31, fill='#dcfce7', outline='#bbf7d0')
        self.canvas.create_text(x + 176, y + 8, anchor='nw', text='VALID', fill=GOOD, font=('Segoe UI', 9, 'bold'))
        y += 56

        self.canvas.create_text(x + 18, y, anchor='nw', text='Quality notes', fill=INK, font=('Segoe UI', 11, 'bold'))
        y += 26

        # Reserve the bottom of the card for the legend. Notes are clipped by
        # count/line length instead of overlapping the legend.
        legend_reserved = 92
        notes_bottom = y0 + card_h - legend_reserved
        for line in (qnotes[:4] if qnotes else []):
            wrapped = textwrap.wrap(line, width=34)[:2] or ['']
            needed = 18 * len(wrapped) + 10
            if y + needed > notes_bottom:
                break
            for i, part in enumerate(wrapped):
                prefix = '• ' if i == 0 else '  '
                self.canvas.create_text(x + 18, y, anchor='nw', text=prefix + part, fill=MUTED, font=('Segoe UI', 9), width=card_w - 36)
                y += 18
            y += 8

        # Bottom-aligned legend. This prevents the previous overlap with notes.
        ly = y0 + card_h - 78
        self.canvas.create_line(x + 18, ly - 12, x + card_w - 18, ly - 12, fill='#e2e8f0')
        self.canvas.create_text(x + 18, ly, anchor='nw', text='Visual cues', fill=INK, font=('Segoe UI', 10, 'bold'))
        ly += 22
        for cue in ['blue = exterior window', 'brown = door opening', 'red hatch = unused cell']:
            self.canvas.create_text(x + 18, ly, anchor='nw', text='• ' + cue, fill=MUTED, font=('Segoe UI', 8), width=card_w - 36)
            ly += 16
