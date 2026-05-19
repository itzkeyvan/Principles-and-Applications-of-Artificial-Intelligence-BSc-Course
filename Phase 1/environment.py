"""
Graph-Based Search Environment for Fundamentals of AI Course
University of Isfahan - Spring 2025

All Designed By:
    - Mahdi (Semi) Semsarzadeh

This environment implements a graph-based search problem over a real-world-inspired
traffic network. An agent must find an optimal path between a selected start and goal
node while considering varying traffic conditions and directional constraints on edges.
The project is designed to help students understand, implement, and visualize classical
search algorithms such as Breadth-First Search (BFS), Depth-First Search (DFS),
Bidirectional Search (BDS), and A* Search.

Key Components:
- Map: Main visualization engine built with Tkinter for interactive graph exploration
- Search Facade: Restricted interface exposing only essential methods required by search algorithms
- Graph Representation: Nodes and directed edges loaded from external JSON files
- Search Algorithms: Modular implementations that interact with the environment via a generator-based event system

Environment Features:
- Realistic map-based visualization with zooming and panning support
- Directed and weighted edges influenced by dynamic traffic levels (low, medium, high)
- Interactive node selection for start and goal states
- Step-by-step animation of search process (frontier expansion, node exploration, path discovery)
- Visual differentiation of node states (unseen, frontier, expanded, final path)
- Runtime statistics including expanded nodes count, execution time, and path cost
- Edge inspection tool displaying traffic level, direction, and geometric length

Usage:
    from environment import Map
    from main import bfs

    map = Map(search_algorithm=bfs)
    map.start()

Note: This code is developed for educational purposes in the Fundamentals of AI course
and is intended to provide an intuitive and visual understanding of search algorithms.
"""

import json
import math
import os
import random
import time

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk


IMAGE_PATH = "map.png"
EDGES_PATH = "edges.json"
NODES_PATH = "nodes.json"

RANDOM_SEED = 42
MAX_SCALE = 2

APP_BG = "#eef2f7"
SIDEBAR_BG = "#f8fafc"
CARD_BG = "#ffffff"
TEXT_DARK = "#1f2937"
TEXT_MUTED = "#6b7280"

TRAFFIC_COLORS = {
    1: "#00b300",
    2: "#ffd000",
    3: "#e53935",
}


class _SearchFacade:
    """Only the 5 allowed methods are exposed to the student's file."""

    def __init__(self, viewer):
        self._viewer = viewer

    def get_successors(self, node):
        return self._viewer.get_successors(node)
    
    def get_predecessors(self, node):
        return self._viewer.get_predecessors(node)

    def is_goal_state(self, node):
        return self._viewer.is_goal_state(node)

    def get_goal_state(self):
        return self._viewer.get_goal_state()

    def get_start_state(self):
        return self._viewer.get_start_state()


