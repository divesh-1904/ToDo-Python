#!/usr/bin/env python3
"""
Todo Pipeline - Custom card-based flowchart view
Beautiful rounded cards with canvas-based rendering and direct line connections
Features: Card/Text mode toggle, Zoom in/out, Clean card design
"""

import tkinter as tk
from tkinter import messagebox
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid


class RoundedCard:
    """Custom rounded rectangle card drawn on canvas"""
    def __init__(self, canvas, x, y, width, height, radius, **kwargs):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.radius = radius
        self.fill = kwargs.get('fill', '#161b22')
        self.outline = kwargs.get('outline', '#30363d')
        self.outline_width = kwargs.get('outline_width', 2)
        
        self.items = []
        self._draw()
    
    def _draw(self):
        """Draw rounded rectangle"""
        x1, y1 = self.x, self.y
        x2, y2 = self.x + self.width, self.y + self.height
        r = self.radius
        
        # Draw rounded rectangle using arcs and lines
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1
        ]
        
        item = self.canvas.create_polygon(points, smooth=True, fill=self.fill,
                                         outline=self.outline, width=self.outline_width)
        self.items.append(item)
        
        return item


class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Todo Pipeline")
        self.root.geometry("1400x800")
        
        # Sticky mode state
        self.sticky_mode = True
        self.root.attributes('-topmost', self.sticky_mode)
        self.root.resizable(True, True)
        
        # Header scale (adjustable - 1.0 = 100%, 0.85 = 85%)
        self.header_scale = 0.85  # Set to 85% of original size
        
        # Data file
        self.data_file = "todo_data.json"
        self.tasks = {}
        self.current_view = "todo"
        self.view_mode = "card"  # "card" or "text"
        self.sort_mode = "priority"  # "priority" or "date"
        self.card_zoom_level = 1.0  # Zoom for card mode
        self.text_zoom_level = 1.0  # Zoom for text mode
        self.load_data()
        
        # Modern color scheme
        self.colors = {
            'bg': '#0d1117',
            'card_bg': '#161b22',
            'card_hover': '#21262d',
            'accent': '#ff6b35',
            'accent_dim': '#d45a2a',
            'text': '#c9d1d9',
            'text_dim': '#8b949e',
            'border': '#30363d',
            'success': '#238636',
            'warning': '#d29922',
            'line': '#ff6b35'
        }
        
        # Card dimensions (base values, will be scaled by zoom)
        self.base_card_width = 240          # Reduced from 280
        self.base_card_height = 120         # Reduced from 140
        self.base_card_spacing_h = 60       # Reduced from 80
        self.base_card_spacing_v = 50       # Reduced from 60
        self.base_level_indent = 30         # Reduced from 40
        
        # Task positions for drawing connections
        self.task_positions = {}  # task_id -> (x, y, width, height)
        
        # Drag and drop state
        self.dragging = False
        self.drag_task_id = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        self.setup_ui()
        self.refresh_pipeline()
    
    @property
    def zoom_level(self):
        """Return current zoom level based on active mode"""
        return self.card_zoom_level if self.view_mode == 'card' else self.text_zoom_level
    
    @property
    def card_width(self):
        return int(self.base_card_width * self.card_zoom_level)
    
    @property
    def card_height(self):
        return int(self.base_card_height * self.card_zoom_level)
    
    @property
    def card_spacing_h(self):
        return int(self.base_card_spacing_h * self.card_zoom_level)
    
    @property
    def card_spacing_v(self):
        return int(self.base_card_spacing_v * self.card_zoom_level)
    
    @property
    def level_indent(self):
        return int(self.base_level_indent * self.card_zoom_level)
    
    def setup_ui(self):
        """Setup the main UI"""
        self.root.configure(bg=self.colors['bg'])
        
        # Header with horizontal scroll capability
        header_container = tk.Frame(self.root, bg=self.colors['bg'])
        header_container.pack(fill=tk.X, padx=10, pady=(10, 10))
        
        # Canvas for header scrolling (scaled)
        header_canvas = tk.Canvas(header_container, bg=self.colors['bg'], height=int(90 * self.header_scale), highlightthickness=0)
        header_scrollbar = tk.Scrollbar(header_container, orient="horizontal", command=header_canvas.xview)
        header_canvas.configure(xscrollcommand=header_scrollbar.set)
        
        header_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        header_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Frame inside canvas for all header content
        header_frame = tk.Frame(header_canvas, bg=self.colors['bg'])
        header_canvas.create_window((0, 0), window=header_frame, anchor='nw')
        
        # Update scroll region when header changes
        def update_header_scroll(event=None):
            header_canvas.configure(scrollregion=header_canvas.bbox("all"))
        header_frame.bind("<Configure>", update_header_scroll)
        
        # Add mouse wheel scrolling to header
        def on_header_scroll(event):
            if event.num == 5 or event.delta < 0:
                header_canvas.xview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                header_canvas.xview_scroll(-1, "units")
        
        header_canvas.bind("<MouseWheel>", on_header_scroll)
        header_canvas.bind("<Button-4>", on_header_scroll)
        header_canvas.bind("<Button-5>", on_header_scroll)
        header_frame.bind("<MouseWheel>", on_header_scroll)
        header_frame.bind("<Button-4>", on_header_scroll)
        header_frame.bind("<Button-5>", on_header_scroll)
        
        title_label = tk.Label(
            header_frame,
            text="📋 PIPELINE",
            font=('Segoe UI', int(20 * self.header_scale), 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['accent']
        )
        title_label.pack(side=tk.LEFT, padx=int(10 * self.header_scale))
        
        # Tab buttons (TODO/DONE/STASH)
        tab_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        tab_frame.pack(side=tk.LEFT, padx=20)
        
        self.todo_tab_btn = tk.Button(
            tab_frame,
            text="TODO",
            font=('Segoe UI', int(12 * self.header_scale), 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(10 * self.header_scale),
            pady=int(8 * self.header_scale),
            command=lambda: self.switch_view('todo')
        )
        self.todo_tab_btn.pack(side=tk.LEFT, padx=int(5 * self.header_scale))
        
        self.done_tab_btn = tk.Button(
            tab_frame,
            text="DONE",
            font=('Segoe UI', int(12 * self.header_scale), 'bold'),
            bg=self.colors['border'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(10 * self.header_scale),
            pady=int(8 * self.header_scale),
            command=lambda: self.switch_view('done')
        )
        self.done_tab_btn.pack(side=tk.LEFT, padx=int(5 * self.header_scale))
        
        self.stash_tab_btn = tk.Button(
            tab_frame,
            text="STASH",
            font=('Segoe UI', int(12 * self.header_scale), 'bold'),
            bg=self.colors['border'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(10 * self.header_scale),
            pady=int(8 * self.header_scale),
            command=lambda: self.switch_view('stash')
        )
        self.stash_tab_btn.pack(side=tk.LEFT, padx=int(5 * self.header_scale))
        
        # View mode toggle (Card/Text)
        mode_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        mode_frame.pack(side=tk.LEFT, padx=int(20 * self.header_scale))
        
        self.card_mode_btn = tk.Button(
            mode_frame,
            text="CARD",
            font=('Segoe UI', int(10 * self.header_scale), 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(8 * self.header_scale),
            pady=int(6 * self.header_scale),
            command=lambda: self.switch_mode('card')
        )
        self.card_mode_btn.pack(side=tk.LEFT, padx=int(3 * self.header_scale))
        
        self.text_mode_btn = tk.Button(
            mode_frame,
            text="TEXT",
            font=('Segoe UI', int(10 * self.header_scale), 'bold'),
            bg=self.colors['border'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(8 * self.header_scale),
            pady=int(6 * self.header_scale),
            command=lambda: self.switch_mode('text')
        )
        self.text_mode_btn.pack(side=tk.LEFT, padx=int(3 * self.header_scale))
        
        # Sort mode toggle
        sort_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        sort_frame.pack(side=tk.LEFT, padx=int(20 * self.header_scale))
        
        tk.Label(
            sort_frame,
            text="SORT:",
            font=('Segoe UI', int(9 * self.header_scale)),
            bg=self.colors['bg'],
            fg=self.colors['text_dim']
        ).pack(side=tk.LEFT, padx=(0, int(5 * self.header_scale)))
        
        self.priority_sort_btn = tk.Button(
            sort_frame,
            text="PRIORITY",
            font=('Segoe UI', int(9 * self.header_scale), 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(9 * self.header_scale),
            pady=int(5 * self.header_scale),
            command=lambda: self.switch_sort('priority')
        )
        self.priority_sort_btn.pack(side=tk.LEFT, padx=int(2 * self.header_scale))
        
        self.date_sort_btn = tk.Button(
            sort_frame,
            text="DATE",
            font=('Segoe UI', int(9 * self.header_scale), 'bold'),
            bg=self.colors['border'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(9 * self.header_scale),
            pady=int(5 * self.header_scale),
            command=lambda: self.switch_sort('date')
        )
        self.date_sort_btn.pack(side=tk.LEFT, padx=int(2 * self.header_scale))
        
        # Zoom controls
        zoom_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        zoom_frame.pack(side=tk.LEFT, padx=int(20 * self.header_scale))
        
        tk.Button(
            zoom_frame,
            text="−",
            font=('Segoe UI', int(14 * self.header_scale), 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=int(3 * self.header_scale),
            pady=int(4 * self.header_scale),
            command=self.zoom_out
        ).pack(side=tk.LEFT, padx=int(2 * self.header_scale))
        
        self.zoom_label = tk.Label(
            zoom_frame,
            text="100%",
            font=('Segoe UI', int(10 * self.header_scale)),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            width=int(5 * self.header_scale)
        )
        self.zoom_label.pack(side=tk.LEFT, padx=int(5 * self.header_scale))
        
        tk.Button(
            zoom_frame,
            text="+",
            font=('Segoe UI', int(14 * self.header_scale), 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=3,
            pady=4,
            command=self.zoom_in
        ).pack(side=tk.LEFT, padx=2)
        
        # Sticky mode checkbox
        sticky_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        sticky_frame.pack(side=tk.LEFT, padx=20)
        
        self.sticky_var = tk.BooleanVar(value=self.sticky_mode)
        sticky_check = tk.Checkbutton(
            sticky_frame,
            text="📌 Sticky",
            variable=self.sticky_var,
            command=self.toggle_sticky,
            font=('Segoe UI', int(10 * self.header_scale)),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            activebackground=self.colors['bg'],
            activeforeground=self.colors['accent'],
            selectcolor=self.colors['card_bg'],
            cursor='hand2'
        )
        sticky_check.pack(side=tk.LEFT)
        
        # Right side buttons
        right_buttons = tk.Frame(header_frame, bg=self.colors['bg'])
        right_buttons.pack(side=tk.RIGHT)
        
        # Add task button
        tk.Button(
            right_buttons,
            text="+ NEW TASK",
            font=('Segoe UI', int(11 * self.header_scale), 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            relief=tk.FLAT,
            cursor='hand2',
            padx=20,
            pady=8,
            command=lambda: self.show_task_dialog(None)
        ).pack(side=tk.LEFT, padx=5)
        
        # Minimize button
        tk.Button(
            right_buttons,
            text="─",
            font=('Segoe UI', 16, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=3,
            command=self.root.iconify
        ).pack(side=tk.LEFT, padx=5)
        
        # Main pipeline container with scrollbars
        self.main_container = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))
        
        # Canvas container for card mode
        self.canvas_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        
        # Canvas with both scrollbars
        self.canvas = tk.Canvas(
            self.canvas_container,
            bg=self.colors['bg'],
            highlightthickness=0
        )
        
        self.v_scrollbar = tk.Scrollbar(self.canvas_container, orient="vertical", command=self.canvas.yview,
                                  bg=self.colors['card_bg'], troughcolor=self.colors['bg'],
                                  activebackground=self.colors['accent'])
        self.h_scrollbar = tk.Scrollbar(self.canvas_container, orient="horizontal", command=self.canvas.xview,
                                  bg=self.colors['card_bg'], troughcolor=self.colors['bg'],
                                  activebackground=self.colors['accent'])
        
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        
        self.v_scrollbar.pack(side="right", fill="y")
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Mouse wheel scrolling for card mode
        def on_card_mousewheel(event):
            # Handle different platforms
            if event.num == 5 or event.delta < 0:  # Scroll down (Linux: button 5, Windows/Mac: negative delta)
                self.canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:  # Scroll up (Linux: button 4, Windows/Mac: positive delta)
                self.canvas.yview_scroll(-1, "units")
        
        def on_card_h_mousewheel(event):
            # Handle different platforms
            if event.num == 5 or event.delta < 0:
                self.canvas.xview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                self.canvas.xview_scroll(-1, "units")
        
        self.canvas.bind("<MouseWheel>", on_card_mousewheel)  # Windows/Mac
        self.canvas.bind("<Button-4>", on_card_mousewheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", on_card_mousewheel)    # Linux scroll down
        self.canvas.bind("<Shift-MouseWheel>", on_card_h_mousewheel)  # Windows/Mac horizontal
        self.canvas.bind("<Shift-Button-4>", on_card_h_mousewheel)    # Linux horizontal
        self.canvas.bind("<Shift-Button-5>", on_card_h_mousewheel)    # Linux horizontal
        
        # Click handling for buttons on canvas
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.button_regions = {}  # region_id -> callback
        
        # Text mode container with scrollable frame
        self.text_container = tk.Frame(self.main_container, bg=self.colors['bg'])
        
        # Canvas for text mode scrolling
        self.text_canvas = tk.Canvas(
            self.text_container,
            bg=self.colors['bg'],
            highlightthickness=0
        )
        
        self.text_v_scrollbar = tk.Scrollbar(self.text_container, orient="vertical", 
                                             command=self.text_canvas.yview,
                                             bg=self.colors['card_bg'], 
                                             troughcolor=self.colors['bg'],
                                             activebackground=self.colors['accent'])
        
        self.text_h_scrollbar = tk.Scrollbar(self.text_container, orient="horizontal", 
                                             command=self.text_canvas.xview,
                                             bg=self.colors['card_bg'], 
                                             troughcolor=self.colors['bg'],
                                             activebackground=self.colors['accent'])
        
        self.text_canvas.configure(yscrollcommand=self.text_v_scrollbar.set,
                                   xscrollcommand=self.text_h_scrollbar.set)
        
        self.text_v_scrollbar.pack(side="right", fill="y")
        self.text_h_scrollbar.pack(side="bottom", fill="x")
        self.text_canvas.pack(side="left", fill="both", expand=True)
        
        # Scrollable frame inside text canvas
        self.scrollable_frame = tk.Frame(self.text_canvas, bg=self.colors['bg'])
        self.scrollable_frame_id = self.text_canvas.create_window(
            (0, 0), 
            window=self.scrollable_frame, 
            anchor="nw"
        )
        
        # Configure scrollable frame
        def configure_scroll_region(event=None):
            self.text_canvas.configure(scrollregion=self.text_canvas.bbox("all"))
        
        self.scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        # Mouse wheel scrolling for text mode
        def on_text_mousewheel(event):
            # Handle different platforms
            if event.num == 5 or event.delta < 0:  # Scroll down
                self.text_canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:  # Scroll up
                self.text_canvas.yview_scroll(-1, "units")
        
        def on_text_h_mousewheel(event):
            # Handle different platforms
            if event.num == 5 or event.delta < 0:
                self.text_canvas.xview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                self.text_canvas.xview_scroll(-1, "units")
        
        self.text_canvas.bind("<MouseWheel>", on_text_mousewheel)     # Windows/Mac
        self.text_canvas.bind("<Button-4>", on_text_mousewheel)       # Linux scroll up
        self.text_canvas.bind("<Button-5>", on_text_mousewheel)       # Linux scroll down
        self.text_canvas.bind("<Shift-MouseWheel>", on_text_h_mousewheel)  # Windows/Mac horizontal
        self.text_canvas.bind("<Shift-Button-4>", on_text_h_mousewheel)    # Linux horizontal
        self.text_canvas.bind("<Shift-Button-5>", on_text_h_mousewheel)    # Linux horizontal
        
        # Start with canvas container visible (card mode is default)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)
    
    def _on_canvas_click(self, event):
        """Handle clicks on canvas - check buttons first, then initiate drag"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # First, check if we clicked a button
        button_clicked = False
        for region_id, callback in self.button_regions.items():
            if region_id in self.canvas.find_all():
                coords = self.canvas.coords(region_id)
                if len(coords) >= 4:
                    x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
                    if x1 <= x <= x2 and y1 <= y <= y2:
                        callback()
                        button_clicked = True
                        break
        
        # If no button was clicked, check if we clicked on a card for dragging
        if not button_clicked:
            for task_id, (tx, ty, tw, th) in self.task_positions.items():
                if tx <= x <= tx + tw and ty <= y <= ty + th:
                    # Only allow dragging root tasks
                    task = self.tasks.get(task_id)
                    if task and task.get('parent_id') is None and not task.get('workflow_sibling_of'):
                        self.dragging = True
                        self.drag_task_id = task_id
                        self.drag_start_x = x
                        self.drag_start_y = y
                        self.drag_offset_x = x - tx
                        self.drag_offset_y = y - ty
                        # Change cursor to indicate dragging
                        self.canvas.config(cursor="hand2")
                        break
    
    def _on_canvas_drag(self, event):
        """Handle dragging motion"""
        if self.dragging and self.drag_task_id:
            # Visual feedback: you could highlight the card being dragged
            # For now, we'll just update cursor
            pass
    
    def _on_canvas_release(self, event):
        """Handle mouse release - drop the card"""
        if self.dragging and self.drag_task_id:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Find which task position we're hovering over
            dropped_on_task_id = None
            for task_id, (tx, ty, tw, th) in self.task_positions.items():
                if tx <= x <= tx + tw and ty <= y <= ty + th:
                    task = self.tasks.get(task_id)
                    # Only drop on root tasks
                    if task and task.get('parent_id') is None and not task.get('workflow_sibling_of'):
                        dropped_on_task_id = task_id
                        break
            
            # Swap priorities if we dropped on another task
            if dropped_on_task_id and dropped_on_task_id != self.drag_task_id:
                drag_priority = self.tasks[self.drag_task_id].get('priority', 999) or 999
                drop_priority = self.tasks[dropped_on_task_id].get('priority', 999) or 999
                
                # Swap priorities
                self.tasks[self.drag_task_id]['priority'] = drop_priority
                self.tasks[dropped_on_task_id]['priority'] = drag_priority
                
                self.save_data()
                self.refresh_pipeline()
            
            # Reset drag state
            self.dragging = False
            self.drag_task_id = None
            self.canvas.config(cursor="")
        else:
            self.dragging = False
            self.drag_task_id = None
            self.canvas.config(cursor="")
    
    def _on_canvas_motion(self, event):
        """Handle mouse motion to show cursor feedback for draggable cards"""
        if self.dragging:
            return  # Don't change cursor while dragging
        
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Check if hovering over a draggable root task
        over_draggable = False
        for task_id, (tx, ty, tw, th) in self.task_positions.items():
            if tx <= x <= tx + tw and ty <= y <= ty + th:
                task = self.tasks.get(task_id)
                if task and task.get('parent_id') is None and not task.get('workflow_sibling_of'):
                    over_draggable = True
                    break
        
        # Set cursor based on whether we're over a draggable card
        if over_draggable:
            self.canvas.config(cursor="fleur")  # Move cursor
        else:
            self.canvas.config(cursor="")
    
    def zoom_in(self):
        """Increase zoom level"""
        if self.view_mode == 'card':
            if self.card_zoom_level < 2.0:
                self.card_zoom_level += 0.1
                self.zoom_label.config(text=f"{int(self.card_zoom_level * 100)}%")
        else:
            if self.text_zoom_level < 2.0:
                self.text_zoom_level += 0.1
                self.zoom_label.config(text=f"{int(self.text_zoom_level * 100)}%")
        self.refresh_pipeline()
    
    def zoom_out(self):
        """Decrease zoom level"""
        if self.view_mode == 'card':
            if self.card_zoom_level > 0.5:
                self.card_zoom_level -= 0.1
                self.zoom_label.config(text=f"{int(self.card_zoom_level * 100)}%")
        else:
            if self.text_zoom_level > 0.5:
                self.text_zoom_level -= 0.1
                self.zoom_label.config(text=f"{int(self.text_zoom_level * 100)}%")
        self.refresh_pipeline()
    
    def toggle_sticky(self):
        """Toggle sticky (always on top) mode"""
        self.sticky_mode = self.sticky_var.get()
        self.root.attributes('-topmost', self.sticky_mode)
    
    def move_priority_up(self, task_id: str):
        """Move task priority up (decrease number = higher priority) - finds nearest lower priority"""
        if task_id not in self.tasks:
            return
        
        current_priority = self.tasks[task_id].get('priority', 999)
        
        # Get all priorities less than current, find the maximum (closest)
        lower_priorities = [t.get('priority', 999) for tid, t in self.tasks.items() 
                           if t.get('priority', 999) < current_priority and tid != task_id]
        
        if not lower_priorities:
            return  # No task with lower priority number (higher priority)
        
        target_priority = max(lower_priorities)  # Closest priority below current
        
        # Find task with that priority and swap
        for tid, t in self.tasks.items():
            if t.get('priority') == target_priority:
                self.tasks[tid]['priority'] = current_priority
                self.tasks[task_id]['priority'] = target_priority
                self.save_data()
                self.refresh_pipeline()
                return
    
    def move_priority_down(self, task_id: str):
        """Move task priority down (increase number = lower priority) - finds nearest higher priority"""
        if task_id not in self.tasks:
            return
        
        current_priority = self.tasks[task_id].get('priority', 999)
        
        # Get all priorities greater than current, find the minimum (closest)
        higher_priorities = [t.get('priority', 999) for tid, t in self.tasks.items() 
                            if t.get('priority', 999) > current_priority and tid != task_id]
        
        if not higher_priorities:
            return  # No task with higher priority number (lower priority)
        
        target_priority = min(higher_priorities)  # Closest priority above current
        
        # Find task with that priority and swap
        for tid, t in self.tasks.items():
            if t.get('priority') == target_priority:
                self.tasks[tid]['priority'] = current_priority
                self.tasks[task_id]['priority'] = target_priority
                self.save_data()
                self.refresh_pipeline()
                return
    
    def switch_view(self, view: str):
        self.current_view = view
        # Reset all tabs to inactive
        self.todo_tab_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
        self.done_tab_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
        self.stash_tab_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
        
        # Highlight active tab
        if view == 'todo':
            self.todo_tab_btn.configure(bg=self.colors['accent'], fg='#ffffff')
        elif view == 'done':
            self.done_tab_btn.configure(bg=self.colors['accent'], fg='#ffffff')
        elif view == 'stash':
            self.stash_tab_btn.configure(bg=self.colors['accent'], fg='#ffffff')
        
        self.refresh_pipeline()
    
    def switch_mode(self, mode: str):
        """Switch between card and text mode"""
        self.view_mode = mode
        if mode == 'card':
            self.card_mode_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.text_mode_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
            # Update zoom label for card mode
            self.zoom_label.config(text=f"{int(self.card_zoom_level * 100)}%")
            # Hide text container, show canvas container
            self.text_container.pack_forget()
            self.canvas_container.pack(fill=tk.BOTH, expand=True)
        else:
            self.text_mode_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.card_mode_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
            # Update zoom label for text mode
            self.zoom_label.config(text=f"{int(self.text_zoom_level * 100)}%")
            # Hide canvas container, show text container
            self.canvas_container.pack_forget()
            self.text_container.pack(fill=tk.BOTH, expand=True)
        self.refresh_pipeline()
    
    def switch_sort(self, mode: str):
        """Switch between priority and date sorting"""
        self.sort_mode = mode
        if mode == 'priority':
            self.priority_sort_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.date_sort_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
        else:
            self.date_sort_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.priority_sort_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
        self.refresh_pipeline()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.tasks = json.load(f)
            except Exception as e:
                print(f"Error loading data: {e}")
                self.tasks = {}
        else:
            self.tasks = {}
    
    def save_data(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def refresh_pipeline(self):
        """Refresh the entire pipeline view"""
        self.canvas.delete("all")
        self.task_positions = {}
        self.button_regions = {}
        
        if self.current_view == 'todo':
            root_tasks = [tid for tid, t in self.tasks.items()
                         if t.get('parent_id') is None 
                         and not t.get('completed', False) 
                         and not t.get('stashed', False)  # Exclude stashed tasks
                         and not t.get('workflow_sibling_of')]
        elif self.current_view == 'done':
            root_tasks = [tid for tid, t in self.tasks.items()
                         if t.get('parent_id') is None and t.get('completed', False) and not t.get('workflow_sibling_of')]
        elif self.current_view == 'stash':
            root_tasks = [tid for tid, t in self.tasks.items()
                         if t.get('parent_id') is None and t.get('stashed', False) and not t.get('workflow_sibling_of')]
        else:
            root_tasks = []
        
        # Sort based on selected sort mode
        if self.sort_mode == 'priority':
            # Sort by priority first (lower number = higher priority), then by creation date
            root_tasks.sort(key=lambda tid: (self.tasks[tid].get('priority', 999) or 999, self.tasks[tid].get('created', '')))
        else:  # date mode
            # Sort by creation date only
            root_tasks.sort(key=lambda tid: self.tasks[tid].get('created', ''))
        
        if not root_tasks:
            if self.current_view == 'todo':
                empty_text = "No tasks yet.\nClick '+ NEW TASK' to get started."
            elif self.current_view == 'done':
                empty_text = "No completed tasks yet."
            elif self.current_view == 'stash':
                empty_text = "No stashed tasks yet."
            else:
                empty_text = "No tasks."
            
            self.canvas.create_text(700, 300, text=empty_text,
                                  font=('Segoe UI', 14), fill=self.colors['text_dim'],
                                  justify=tk.CENTER)
        else:
            if self.view_mode == 'card':
                current_y = 40
                for idx, task_id in enumerate(root_tasks):
                    # Add separator line before each task (except the first)
                    if idx > 0:
                        separator_y = current_y - 20
                        self.canvas.create_line(
                            20, separator_y, 
                            1360, separator_y,  # Full width line
                            fill=self.colors['border'], 
                            width=2,
                            dash=(10, 5)  # Dashed line
                        )
                    
                    height = self._render_task_tree(task_id, 40, current_y, level=0)
                    current_y += height + 40
            else:  # text mode
                self._render_text_mode(root_tasks)
        
        # Update scroll region dynamically based on actual positions
        if self.task_positions:
            # Find the maximum x and y used by any task
            max_x = max(tx + tw for tx, ty, tw, th in self.task_positions.values())
            max_y = max(ty + th for tx, ty, tw, th in self.task_positions.values())
            # Add generous padding
            self.canvas.configure(scrollregion=(0, 0, max_x + 200, max_y + 200))
        else:
            bbox = self.canvas.bbox("all")
            if bbox:
                self.canvas.configure(scrollregion=(0, 0, max(bbox[2] + 500, 3000), bbox[3] + 100))
    
    def _render_text_mode(self, root_tasks: List[str]):
        """Render tasks in simple tree view mode (read-only, Maven dependency style)"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not root_tasks:
            if self.current_view == 'todo':
                empty_text = "No tasks yet.\nClick '+ NEW TASK' to get started."
            elif self.current_view == 'done':
                empty_text = "No completed tasks yet."
            elif self.current_view == 'stash':
                empty_text = "No stashed tasks yet."
            else:
                empty_text = "No tasks."
            
            empty_label = tk.Label(
                self.scrollable_frame,
                text=empty_text,
                font=('Courier New', int(12 * self.text_zoom_level)),
                bg=self.colors['bg'],
                fg=self.colors['text_dim'],
                justify=tk.CENTER
            )
            empty_label.pack(pady=100)
        else:
            # Render each root task as a tree with separators
            for idx, task_id in enumerate(root_tasks):
                # Add separator before each task (except the first)
                if idx > 0:
                    separator = tk.Label(
                        self.scrollable_frame,
                        text="─" * 80,
                        font=('Courier New', int(8 * self.text_zoom_level)),
                        bg=self.colors['bg'],
                        fg=self.colors['border'],
                        anchor='w'
                    )
                    separator.pack(anchor='w', padx=(int(10 * self.text_zoom_level), 0), pady=(int(5 * self.text_zoom_level), int(5 * self.text_zoom_level)))
                
                self._render_tree_node(self.scrollable_frame, task_id, level=0)
    
    def _render_tree_node(self, parent, task_id: str, level: int = 0, is_last_child: bool = True, prefix: str = "", show_subtasks: bool = True):
        """Render a single node in the tree view (Maven dependency style)
        Workflows stay at same level (↓ vertical continuations), subtasks indent (→ going forward into details)"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        completed = task.get('completed', False)
        stashed = task.get('stashed', False)
        priority = task.get('priority', 999)
        if priority is None:
            priority = 999
        
        # Filter based on current view - skip if doesn't match
        if self.current_view == 'todo':
            if completed or stashed:
                return  # Skip completed or stashed tasks in TODO view
        elif self.current_view == 'done':
            if not completed:
                return  # Skip non-completed tasks in DONE view
        elif self.current_view == 'stash':
            if not stashed:
                return  # Skip non-stashed tasks in STASH view
        
        # Build the tree characters
        if level == 0:
            tree_chars = ""
        else:
            # Use box-drawing characters for tree structure
            tree_chars = prefix + ("└── " if is_last_child else "├── ")
        
        # Build task text (without priority number)
        check_mark = "✓ " if completed else ("⏸ " if stashed else "")
        task_text = f"{tree_chars}{check_mark}{task['title']}"
        
        # Determine text color based on priority, completion, and stash status
        if completed:
            text_color = self.colors['text_dim']
        elif stashed:
            text_color = self.colors['warning']  # Orange for stashed
        elif priority <= 1:
            text_color = '#ff4444'
        elif priority <= 3:
            text_color = self.colors['accent']
        elif priority <= 5:
            text_color = self.colors['warning']
        else:
            text_color = self.colors['text']
        
        # Create label with tree structure
        font_style = 'overstrike' if completed else 'normal'
        task_label = tk.Label(
            parent,
            text=task_text,
            font=('Courier New', int(10 * self.text_zoom_level), font_style),
            bg=self.colors['bg'],
            fg=text_color,
            anchor='w',
            justify='left'
        )
        task_label.pack(anchor='w', padx=(int(10 * self.text_zoom_level), 0), pady=1)
        
        # Get subtasks (→ horizontal/forward - rendered as indented children going into details)
        subtasks = self.get_subtasks(task_id)
        
        # Render subtasks as indented children (going forward into details)
        # Note: filtering happens in _render_tree_node itself
        if subtasks:
            # Build prefix for subtask children (indented)
            if level == 0:
                child_prefix = ""
            else:
                child_prefix = prefix + ("    " if is_last_child else "│   ")
            
            for idx, sub_id in enumerate(subtasks):
                is_last = (idx == len(subtasks) - 1)
                self._render_tree_node(parent, sub_id, level + 1, is_last, child_prefix, show_subtasks=True)
        
        # Get workflow siblings (↓ vertical/below - rendered at SAME level as vertical continuations)
        if show_subtasks:
            workflow_siblings = self.get_workflow_siblings(task_id)
            
            # Render workflows at the SAME level as this task (vertical continuations)
            # Note: filtering happens in _render_tree_node itself
            for wf_id in workflow_siblings:
                # Use same prefix and level as current task
                self._render_tree_node(parent, wf_id, level, is_last_child=False, prefix=prefix, show_subtasks=True)
    
    def _render_task_tree(self, task_id: str, x: int, y: int, level: int = 0) -> int:
        """Render a task and all its children in card mode using iterative layout calculation"""
        task = self.tasks.get(task_id)
        if not task:
            return 0
        
        # Build complete layout tree first (breadth-first to avoid deep recursion)
        layout_queue = [(task_id, x, y, level)]
        max_y_used = y
        max_x_used = x
        
        while layout_queue:
            current_id, curr_x, curr_y, curr_level = layout_queue.pop(0)
            current_task = self.tasks.get(current_id)
            if not current_task:
                continue
            
            # Draw the current card
            card_height = self._draw_task_card(current_id, curr_x, curr_y)
            max_y_used = max(max_y_used, curr_y + card_height)
            max_x_used = max(max_x_used, curr_x + self.card_width)
            
            # Get subtasks (horizontal - go right)
            subtasks = self.get_subtasks(current_id)
            if subtasks:
                # Calculate horizontal position for subtasks
                subtask_x = curr_x + self.card_width + self.card_spacing_h
                
                for idx, sub_id in enumerate(subtasks):
                    # Draw horizontal arrow
                    if idx == 0:
                        line_y = curr_y + self.card_height // 2
                        line_width = int(3 * self.card_zoom_level)
                        self.canvas.create_line(
                            curr_x + self.card_width, line_y,
                            subtask_x - int(20 * self.card_zoom_level), line_y,
                            fill=self.colors['line'], width=line_width
                        )
                        arrow_size = int(6 * self.card_zoom_level)
                        self.canvas.create_polygon(
                            subtask_x - int(20 * self.card_zoom_level), line_y - arrow_size,
                            subtask_x - int(20 * self.card_zoom_level), line_y + arrow_size,
                            subtask_x - int(10 * self.card_zoom_level), line_y,
                            fill=self.colors['line'], outline=self.colors['line']
                        )
                    
                    # Queue subtask for rendering
                    layout_queue.append((sub_id, subtask_x, curr_y, curr_level))
                    
                    # Update subtask_x for next subtask in chain
                    # Calculate how much space this subtask branch will need
                    subtask_x += self.card_width + self.card_spacing_h
            
            # Get workflow siblings (vertical - go down)
            workflows = self.get_workflow_siblings(current_id)
            if workflows:
                # Calculate vertical position for workflows
                workflow_y = curr_y + card_height + self.card_spacing_v
                workflow_x = curr_x + self.level_indent
                
                # Draw vertical line
                line_start_x = curr_x + self.card_width // 2
                line_start_y = curr_y + card_height
                line_end_y = workflow_y - int(20 * self.card_zoom_level)
                line_width = int(3 * self.card_zoom_level)
                
                self.canvas.create_line(
                    line_start_x, line_start_y,
                    line_start_x, line_end_y,
                    fill=self.colors['line'], width=line_width
                )
                circle_r = int(5 * self.card_zoom_level)
                self.canvas.create_oval(
                    line_start_x - circle_r, line_end_y - circle_r,
                    line_start_x + circle_r, line_end_y + circle_r,
                    fill=self.colors['line'], outline=self.colors['line']
                )
                
                for wf_id in workflows:
                    layout_queue.append((wf_id, workflow_x, workflow_y, curr_level + 1))
                    workflow_y += self.card_height + self.card_spacing_v
        
        return max_y_used - y + self.card_height
    
    def _draw_task_card(self, task_id: str, x: int, y: int) -> int:
        """Draw a single task card and return its height"""
        task = self.tasks.get(task_id)
        if not task:
            return 0
        
        completed = task.get('completed', False)
        priority = task.get('priority', 999)
        
        # Card background color
        card_color = self.colors['success'] if completed else self.colors['card_bg']
        
        # Draw rounded card
        radius = int(12 * self.card_zoom_level)
        card = RoundedCard(
            self.canvas, x, y, self.card_width, self.card_height, radius,
            fill=card_color, outline=self.colors['border'], outline_width=int(2 * self.card_zoom_level)
        )
        
        # Store position
        self.task_positions[task_id] = (x, y, self.card_width, self.card_height)
        
        # Add drag handle icon for root tasks (top right corner)
        if task.get('parent_id') is None and not task.get('workflow_sibling_of'):
            drag_icon_size = int(16 * self.card_zoom_level)
            drag_icon_x = x + self.card_width - drag_icon_size - int(8 * self.card_zoom_level)
            drag_icon_y = y + int(8 * self.card_zoom_level)
            self.canvas.create_text(
                drag_icon_x, drag_icon_y,
                text="⋮⋮", 
                font=('Segoe UI', int(10 * self.card_zoom_level), 'bold'),
                fill=self.colors['text_dim'],
                anchor='nw'
            )
        
        # Card content
        padding = int(12 * self.card_zoom_level)  # Reduced from 16
        content_x = x + padding
        content_y = y + padding
        
        # Priority badge removed - priority still used for coloring but not displayed
        
        # Title with priority arrows (for root tasks only)
        title = task['title']
        title_length = int(35 / self.card_zoom_level)
        if len(title) > title_length:
            title = title[:title_length-3] + '...'
        
        # Add priority arrows for root tasks
        is_root_task = task.get('parent_id') is None and not task.get('workflow_sibling_of')
        if is_root_task:
            arrow_size = int(16 * self.card_zoom_level)
            arrow_x = content_x
            arrow_y = content_y
            
            # Up arrow - clickable rectangle
            up_rect = self.canvas.create_rectangle(
                arrow_x, arrow_y, 
                arrow_x + arrow_size, arrow_y + arrow_size,
                fill='', outline='', tags="button"
            )
            self.canvas.create_text(
                arrow_x + arrow_size // 2, arrow_y + arrow_size // 2,
                text="▲", 
                font=('Segoe UI', int(10 * self.card_zoom_level), 'bold'),
                fill=self.colors['accent']
            )
            self.button_regions[up_rect] = lambda tid=task_id: self.move_priority_up(tid)
            
            # Down arrow - clickable rectangle
            down_rect = self.canvas.create_rectangle(
                arrow_x + arrow_size, arrow_y,
                arrow_x + arrow_size * 2, arrow_y + arrow_size,
                fill='', outline='', tags="button"
            )
            self.canvas.create_text(
                arrow_x + arrow_size + arrow_size // 2, arrow_y + arrow_size // 2,
                text="▼",
                font=('Segoe UI', int(10 * self.card_zoom_level), 'bold'),
                fill=self.colors['warning']
            )
            self.button_regions[down_rect] = lambda tid=task_id: self.move_priority_down(tid)
            
            # Adjust title position to make room for arrows
            title_x = content_x + int(35 * self.card_zoom_level)
        else:
            title_x = content_x
        
        self.canvas.create_text(
            title_x, content_y,
            text=title, font=('Segoe UI', int(11 * self.card_zoom_level), 'bold'),
            fill='#ffffff' if completed else self.colors['text'],
            anchor='w', width=self.card_width - 2*padding - (int(35 * self.card_zoom_level) if is_root_task else 0)
        )
        content_y += int(24 * self.card_zoom_level)
        
        # Description
        if task.get('description'):
            desc = task['description']
            desc_length = int(60 / self.card_zoom_level)
            if len(desc) > desc_length:
                desc = desc[:desc_length-3] + '...'
            
            self.canvas.create_text(
                content_x, content_y,
                text=desc, font=('Segoe UI', int(8 * self.card_zoom_level)),  # Reduced from 9
                fill='#cccccc' if completed else self.colors['text_dim'],
                anchor='w', width=self.card_width - 2*padding
            )
            content_y += int(20 * self.card_zoom_level)  # Reduced from 25
        else:
            content_y += int(6 * self.card_zoom_level)  # Reduced from 10
        
        # Divider line
        self.canvas.create_line(
            x + padding, content_y, x + self.card_width - padding, content_y,
            fill=self.colors['border'], width=1
        )
        content_y += int(6 * self.card_zoom_level)  # Reduced from 8
        
        # Action buttons row
        btn_y = content_y
        btn_size = int(24 * self.card_zoom_level)  # Reduced from 28
        btn_spacing = int(6 * self.card_zoom_level)  # Reduced from 8
        
        # Left buttons: Subtask (→) goes horizontal, Workflow (↓) goes down
        btn_x = content_x
        
        # Check if task already has subtasks or workflows
        has_subtasks = len(self.get_subtasks(task_id)) > 0
        has_workflows = len(self.get_workflow_siblings(task_id)) > 0
        
        # Subtask button (only show if task doesn't have subtasks yet)
        if not has_subtasks:
            btn_rect = self.canvas.create_rectangle(
                btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
                fill=self.colors['warning'], outline='', tags="button"
            )
            self.canvas.create_text(
                btn_x + btn_size // 2, btn_y + btn_size // 2,
                text="→", font=('Segoe UI', int(10 * self.card_zoom_level), 'bold'), fill='#ffffff'
            )
            self.button_regions[btn_rect] = lambda tid=task_id: self.add_subtask(tid)
            btn_x += btn_size + btn_spacing
        
        # Workflow button (only show if task doesn't have workflows yet)
        if not has_workflows:
            btn_rect = self.canvas.create_rectangle(
                btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
                fill=self.colors['accent'], outline='', tags="button"
            )
            self.canvas.create_text(
                btn_x + btn_size // 2, btn_y + btn_size // 2,
                text="↓", font=('Segoe UI', int(10 * self.card_zoom_level), 'bold'), fill='#ffffff'
            )
            self.button_regions[btn_rect] = lambda tid=task_id: self.add_workflow_sibling(tid)
        
        # Right buttons: Edit, Delete, Done
        btn_x = x + self.card_width - padding - btn_size
        
        # Done button
        btn_rect = self.canvas.create_rectangle(
            btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
            fill='', outline='', tags="button"
        )
        self.canvas.create_text(
            btn_x + btn_size // 2, btn_y + btn_size // 2,
            text="✓" if completed else "○",
            font=('Segoe UI', int(12 * self.card_zoom_level), 'bold'),  # Reduced from 14
            fill='#ffffff' if completed else self.colors['success']
        )
        self.button_regions[btn_rect] = lambda tid=task_id, c=completed: self.toggle_done_status(
            tid, "Todo" if c else "Done ✓"
        )
        btn_x -= btn_size + btn_spacing
        
        # Stash button (📦 or pause icon)
        stashed = task.get('stashed', False)
        btn_rect = self.canvas.create_rectangle(
            btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
            fill=self.colors['warning'] if stashed else '', outline='', tags="button"
        )
        self.canvas.create_text(
            btn_x + btn_size // 2, btn_y + btn_size // 2,
            text="⏸" if stashed else "⏸",
            font=('Segoe UI', int(12 * self.card_zoom_level), 'bold'),
            fill='#ffffff' if stashed else self.colors['text_dim']
        )
        self.button_regions[btn_rect] = lambda tid=task_id: self.toggle_stash_status(tid)
        btn_x -= btn_size + btn_spacing
        
        # Delete button
        btn_rect = self.canvas.create_rectangle(
            btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
            fill='', outline='', tags="button"
        )
        self.canvas.create_text(
            btn_x + btn_size // 2, btn_y + btn_size // 2,
            text="×", font=('Segoe UI', int(14 * self.card_zoom_level), 'bold'), fill='#ff4444'  # Reduced from 16
        )
        self.button_regions[btn_rect] = lambda tid=task_id: self.delete_task(tid)
        btn_x -= btn_size + btn_spacing
        
        # Edit button
        btn_rect = self.canvas.create_rectangle(
            btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
            fill='', outline='', tags="button"
        )
        self.canvas.create_text(
            btn_x + btn_size // 2, btn_y + btn_size // 2,
            text="✎", font=('Segoe UI', int(12 * self.card_zoom_level)), fill=self.colors['text_dim']  # Reduced from 14
        )
        self.button_regions[btn_rect] = lambda tid=task_id: self.edit_task(tid)
        
        return self.card_height
    
    def get_subtasks(self, parent_id: str) -> List[str]:
        """Get ONLY direct subtasks (now render horizontally →), not workflow siblings"""
        subtasks = []
        for tid, t in self.tasks.items():
            if t.get('parent_id') == parent_id and not t.get('workflow_sibling_of'):
                subtasks.append(tid)
        
        subtasks.sort(key=lambda tid: self.tasks[tid].get('priority', 999) or 999)
        return subtasks
    
    def get_workflow_siblings(self, task_id: str) -> List[str]:
        """Get workflow siblings (now render vertically ↓) - only direct siblings, not recursive"""
        siblings = []
        
        # Find direct workflow siblings (tasks that reference this task)
        for tid, t in self.tasks.items():
            if t.get('workflow_sibling_of') == task_id:
                siblings.append(tid)
        
        siblings.sort(key=lambda tid: self.tasks[tid].get('created', ''))
        
        # Return only direct siblings - rendering will handle recursion
        return siblings
    
    def toggle_done_status(self, task_id: str, status: str):
        """Toggle task completion status"""
        if task_id in self.tasks:
            self.tasks[task_id]['completed'] = (status == "Done ✓")
            # Un-stash if marking as done
            if self.tasks[task_id]['completed']:
                self.tasks[task_id]['stashed'] = False
            self.save_data()
            self.refresh_pipeline()
    
    def toggle_stash_status(self, task_id: str):
        """Toggle task stashed status (temporarily closed) - cascades to children"""
        if task_id in self.tasks:
            current_stashed = self.tasks[task_id].get('stashed', False)
            new_stashed = not current_stashed
            
            # Apply stash status to this task and all children
            self._set_stash_recursive(task_id, new_stashed)
            
            self.save_data()
            self.refresh_pipeline()
    
    def _set_stash_recursive(self, task_id: str, stashed: bool):
        """Recursively set stash status for task and all its children"""
        if task_id not in self.tasks:
            return
        
        self.tasks[task_id]['stashed'] = stashed
        
        # Un-complete if stashing
        if stashed:
            self.tasks[task_id]['completed'] = False
        
        # Apply to all subtasks
        for subtask_id in self.get_subtasks(task_id):
            self._set_stash_recursive(subtask_id, stashed)
        
        # Apply to all workflow siblings
        for workflow_id in self.get_workflow_siblings(task_id):
            self._set_stash_recursive(workflow_id, stashed)
    
    def add_subtask(self, parent_id: str):
        """Add a subtask (now goes horizontally → to the right)"""
        self.show_task_dialog(parent_id=parent_id, is_workflow=False)
    
    def add_workflow_sibling(self, sibling_of_id: str):
        """Add a workflow sibling (now goes vertically ↓ below)"""
        task = self.tasks.get(sibling_of_id)
        if task:
            # Workflow siblings share the same parent but are marked differently
            parent_id = task.get('parent_id')
            self.show_task_dialog(parent_id=parent_id, is_workflow=True, workflow_sibling_of=sibling_of_id)
    
    def show_task_dialog(self, parent_id: Optional[str] = None, is_workflow: bool = False, workflow_sibling_of: Optional[str] = None):
        """Show dialog to create new task"""
        dialog = tk.Toplevel(self.root)
        dialog.title("New Task")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])
        dialog.attributes('-topmost', True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        if is_workflow:
            title_text = "Create Workflow Task (↓ Below)"
        elif parent_id:
            title_text = "Create Subtask (→ Forward)"
        else:
            title_text = "Create New Task"
        
        tk.Label(dialog, text=title_text, font=('Segoe UI', 16, 'bold'),
                bg=self.colors['bg'], fg=self.colors['text']).pack(pady=(20, 10))
        
        fields = tk.Frame(dialog, bg=self.colors['bg'])
        fields.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        tk.Label(fields, text="Title:", font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w')
        title_entry = tk.Entry(fields, font=('Segoe UI', 11), bg=self.colors['card_bg'],
                              fg=self.colors['text'], insertbackground=self.colors['text'],
                              relief=tk.FLAT, bd=2)
        title_entry.pack(fill=tk.X, pady=(5, 15), ipady=5)
        title_entry.focus()
        
        tk.Label(fields, text="Description:", font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w')
        desc_text = tk.Text(fields, font=('Segoe UI', 10), bg=self.colors['card_bg'],
                           fg=self.colors['text'], insertbackground=self.colors['text'],
                           relief=tk.FLAT, bd=2, height=3, wrap=tk.WORD)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        # Priority field removed - will be auto-assigned
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=20)
        
        def create_task():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("Warning", "Please enter a title")
                return
            
            # Auto-assign next available priority (sequential starting from 1)
            existing_priorities = [t.get('priority', 0) for t in self.tasks.values()]
            if existing_priorities:
                priority_val = max(existing_priorities) + 1
            else:
                priority_val = 1
            
            task_id = str(uuid.uuid4())
            new_task = {
                'id': task_id,
                'title': title,
                'description': desc_text.get('1.0', 'end-1c').strip(),
                'completed': False,
                'parent_id': parent_id,
                'created': datetime.now().isoformat(),
                'priority': priority_val
            }
            
            # Mark workflow siblings
            if is_workflow and workflow_sibling_of:
                new_task['workflow_sibling_of'] = workflow_sibling_of
            
            self.tasks[task_id] = new_task
            self.save_data()
            self.refresh_pipeline()
            dialog.destroy()
        
        tk.Button(btn_frame, text="CANCEL", font=('Segoe UI', 10),
                 bg=self.colors['card_bg'], fg=self.colors['text_dim'],
                 relief=tk.FLAT, cursor='hand2', command=dialog.destroy, width=12).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="CREATE", font=('Segoe UI', 10, 'bold'),
                 bg=self.colors['accent'], fg='#ffffff', relief=tk.FLAT,
                 cursor='hand2', command=create_task, width=12).pack(side=tk.RIGHT)
        
        dialog.bind('<Return>', lambda e: create_task())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def edit_task(self, task_id: str):
        """Show dialog to edit existing task"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Task")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])
        dialog.attributes('-topmost', True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Edit Task", font=('Segoe UI', 16, 'bold'),
                bg=self.colors['bg'], fg=self.colors['text']).pack(pady=(20, 10))
        
        fields = tk.Frame(dialog, bg=self.colors['bg'])
        fields.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        tk.Label(fields, text="Title:", font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w')
        title_entry = tk.Entry(fields, font=('Segoe UI', 11), bg=self.colors['card_bg'],
                              fg=self.colors['text'], insertbackground=self.colors['text'],
                              relief=tk.FLAT, bd=2)
        title_entry.insert(0, task['title'])
        title_entry.pack(fill=tk.X, pady=(5, 15), ipady=5)
        title_entry.focus()
        
        tk.Label(fields, text="Description:", font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text']).pack(anchor='w')
        desc_text = tk.Text(fields, font=('Segoe UI', 10), bg=self.colors['card_bg'],
                           fg=self.colors['text'], insertbackground=self.colors['text'],
                           relief=tk.FLAT, bd=2, height=3, wrap=tk.WORD)
        desc_text.insert('1.0', task.get('description', ''))
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        # Priority field removed - can only be changed via drag & drop
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=20)
        
        def save_changes():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("Warning", "Please enter a title")
                return
            
            # Priority is not changed during edit - only via drag & drop
            self.tasks[task_id]['title'] = title
            self.tasks[task_id]['description'] = desc_text.get('1.0', 'end-1c').strip()
            # Keep existing priority
            self.save_data()
            self.refresh_pipeline()
            dialog.destroy()
        
        tk.Button(btn_frame, text="CANCEL", font=('Segoe UI', 10),
                 bg=self.colors['card_bg'], fg=self.colors['text_dim'],
                 relief=tk.FLAT, cursor='hand2', command=dialog.destroy, width=12).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="SAVE", font=('Segoe UI', 10, 'bold'),
                 bg=self.colors['accent'], fg='#ffffff', relief=tk.FLAT,
                 cursor='hand2', command=save_changes, width=12).pack(side=tk.RIGHT)
        
        dialog.bind('<Return>', lambda e: save_changes())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def delete_task(self, task_id: str):
        """Delete task and all its subtasks"""
        subtasks = self.get_subtasks(task_id)
        workflow_siblings = self.get_workflow_siblings(task_id)
        
        msg = "Delete this task?"
        if subtasks:
            msg += f"\n\nThis will also delete {len(subtasks)} subtask(s)."
        if workflow_siblings:
            msg += f"\n\nThis will also delete {len(workflow_siblings)} workflow sibling(s)."
            
        if messagebox.askyesno("Confirm Delete", msg):
            self._delete_recursive(task_id)
            self.save_data()
            self.refresh_pipeline()
    
    def _delete_recursive(self, task_id: str):
        """Recursively delete task, all subtasks, and workflow siblings"""
        # Delete subtasks
        for subtask_id in self.get_subtasks(task_id):
            self._delete_recursive(subtask_id)
        
        # Delete workflow siblings
        for sibling_id in self.get_workflow_siblings(task_id):
            self._delete_recursive(sibling_id)
        
        # Delete the task itself
        if task_id in self.tasks:
            del self.tasks[task_id]


def main():
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