class Map:
    NODE_MARKER_STYLES = {
        "unseen": {"fill": "", "outline": "", "width": 0, "state": "hidden"},
        "frontier": {"fill": "#dbeafe", "outline": "#60a5fa", "width": 2, "state": "normal"},
        "expanded": {"fill": "#f9a8d4", "outline": "#f472b6", "width": 2, "state": "normal"},
        "path": {"fill": "#ddd6fe", "outline": "#8b5cf6", "width": 2, "state": "normal"},
        "start": {"fill": "blue", "outline": "blue", "width": 4, "state": "normal"},
        "goal": {"fill": "red", "outline": "red", "width": 4, "state": "normal"},
    }

    NODE_PRIORITY = {
        "unseen": 0,
        "frontier": 1,
        "expanded": 2,
        "path": 3,
        "start": 5,
        "goal": 5,
    }

    def __init__(
        self,
        search_algorithm,
        seed=RANDOM_SEED,
        delay=25
    ):
        self.search_algorithm = search_algorithm
        self.seed = seed
        self.delay = delay
        self.image_path = IMAGE_PATH
        self.edges_path = EDGES_PATH
        self.nodes_path = NODES_PATH

        self.root = tk.Tk()
        self.root.title("Navigator")
        self.root.geometry("1330x720")
        self.root.resizable(False, False)
        self.root.configure(bg=APP_BG)

        self._setup_styles()

        self.rng = random.Random(self.seed)
        self.original_img = Image.open(self.image_path)

        self.scale = 1.0
        self.min_scale = 1.0
        self.max_scale = MAX_SCALE
        self.offset_x = 0
        self.offset_y = 0

        self.preview_cache = {}
        self.final_cache = {}
        self.bg_refine_job = None

        self.edge_weights = {}
        self.nodes = []
        self.edges = []
        self.adjacency = {}
        self.reverse_adjacency = {}
        self.drawn_edges_data = {}
        self.node_item_by_node = {}
        self.search_marker_by_node = {}

        self.selected_start = None
        self.selected_goal = None
        self.node_states = {}
        self.path_nodes = []
        self.search_running = False
        self.stop_requested = False
        self.search_job = None
        self.search_gen = None
        self.expanded_count = 0
        self.search_start_time = 0.0
        self.search_path_cost = 0.0

        self.start_var = tk.StringVar(value="Start: -")
        self.goal_var = tk.StringVar(value="Goal: -")
        self.status_var = tk.StringVar(value="Status: Ready")
        self.cost_var = tk.StringVar(value="Path Cost: -")
        self.expanded_var = tk.StringVar(value="Expanded Nodes: 0")
        self.runtime_var = tk.StringVar(value="Runtime: 0.00 s")

        self.sidebar = tk.Frame(self.root, width=250, bg=SIDEBAR_BG, padx=14, pady=14)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.canvas = tk.Canvas(
            self.root,
            bg=APP_BG,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.is_panning = False
        self.last_pan_x = 0
        self.last_pan_y = 0

        self.tk_img = None
        self.map_img_id = None

        self.epicenters = [
            (self.rng.randint(0, 1080), self.rng.randint(0, 720))
            for _ in range(7)
        ]

        self.setup_sidebar_ui()
        self.load_graph_data()
        self.build_adjacency()
        self.draw_base_scene()

        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_pan_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_pan_end)

        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)

        self.canvas.tag_bind("edge", "<Button-1>", self.on_edge_click)

        self.refresh_control_states()

    # --------------------------------------------
    # Public start
    # --------------------------------------------
    def start(self):
        self.root.mainloop()

    # --------------------------------------------
    # Styling
    # --------------------------------------------
    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception as e:
            print(e)

        style.configure(
            "Graph.TCombobox",
            padding=4,
            relief="flat",
            fieldbackground="white",
            background="white",
            foreground=TEXT_DARK,
            arrowcolor=TEXT_DARK,
        )
        style.map(
            "Graph.TCombobox",
            fieldbackground=[("readonly", "white")],
            selectbackground=[("readonly", "white")],
            selectforeground=[("readonly", TEXT_DARK)],
            background=[("readonly", "white")],
            foreground=[("readonly", TEXT_DARK)],
        )

    def make_card(self, parent, title, bg=CARD_BG):
        return tk.LabelFrame(
            parent,
            text=title,
            bg=bg,
            fg=TEXT_DARK,
            font=("Arial", 10, "bold"),
            padx=10,
            pady=9,
            bd=1,
            relief="solid",
            labelanchor="n",
        )

    def make_soft_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#e8edf5",
            fg=TEXT_DARK,
            activebackground="#dbe3ee",
            activeforeground=TEXT_DARK,
            relief="flat",
            bd=0,
            padx=10,
            pady=7,
            highlightthickness=0,
            takefocus=0,
            cursor="hand2",
            font=("Arial", 9, "bold"),
        )

    # --------------------------------------------
    # UI
    # --------------------------------------------
    def setup_sidebar_ui(self):
        footer = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 10))

        separator = tk.Frame(footer, bg=TEXT_MUTED, height=1)
        separator.pack(fill=tk.X, padx=20, pady=(0, 10))

        tk.Label(
            footer,
            text="M. Semi",
            bg=SIDEBAR_BG,
            fg=TEXT_DARK,
            font=("sans-serif", 11, "bold"),
            anchor=tk.CENTER,
        ).pack(fill=tk.X)

        tk.Label(
            footer,
            text="All Designed By",
            bg=SIDEBAR_BG,
            fg=TEXT_MUTED,
            font=("sans-serif", 9),
            anchor=tk.CENTER,
        ).pack(fill=tk.X, pady=(2, 0))

        node_frame = self.make_card(self.sidebar, "Node Display")
        node_frame.pack(fill=tk.X, pady=(0, 10))

        self.node_combo = ttk.Combobox(
            node_frame,
            state="readonly",
            style="Graph.TCombobox",
            values=("Full", "Border", "Hidden"),
            takefocus=0,
        )
        self.node_combo.current(0)
        self.node_combo.pack(fill=tk.X)
        self.node_combo.bind("<<ComboboxSelected>>", self.on_combobox_selected)

        edge_frame = self.make_card(self.sidebar, "Traffic Edge Filter")
        edge_frame.pack(fill=tk.X, pady=(0, 10))

        self.edge_combo = ttk.Combobox(
            edge_frame,
            state="readonly",
            style="Graph.TCombobox",
            values=("Show All", "Green", "Yellow", "Red", "Hide All"),
            takefocus=0,
        )
        self.edge_combo.current(0)
        self.edge_combo.pack(fill=tk.X)
        self.edge_combo.bind("<<ComboboxSelected>>", self.on_combobox_selected)

        action_frame = self.make_card(self.sidebar, "Search Control")
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_button = self.make_soft_button(action_frame, "Start", self.start_search)
        self.start_button.pack(fill=tk.X, pady=(0, 6))

        self.reset_button = self.make_soft_button(action_frame, "Reset", self.reset_environment)
        self.reset_button.pack(fill=tk.X, pady=(0, 6))

        self.stop_button = self.make_soft_button(action_frame, "Stop", self.stop_search)
        self.stop_button.pack(fill=tk.X)

        edge_info = self.make_card(self.sidebar, "Edge Information", bg="#eff6ff")
        edge_info.pack(fill=tk.X, pady=(0, 10))

        self.info_traffic = tk.StringVar(value="Traffic Level: -")
        self.info_type = tk.StringVar(value="Direction: -")
        self.info_length = tk.StringVar(value="Length: -")

        tk.Label(edge_info, textvariable=self.info_traffic, bg="#eff6ff", fg=TEXT_DARK, anchor=tk.W, font=("Arial", 9, "bold")).pack(fill=tk.X, pady=(0, 4))
        tk.Label(edge_info, textvariable=self.info_type, bg="#eff6ff", fg=TEXT_DARK, anchor=tk.W).pack(fill=tk.X, pady=2)
        tk.Label(edge_info, textvariable=self.info_length, bg="#eff6ff", fg=TEXT_DARK, anchor=tk.W).pack(fill=tk.X, pady=2)

        search_info = self.make_card(self.sidebar, "Search Stats", bg="#f0fdf4")
        search_info.pack(fill=tk.X, pady=(0, 10))

        tk.Label(search_info, textvariable=self.status_var, bg="#f0fdf4", fg=TEXT_DARK, anchor=tk.W, wraplength=200).pack(fill=tk.X, pady=2)
        tk.Label(search_info, textvariable=self.cost_var, bg="#f0fdf4", fg=TEXT_DARK, anchor=tk.W).pack(fill=tk.X, pady=2)
        tk.Label(search_info, textvariable=self.expanded_var, bg="#f0fdf4", fg=TEXT_DARK, anchor=tk.W).pack(fill=tk.X, pady=2)
        tk.Label(search_info, textvariable=self.runtime_var, bg="#f0fdf4", fg=TEXT_DARK, anchor=tk.W).pack(fill=tk.X, pady=2)

    def on_combobox_selected(self, event):
        self.update_graphics(event)
        widget = event.widget
        self.root.after_idle(lambda w=widget: self.clear_combobox_selection(w))

    def clear_combobox_selection(self, widget):
        try:
            widget.selection_clear()
        except Exception as e:
            print(e)
        try:
            widget.icursor(tk.END)
        except Exception as e:
            print(e)

    # --------------------------------------------
    # Graph data
    # --------------------------------------------
    def load_graph_data(self):
        self.edges = []
        self.nodes = []

        if os.path.exists(self.edges_path):
            with open(self.edges_path, "r") as f:
                edges_list = json.load(f)

            self.edges = [(tuple(p1), tuple(p2)) for p1, p2 in edges_list]
            self.edges.sort()

            for p1, p2 in self.edges:
                key = tuple(sorted((p1, p2)))
                if key not in self.edge_weights:
                    self.edge_weights[key] = self.generate_traffic_level(p1, p2)

        if os.path.exists(self.nodes_path):
            with open(self.nodes_path, "r") as f:
                self.nodes = [tuple(node) for node in json.load(f)]

    def build_adjacency(self):
        self.adjacency = {node: [] for node in self.nodes}
        for u, v in self.edges:
            self.adjacency.setdefault(u, []).append(v)
            self.adjacency.setdefault(v, [])

            self.reverse_adjacency.setdefault(v, []).append(u)
            self.reverse_adjacency.setdefault(u, [])

    def generate_traffic_level(self, p1, p2):
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2
        min_dist = min(math.hypot(mid_x - ex, mid_y - ey) for ex, ey in self.epicenters)
        dist = min_dist + self.rng.random() * 50

        if dist < 100:
            return 3
        if dist < 175:
            return 2
        return 1

    # --------------------------------------------
    # Required 5 methods for interaction
    # --------------------------------------------
    def get_successors(self, node):
        successors = []
        for neighbor in self.adjacency.get(node, []):
            key = tuple(sorted((node, neighbor)))
            traffic = self.edge_weights.get(key, 1)
            length = math.hypot(neighbor[0] - node[0], neighbor[1] - node[1])
            successors.append((neighbor, length * traffic))
        return successors
    
    def get_predecessors(self, node):
        predecessors = []
        for neighbor in self.reverse_adjacency.get(node, []):
            key = tuple(sorted((node, neighbor)))
            traffic = self.edge_weights.get(key, 1)
            length = math.hypot(neighbor[0] - node[0], neighbor[1] - node[1])
            predecessors.append((neighbor, length * traffic))
        return predecessors

    def is_goal_state(self, node):
        return node == self.selected_goal

    def get_goal_state(self):
        return self.selected_goal

    def get_start_state(self):
        return self.selected_start

    def _get_search_algorithm_label(self):
        if self.search_algorithm is None:
            return "Search"
        name = getattr(self.search_algorithm, "__name__", "search")
        return name.replace("_", " ").upper()

    def _calculate_path_cost(self, path):
        total = 0.0
        if not path or len(path) < 2:
            return total

        for u, v in zip(path, path[1:]):
            key = tuple(sorted((u, v)))
            traffic = self.edge_weights.get(key, 1)
            length = math.hypot(v[0] - u[0], v[1] - u[1])
            total += length * traffic

        return total

    def _set_final_runtime(self):
        elapsed = time.perf_counter() - self.search_start_time
        self.runtime_var.set(f"Runtime: {elapsed:.2f} s")

    # --------------------------------------------
    # Coordinates
    # --------------------------------------------
    def world_to_canvas(self, x, y):
        return x * self.scale + self.offset_x, y * self.scale + self.offset_y

    def canvas_to_world(self, x, y):
        return (x - self.offset_x) / self.scale, (y - self.offset_y) / self.scale

    # --------------------------------------------
    # Bounds
    # --------------------------------------------
    def get_canvas_size(self):
        self.root.update_idletasks()
        return self.canvas.winfo_width(), self.canvas.winfo_height()

    def get_scaled_image_size(self):
        return (
            max(1, int(self.original_img.width * self.scale)),
            max(1, int(self.original_img.height * self.scale)),
        )

    def get_allowed_top_left(self):
        canvas_w, canvas_h = self.get_canvas_size()
        img_w, img_h = self.get_scaled_image_size()

        if img_w >= canvas_w:
            min_x, max_x = canvas_w - img_w, 0
        else:
            min_x = max_x = (canvas_w - img_w) / 2

        if img_h >= canvas_h:
            min_y, max_y = canvas_h - img_h, 0
        else:
            min_y = max_y = (canvas_h - img_h) / 2

        return min_x, max_x, min_y, max_y

    def clamp_offset(self, x, y):
        min_x, max_x, min_y, max_y = self.get_allowed_top_left()
        x = min(max(x, min_x), max_x) if min_x != max_x else min_x
        y = min(max(y, min_y), max_y) if min_y != max_y else min_y
        return x, y

    def keep_world_inside_bounds(self):
        target_x, target_y = self.clamp_offset(self.offset_x, self.offset_y)
        dx = target_x - self.offset_x
        dy = target_y - self.offset_y

        if dx or dy:
            self.canvas.move("world", dx, dy)
            self.offset_x = target_x
            self.offset_y = target_y

    def move_world_by(self, dx, dy):
        target_x = self.offset_x + dx
        target_y = self.offset_y + dy
        clamped_x, clamped_y = self.clamp_offset(target_x, target_y)
        actual_dx = clamped_x - self.offset_x
        actual_dy = clamped_y - self.offset_y

        if actual_dx or actual_dy:
            self.canvas.move("world", actual_dx, actual_dy)
            self.offset_x = clamped_x
            self.offset_y = clamped_y

    # --------------------------------------------
    # Background
    # --------------------------------------------
    def _render_background(self, quality="final"):
        key = round(self.scale, 4)
        cache = self.preview_cache if quality == "preview" else self.final_cache

        if key in cache:
            return cache[key]

        new_w = max(1, int(self.original_img.width * self.scale))
        new_h = max(1, int(self.original_img.height * self.scale))
        resample = Image.Resampling.NEAREST if quality == "preview" else Image.Resampling.LANCZOS
        resized = self.original_img.resize((new_w, new_h), resample)
        img = ImageTk.PhotoImage(resized)
        cache[key] = img
        return img

    def _map_item_exists(self):
        if self.map_img_id is None:
            return False
        try:
            return self.canvas.type(self.map_img_id) != ""
        except tk.TclError:
            return False

    def update_background_image(self, quality="final"):
        self.tk_img = self._render_background(quality=quality)

        if not self._map_item_exists():
            self.map_img_id = self.canvas.create_image(
                self.offset_x,
                self.offset_y,
                anchor=tk.NW,
                image=self.tk_img,
                tags=("world", "background", "graph_element"),
            )
        else:
            self.canvas.itemconfig(self.map_img_id, image=self.tk_img)
            self.canvas.coords(self.map_img_id, self.offset_x, self.offset_y)

    def schedule_background_refine(self):
        if self.bg_refine_job is not None:
            self.root.after_cancel(self.bg_refine_job)
        self.bg_refine_job = self.root.after(120, self._apply_background_refine)

    def _apply_background_refine(self):
        self.bg_refine_job = None
        self.update_background_image(quality="final")
        self.canvas.tag_raise("background")
        self.canvas.tag_raise("edge")
        self.canvas.tag_raise("search_marker")
        self.canvas.tag_raise("path_line")
        self.canvas.tag_raise("selection_label")
        self.canvas.tag_raise("node")

    # --------------------------------------------
    # Drawing
    # --------------------------------------------
    def sync_node_layers(self):
        for node in self.nodes:
            cx, cy = self.world_to_canvas(*node)

            node_id = self.node_item_by_node.get(node)
            if node_id is not None:
                r = max(2, int(4.5 * self.scale))
                self.canvas.coords(node_id, cx - r, cy - r, cx + r, cy + r)

            marker_id = self.search_marker_by_node.get(node)
            if marker_id is not None:
                mr = max(5, int(7.5 * self.scale))
                self.canvas.coords(marker_id, cx - mr, cy - mr, cx + mr, cy + mr)

    def draw_base_scene(self):
        self.canvas.delete("all")
        self.map_img_id = None
        self.drawn_edges_data.clear()
        self.node_item_by_node.clear()
        self.search_marker_by_node.clear()

        self.update_background_image(quality="final")

        for p1, p2 in self.edges:
            key = tuple(sorted((p1, p2)))
            lv = self.edge_weights[key]
            is_two_way = (p2, p1) in self.edges
            x1, y1 = self.world_to_canvas(*p1)
            x2, y2 = self.world_to_canvas(*p2)

            line_id = self.canvas.create_line(
                x1, y1, x2, y2,
                fill=TRAFFIC_COLORS[lv],
                width=max(1, int(3.5 * self.scale)),
                arrow=None if is_two_way else tk.LAST,
                arrowshape=(10, 12, 4),
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags=("world", f"edge_lv{lv}", "graph_element", "edge"),
            )

            self.drawn_edges_data[line_id] = {
                "p1": p1,
                "p2": p2,
                "traffic": lv,
                "two_way": is_two_way,
            }

        for node in self.nodes:
            cx, cy = self.world_to_canvas(*node)
            r = max(2, int(4.5 * self.scale))

            node_id = self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill="#475569",
                outline="white",
                width=max(1, int(1.8 * self.scale)),
                tags=("world", "node", "graph_element"),
            )
            self.node_item_by_node[node] = node_id

            mr = max(5, int(8 * self.scale))
            marker_id = self.canvas.create_oval(
                cx - mr, cy - mr, cx + mr, cy + mr,
                fill="",
                outline="",
                width=max(1, int(3 * self.scale)),
                state="hidden",
                tags=("world", "search_marker", "graph_element"),
            )
            self.search_marker_by_node[node] = marker_id

        self.redraw_path_line()
        self.redraw_selection_labels()
        self.apply_graphics_settings()
        self.apply_all_node_states()
        self.sync_node_layers()

        self.canvas.tag_raise("background")
        self.canvas.tag_raise("edge")
        self.canvas.tag_raise("search_marker")
        self.canvas.tag_raise("path_line")
        self.canvas.tag_raise("selection_label")
        self.canvas.tag_raise("node")

        self.keep_world_inside_bounds()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def redraw_path_line(self):
        self.canvas.delete("path_line")
        if len(self.path_nodes) < 2:
            return

        pts = []
        for node in self.path_nodes:
            pts.extend(self.world_to_canvas(*node))

        self.canvas.create_line(
            *pts,
            fill="#7c3aed",
            width=max(2, int(5.5 * self.scale)),
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
            smooth=True,
            tags=("world", "path_line", "graph_element"),
        )

    def redraw_selection_labels(self):
        self.canvas.delete("selection_label")

        for role, node in (("S", self.selected_start), ("G", self.selected_goal)):
            if node is None:
                continue

            x, y = self.world_to_canvas(*node)
            label_color = self.NODE_MARKER_STYLES["start"]["fill"] if role == "S" else self.NODE_MARKER_STYLES["goal"]["fill"]

            self.canvas.create_text(
                x,
                y - max(12, 14 * self.scale),
                text=role,
                fill=label_color,
                font=("Arial", max(8, int(10 * self.scale)), "bold"),
                tags=("world", "selection_label", "graph_element"),
            )

    # --------------------------------------------
    # Search visuals
    # --------------------------------------------
    def apply_all_node_states(self):
        for node in self.nodes:
            self.apply_node_state(node)

    def apply_node_state(self, node):
        marker_id = self.search_marker_by_node.get(node)
        if marker_id is None:
            return

        state = self.node_states.get(node, "unseen")
        style = self.NODE_MARKER_STYLES[state]

        if style["state"] == "hidden":
            self.canvas.itemconfigure(marker_id, state="hidden")
            return

        self.canvas.itemconfigure(
            marker_id,
            state="normal",
            fill=style["fill"],
            outline=style["outline"],
            width=max(1, int(style["width"] * self.scale)),
        )

    def set_node_state(self, node, state):
        current = self.node_states.get(node, "unseen")
        if self.NODE_PRIORITY.get(state, 0) < self.NODE_PRIORITY.get(current, 0):
            return
        self.node_states[node] = state
        self.apply_node_state(node)

    def clear_search_visuals(self, keep_selection=False):
        if self.search_job is not None:
            self.root.after_cancel(self.search_job)
            self.search_job = None

        self.search_running = False
        self.stop_requested = False
        self.canvas.delete("path_line")
        self.path_nodes = []

        if keep_selection:
            preserved = {}
            if self.selected_start is not None:
                preserved[self.selected_start] = "start"
            if self.selected_goal is not None:
                preserved[self.selected_goal] = "goal"
            self.node_states = preserved
        else:
            self.node_states = {}

        for node in self.nodes:
            self.apply_node_state(node)

        if not keep_selection:
            self.selected_start = None
            self.selected_goal = None
            self.canvas.delete("selection_label")
        else:
            self.redraw_selection_labels()

    def clear_visuals_only(self):
        preserved = {}
        if self.selected_start is not None:
            preserved[self.selected_start] = "start"
        if self.selected_goal is not None:
            preserved[self.selected_goal] = "goal"
        
        self.node_states = preserved

        for node in self.nodes:
            self.apply_node_state(node)

    # --------------------------------------------
    # Sidebar
    # --------------------------------------------
    def refresh_selection_text(self):
        def fmt(node):
            return f"({node[0]}, {node[1]})" if node else "-"

        self.start_var.set(f"Start: {fmt(self.selected_start)}")
        self.goal_var.set(f"Goal: {fmt(self.selected_goal)}")

    def refresh_control_states(self):
        ready = (
            not self.search_running
            and self.selected_start is not None
            and self.selected_goal is not None
            and self.selected_start != self.selected_goal
            and self.search_algorithm is not None
        )

        state = tk.NORMAL if ready else tk.DISABLED
        self.start_button.config(state=state)
        self.reset_button.config(state=(tk.DISABLED if self.search_running else tk.NORMAL))
        self.stop_button.config(state=(tk.NORMAL if self.search_running else tk.DISABLED))

    def refresh_stats(self):
        self.expanded_var.set(f"Expanded Nodes: {self.expanded_count}")
        if self.search_running:
            elapsed = time.perf_counter() - self.search_start_time
            self.runtime_var.set(f"Runtime: {elapsed:.2f} s")

    # --------------------------------------------
    # Node picking
    # --------------------------------------------
    def find_nearest_node(self, canvas_x, canvas_y):
        wx, wy = self.canvas_to_world(canvas_x, canvas_y)
        threshold = 16 / self.scale
        best_node = None
        best_dist = float("inf")

        for node in self.nodes:
            d = math.hypot(wx - node[0], wy - node[1])
            if d < threshold and d < best_dist:
                best_dist = d
                best_node = node

        return best_node

    def on_left_press(self, event):
        items = self.canvas.find_withtag("current")
        clicked_edge = False

        if items:
            item_id = items[0]
            tags = self.canvas.gettags(item_id)
            if "edge" in tags:
                clicked_edge = True

        if clicked_edge:
            return

        if not self.search_running:
            node = self.find_nearest_node(event.x, event.y)
            if node is not None:
                self.select_node(node)
                return

        self.is_panning = True
        self.last_pan_x = event.x
        self.last_pan_y = event.y

    def select_node(self, node):
        if self.selected_start is None:
            self.selected_start = node
            self.node_states[node] = "start"
        elif self.selected_goal is None and node != self.selected_start:
            self.selected_goal = node
            self.node_states[node] = "goal"
        else:
            return

        self.redraw_selection_labels()
        self.apply_node_state(node)
        self.refresh_selection_text()
        self.refresh_control_states()

    # --------------------------------------------
    # Edge inspection
    # --------------------------------------------
    def on_edge_click(self, event):
        items = self.canvas.find_withtag("current")
        if not items:
            return

        item_id = items[0]
        if item_id in self.drawn_edges_data:
            data = self.drawn_edges_data[item_id]
            p1, p2 = data["p1"], data["p2"]
            length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])

            self.info_traffic.set(f"Traffic Level: {data['traffic']}")
            self.info_type.set(f"Direction: {'Two-way' if data['two_way'] else 'One-way'}")
            self.info_length.set(f"Length: {length:.2f} px")

    # --------------------------------------------
    # Display
    # --------------------------------------------
    def update_graphics(self, event=None):
        node_idx = self.node_combo.current()
        if node_idx == 0:
            self.canvas.itemconfigure("node", state="normal", fill="#475569", outline="white")
        elif node_idx == 1:
            self.canvas.itemconfigure("node", state="normal", fill="", outline="white")
        else:
            self.canvas.itemconfigure("node", state="hidden")

        edge_idx = self.edge_combo.current()
        for lv in (1, 2, 3):
            tag = f"edge_lv{lv}"
            self.canvas.itemconfigure(
                tag,
                state=("normal" if edge_idx == 0 or edge_idx == lv else "hidden"),
            )

        self.apply_all_node_states()

    def apply_graphics_settings(self):
        self.update_graphics()

    def update_dynamic_styles(self):
        edge_width = max(1, int(3.5 * self.scale))
        node_border = max(1, int(1.8 * self.scale))
        path_width = max(2, int(5.5 * self.scale))
        marker_width = max(1, int(3 * self.scale))

        self.canvas.itemconfigure("edge", width=edge_width)
        self.canvas.itemconfigure("node", width=node_border)
        self.canvas.itemconfigure("path_line", width=path_width)
        self.canvas.itemconfigure("search_marker", width=marker_width)
        self.canvas.itemconfigure("selection_label", font=("Arial", max(8, int(10 * self.scale)), "bold"))

    # --------------------------------------------
    # Pan / zoom
    # --------------------------------------------
    def on_pan_move(self, event):
        if not self.is_panning:
            return

        dx = event.x - self.last_pan_x
        dy = event.y - self.last_pan_y
        self.move_world_by(dx, dy)
        self.last_pan_x = event.x
        self.last_pan_y = event.y

    def on_pan_end(self, event):
        self.is_panning = False

    def on_zoom(self, event):
        if event.num == 4 or getattr(event, "delta", 0) > 0:
            factor = 1.1
        elif event.num == 5 or getattr(event, "delta", 0) < 0:
            factor = 0.9
        else:
            return

        old_scale = self.scale
        new_scale = old_scale * factor

        if new_scale > self.max_scale:
            factor = self.max_scale / old_scale
            new_scale = self.max_scale
        elif new_scale < self.min_scale:
            factor = self.min_scale / old_scale
            new_scale = self.min_scale

        if abs(new_scale - old_scale) < 1e-12:
            return

        self.scale = new_scale
        cx, cy = event.x, event.y

        self.canvas.scale("world", cx, cy, factor, factor)
        self.offset_x = cx + factor * (self.offset_x - cx)
        self.offset_y = cy + factor * (self.offset_y - cy)

        self.update_background_image(quality="preview")
        self.update_dynamic_styles()
        self.sync_node_layers()
        self.apply_all_node_states()

        self.keep_world_inside_bounds()
        self.schedule_background_refine()

    # --------------------------------------------
    # Search control
    # --------------------------------------------
    def start_search(self):
        if self.search_running or self.search_algorithm is None:
            return
        if (
            self.selected_start is None
            or self.selected_goal is None
            or self.selected_start == self.selected_goal
        ):
            return

        self.clear_search_visuals(keep_selection=True)

        self.search_running = True
        self.stop_requested = False
        self.search_start_time = time.perf_counter()
        self.expanded_count = 0
        self.search_path_cost = 0.0
        self.path_nodes = []

        self.info_traffic.set("Traffic Level: -")
        self.info_type.set("Direction: -")
        self.info_length.set("Length: -")

        algo_name = self._get_search_algorithm_label()
        self.status_var.set(f"Status: {algo_name} running...")
        self.cost_var.set("Path Cost: -")
        self.expanded_var.set("Expanded Nodes: 0")
        self.runtime_var.set("Runtime: 0.00 s")

        self.refresh_control_states()

        facade = _SearchFacade(self)
        self.search_gen = iter(self.search_algorithm(facade))
        self.search_job = self.root.after(0, self._search_step)

    def _search_step(self):
        self.search_job = None

        if self.stop_requested or not self.search_running:
            return

        try:
            event = next(self.search_gen)
        except StopIteration:
            self.search_running = False
            self.stop_requested = False
            self.refresh_control_states()
            self._set_final_runtime()
            return

        self._apply_search_event(event)
        self.refresh_stats()

        if self.search_running:
            self.search_job = self.root.after(self.delay, self._search_step)

    def _apply_search_event(self, event):
        if not event:
            return

        etype = None
        payload = None

        if isinstance(event, dict):
            etype = event.get("type")
            payload = event
        elif isinstance(event, tuple):
            if len(event) >= 1:
                etype = event[0]
            if len(event) >= 2:
                payload = event[1]

        if etype == "status":
            if isinstance(event, dict):
                self.status_var.set(event.get("message", "Status: ..."))

        elif etype == "expand":
            node = payload if not isinstance(event, dict) else event.get("node")
            self.expanded_count += 1
            if node not in (self.selected_start, self.selected_goal):
                self.set_node_state(node, "expanded")

        elif etype == "reset_visuals":
            self.clear_visuals_only()

        elif etype in ("discover", "frontier"):
            node = payload if not isinstance(event, dict) else event.get("node")
            if node not in (self.selected_start, self.selected_goal):
                self.set_node_state(node, "frontier")

        elif etype in ("path", "goal"):
            path = payload if not isinstance(event, dict) else event.get("path")
            if not path:
                return

            self.path_nodes = list(path)
            self.search_path_cost = self._calculate_path_cost(path)

            self.canvas.delete("path_line")
            self.redraw_path_line()

            for node in path:
                if node not in (self.selected_start, self.selected_goal):
                    self.node_states[node] = "path"
                    self.apply_node_state(node)

            self.canvas.tag_raise("path_line")
            self.canvas.tag_raise("selection_label")
            self.canvas.tag_raise("search_marker")
            self.canvas.tag_raise("node")

            self.cost_var.set(f"Path Cost: {self.search_path_cost:.2f}")
            self.status_var.set("Status: Path found.")
            self.search_running = False
            self.stop_requested = False
            self._set_final_runtime()
            self.refresh_control_states()

        elif etype in ("finish", "fail"):
            self.search_running = False
            self.stop_requested = False
            self.status_var.set("Status: No path found.")
            self.cost_var.set("Path Cost: -")
            self._set_final_runtime()
            self.refresh_control_states()

    def stop_search(self):
        if not self.search_running:
            return

        self.stop_requested = True
        if self.search_job is not None:
            try:
                self.root.after_cancel(self.search_job)
            except Exception as e:
                print(e)
                
            self.search_job = None

        self.search_running = False
        self.status_var.set("Status: Stopped by user.")
        self._set_final_runtime()
        self.refresh_control_states()

    def reset_environment(self):
        if self.search_job is not None:
            try:
                self.root.after_cancel(self.search_job)
            except Exception as e:
                print(e)

        self.search_job = None
        self.search_gen = None
        self.search_running = False
        self.stop_requested = False
        self.selected_start = None
        self.selected_goal = None
        self.node_states = {}
        self.path_nodes = []
        self.expanded_count = 0
        self.search_path_cost = 0.0

        self.status_var.set("Status: Ready")
        self.cost_var.set("Path Cost: -")
        self.expanded_var.set("Expanded Nodes: 0")
        self.runtime_var.set("Runtime: 0.00 s")

        self.info_traffic.set("Traffic Level: -")
        self.info_type.set("Direction: -")
        self.info_length.set("Length: -")

        self.refresh_selection_text()
        self.draw_base_scene()
        self.refresh_control_states()