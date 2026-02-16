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
        
        # Make window always on top (sticky)
        self.root.attributes('-topmost', True)
        self.root.resizable(True, True)
        
        # Data file
        self.data_file = "todo_data.json"
        self.tasks = {}
        self.current_view = "todo"
        self.view_mode = "card"  # "card" or "text"
        self.zoom_level = 1.0  # Default zoom
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
        self.base_card_width = 280
        self.base_card_height = 140  # Reduced from 160 to remove bottom space
        self.base_card_spacing_h = 80
        self.base_card_spacing_v = 60
        self.base_level_indent = 40
        
        # Task positions for drawing connections
        self.task_positions = {}  # task_id -> (x, y, width, height)
        
        self.setup_ui()
        self.refresh_pipeline()
    
    @property
    def card_width(self):
        return int(self.base_card_width * self.zoom_level)
    
    @property
    def card_height(self):
        return int(self.base_card_height * self.zoom_level)
    
    @property
    def card_spacing_h(self):
        return int(self.base_card_spacing_h * self.zoom_level)
    
    @property
    def card_spacing_v(self):
        return int(self.base_card_spacing_v * self.zoom_level)
    
    @property
    def level_indent(self):
        return int(self.base_level_indent * self.zoom_level)
    
    def setup_ui(self):
        """Setup the main UI"""
        self.root.configure(bg=self.colors['bg'])
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.colors['bg'], height=70)
        header_frame.pack(fill=tk.X, padx=30, pady=(20, 10))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="📋 PIPELINE",
            font=('Segoe UI', 24, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['accent']
        )
        title_label.pack(side=tk.LEFT)
        
        # Tab buttons (TODO/DONE)
        tab_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        tab_frame.pack(side=tk.LEFT, padx=40)
        
        self.todo_tab_btn = tk.Button(
            tab_frame,
            text="TODO",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            relief=tk.FLAT,
            cursor='hand2',
            width=10,
            pady=8,
            command=lambda: self.switch_view('todo')
        )
        self.todo_tab_btn.pack(side=tk.LEFT, padx=5)
        
        self.done_tab_btn = tk.Button(
            tab_frame,
            text="DONE",
            font=('Segoe UI', 12, 'bold'),
            bg=self.colors['border'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=10,
            pady=8,
            command=lambda: self.switch_view('done')
        )
        self.done_tab_btn.pack(side=tk.LEFT, padx=5)
        
        # View mode toggle (Card/Text)
        mode_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        mode_frame.pack(side=tk.LEFT, padx=20)
        
        self.card_mode_btn = tk.Button(
            mode_frame,
            text="CARD",
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            relief=tk.FLAT,
            cursor='hand2',
            width=8,
            pady=6,
            command=lambda: self.switch_mode('card')
        )
        self.card_mode_btn.pack(side=tk.LEFT, padx=3)
        
        self.text_mode_btn = tk.Button(
            mode_frame,
            text="TEXT",
            font=('Segoe UI', 10, 'bold'),
            bg=self.colors['border'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=8,
            pady=6,
            command=lambda: self.switch_mode('text')
        )
        self.text_mode_btn.pack(side=tk.LEFT, padx=3)
        
        # Zoom controls
        zoom_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        zoom_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Button(
            zoom_frame,
            text="−",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=3,
            pady=4,
            command=self.zoom_out
        ).pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = tk.Label(
            zoom_frame,
            text="100%",
            font=('Segoe UI', 10),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            width=5
        )
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            zoom_frame,
            text="+",
            font=('Segoe UI', 14, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            activebackground=self.colors['card_hover'],
            relief=tk.FLAT,
            cursor='hand2',
            width=3,
            pady=4,
            command=self.zoom_in
        ).pack(side=tk.LEFT, padx=2)
        
        # Right side buttons
        right_buttons = tk.Frame(header_frame, bg=self.colors['bg'])
        right_buttons.pack(side=tk.RIGHT)
        
        # Add task button
        tk.Button(
            right_buttons,
            text="+ NEW TASK",
            font=('Segoe UI', 11, 'bold'),
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
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_h_mousewheel)
        
        # Click handling for buttons on canvas
        self.canvas.bind("<Button-1>", self._on_canvas_click)
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
            self.text_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def on_text_h_mousewheel(event):
            self.text_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        
        self.text_canvas.bind_all("<MouseWheel>", on_text_mousewheel)
        self.text_canvas.bind_all("<Shift-MouseWheel>", on_text_h_mousewheel)
        
        # Start with canvas container visible (card mode is default)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_h_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_canvas_click(self, event):
        """Handle clicks on canvas buttons"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        for region_id, callback in self.button_regions.items():
            if region_id in self.canvas.find_all():
                coords = self.canvas.coords(region_id)
                if len(coords) >= 4:
                    x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
                    if x1 <= x <= x2 and y1 <= y <= y2:
                        callback()
                        break
    
    def zoom_in(self):
        """Increase zoom level"""
        if self.zoom_level < 2.0:
            self.zoom_level += 0.1
            self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
            self.refresh_pipeline()
    
    def zoom_out(self):
        """Decrease zoom level"""
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.1
            self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
            self.refresh_pipeline()
    
    def switch_view(self, view: str):
        self.current_view = view
        if view == 'todo':
            self.todo_tab_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.done_tab_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
        else:
            self.done_tab_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.todo_tab_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
        self.refresh_pipeline()
    
    def switch_mode(self, mode: str):
        """Switch between card and text mode"""
        self.view_mode = mode
        if mode == 'card':
            self.card_mode_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.text_mode_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
            # Hide text container, show canvas container
            self.text_container.pack_forget()
            self.canvas_container.pack(fill=tk.BOTH, expand=True)
        else:
            self.text_mode_btn.configure(bg=self.colors['accent'], fg='#ffffff')
            self.card_mode_btn.configure(bg=self.colors['border'], fg=self.colors['text_dim'])
            # Hide canvas container, show text container
            self.canvas_container.pack_forget()
            self.text_container.pack(fill=tk.BOTH, expand=True)
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
                         if t.get('parent_id') is None and not t.get('completed', False)]
        else:
            root_tasks = [tid for tid, t in self.tasks.items()
                         if t.get('parent_id') is None and t.get('completed', False)]
        
        root_tasks.sort(key=lambda tid: self.tasks[tid].get('created', ''))
        
        if not root_tasks:
            empty_text = "No tasks yet.\nClick '+ NEW TASK' to get started." if self.current_view == 'todo' else "No completed tasks yet."
            self.canvas.create_text(700, 300, text=empty_text,
                                  font=('Segoe UI', 14), fill=self.colors['text_dim'],
                                  justify=tk.CENTER)
        else:
            if self.view_mode == 'card':
                current_y = 40
                for task_id in root_tasks:
                    height = self._render_task_tree(task_id, 40, current_y, level=0)
                    current_y += height + 40
            else:  # text mode
                self._render_text_mode(root_tasks)
        
        # Update scroll region
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=(0, 0, bbox[2] + 100, bbox[3] + 100))
    
    def _render_text_mode(self, root_tasks: List[str]):
        """Render tasks in simple text list mode"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not root_tasks:
            empty_text = "No tasks yet.\nClick '+ NEW TASK' to get started." if self.current_view == 'todo' else "No completed tasks yet."
            empty_label = tk.Label(
                self.scrollable_frame,
                text=empty_text,
                font=('Courier New', 12),
                bg=self.colors['bg'],
                fg=self.colors['text_dim'],
                justify=tk.CENTER
            )
            empty_label.pack(pady=100)
        else:
            # Render each workflow chain
            for task_id in root_tasks:
                self.render_text_task_card(self.scrollable_frame, task_id, level=0)
    
    def render_text_task_card(self, parent, task_id: str, level: int = 0, rendered_tasks: set = None):
        """Render a task in text mode using frames (like reference code)"""
        if rendered_tasks is None:
            rendered_tasks = set()
        
        # Skip if already rendered
        if task_id in rendered_tasks:
            return
        rendered_tasks.add(task_id)
        
        task = self.tasks.get(task_id)
        if not task:
            return
        
        completed = task.get('completed', False)
        priority = task.get('priority', 999)
        if priority is None:
            priority = 999
        
        # Container for this task, its workflow siblings, and all their subtasks
        main_container = tk.Frame(parent, bg=self.colors['bg'])
        main_container.pack(anchor='nw', pady=2)
        
        # Vertical connector if this is a subtask
        if level > 0:
            connector_row = tk.Frame(main_container, bg=self.colors['bg'])
            connector_row.pack(anchor='w')
            indent = "    " * level
            v_line = tk.Label(connector_row, text=f"{indent}|", font=('Courier New', 9), 
                             bg=self.colors['bg'], fg=self.colors['line'])
            v_line.pack(anchor='w')
        
        # Horizontal row for workflow siblings
        workflow_row = tk.Frame(main_container, bg=self.colors['bg'])
        workflow_row.pack(anchor='w')
        
        # Get all tasks in this workflow chain
        workflow_chain = [task_id] + self.get_workflow_siblings(task_id)
        
        # Container to hold each task and its subtasks vertically
        task_columns = []
        
        # Render each task in the workflow chain
        prev_task_label = None  # Keep track of previous task label for width calculation
        
        for idx, chain_task_id in enumerate(workflow_chain):
            if chain_task_id in rendered_tasks and chain_task_id != task_id:
                continue
            
            if chain_task_id != task_id:
                rendered_tasks.add(chain_task_id)
            
            chain_task = self.tasks.get(chain_task_id)
            if not chain_task:
                continue
            
            is_completed = chain_task.get('completed', False)
            task_priority = chain_task.get('priority', 999)
            if task_priority is None:
                task_priority = 999
            
            # Column for this task and its subtasks
            task_column = tk.Frame(workflow_row, bg=self.colors['bg'])
            task_column.pack(side=tk.LEFT, anchor='n')
            task_columns.append((task_column, chain_task_id))
            
            # Task row
            task_row = tk.Frame(task_column, bg=self.colors['bg'])
            task_row.pack(anchor='w')
            
            # Indent for level (only on first task)
            if idx == 0:
                indent = "    " * level
                indent_lbl = tk.Label(task_row, text=indent, font=('Courier New', 10), 
                                     bg=self.colors['bg'])
                indent_lbl.pack(side=tk.LEFT)
            
            # Horizontal connector for workflow (not first in chain)
            if idx > 0 and prev_task_label is not None:
                # Create connector that will be updated after task label is rendered
                connector = tk.Label(task_row, text=" ", font=('Courier New', 9), 
                                   bg=self.colors['bg'], fg=self.colors['line'])
                connector.pack(side=tk.LEFT)
            
            # Task text with priority
            priority_text = f"[{task_priority}]" if task_priority != 999 else ""
            task_text = f"{priority_text} {chain_task['title']}" if priority_text else chain_task['title']
            
            if is_completed:
                task_text = f"✓ {task_text}"
            
            # Determine text color based on priority and completion
            if is_completed:
                text_color = self.colors['text_dim']
            elif task_priority <= 1:
                text_color = '#ff4444'
            elif task_priority <= 3:
                text_color = self.colors['accent']
            elif task_priority <= 5:
                text_color = self.colors['warning']
            else:
                text_color = self.colors['text']
            
            task_lbl = tk.Label(
                task_row,
                text=task_text,
                font=('Courier New', 10, 'overstrike' if is_completed else 'normal'),
                bg=self.colors['bg'],
                fg=text_color
            )
            task_lbl.pack(side=tk.LEFT, padx=(0, 5))
            
            # Update connector after label is created and we can measure it
            if idx > 0 and prev_task_label is not None:
                # Force update to get accurate width
                task_row.update_idletasks()
                prev_task_label.update_idletasks()
                
                # Calculate number of dashes needed to bridge the gap
                # Each dash (–) is roughly 7-8 pixels in Courier New 9
                prev_width = prev_task_label.winfo_width()
                dash_char_width = 7  # Approximate width of – character in pixels
                # Base number of dashes on previous task width
                num_dashes = max(3, prev_width // dash_char_width)
                
                connector_text = "–" * num_dashes + "→ "
                connector.config(text=connector_text)
            
            # Store reference for next iteration
            prev_task_label = task_lbl
            
            # Action buttons
            actions = tk.Frame(task_row, bg=self.colors['bg'])
            actions.pack(side=tk.LEFT)
            
            # → button (add workflow)
            btn_workflow = tk.Label(actions, text="→", font=('Courier New', 8), bg=self.colors['bg'], 
                                    fg=self.colors['accent'], cursor='hand2')
            btn_workflow.pack(side=tk.LEFT, padx=1)
            btn_workflow.bind('<Button-1>', lambda e, tid=chain_task_id: self.add_workflow_sibling(tid))
            
            # ↓ button (add subtask)
            btn_subtask = tk.Label(actions, text="↓", font=('Courier New', 8), bg=self.colors['bg'], 
                                   fg=self.colors['warning'], cursor='hand2')
            btn_subtask.pack(side=tk.LEFT, padx=1)
            btn_subtask.bind('<Button-1>', lambda e, tid=chain_task_id: self.add_subtask(tid))
            
            # Edit button
            btn_edit = tk.Label(actions, text="✎", font=('Courier New', 8), bg=self.colors['bg'], 
                               fg=self.colors['text_dim'], cursor='hand2')
            btn_edit.pack(side=tk.LEFT, padx=1)
            btn_edit.bind('<Button-1>', lambda e, tid=chain_task_id: self.edit_task(tid))
            
            # Delete button
            btn_del = tk.Label(actions, text="×", font=('Courier New', 9), bg=self.colors['bg'], 
                              fg=self.colors['text_dim'], cursor='hand2')
            btn_del.pack(side=tk.LEFT, padx=1)
            btn_del.bind('<Button-1>', lambda e, tid=chain_task_id: self.delete_task(tid))
            
            # Done toggle
            done_text = "✓" if is_completed else "○"
            btn_done = tk.Label(actions, text=done_text, font=('Courier New', 9), 
                               bg=self.colors['success'] if is_completed else self.colors['bg'],
                               fg='#ffffff' if is_completed else self.colors['text_dim'], 
                               cursor='hand2', padx=2)
            btn_done.pack(side=tk.LEFT, padx=1)
            btn_done.bind('<Button-1>', lambda e, tid=chain_task_id, comp=is_completed: 
                        self.toggle_done_status(tid, "Todo" if comp else "Done ✓"))
        
        # Now render subtasks for EACH task in the workflow chain
        for task_column, chain_task_id in task_columns:
            subtasks = self.get_subtasks(chain_task_id)
            if subtasks:
                for subtask_id in subtasks:
                    self.render_text_task_card(task_column, subtask_id, level=level + 1, rendered_tasks=rendered_tasks)
    
    def _render_task_tree(self, task_id: str, x: int, y: int, level: int = 0) -> int:
        """Render a task and all its children in card mode, return total height used"""
        task = self.tasks.get(task_id)
        if not task:
            return 0
        
        # Get workflow siblings (tasks that follow this one horizontally)
        workflow_chain = [task_id] + self.get_workflow_siblings(task_id)
        
        max_height = 0
        current_x = x
        
        # Track the maximum x position used by each workflow item and its subtasks
        branch_widths = []
        
        for idx, chain_task_id in enumerate(workflow_chain):
            chain_task = self.tasks.get(chain_task_id)
            if not chain_task:
                continue
            
            # Draw horizontal arrow if not first in chain
            if idx > 0:
                prev_pos = self.task_positions.get(workflow_chain[idx-1])
                if prev_pos:
                    prev_x, prev_y, prev_w, prev_h = prev_pos
                    # Horizontal line from previous card to current
                    line_y = prev_y + prev_h // 2
                    line_width = int(3 * self.zoom_level)
                    self.canvas.create_line(
                        prev_x + prev_w, line_y,
                        current_x - int(20 * self.zoom_level), line_y,
                        fill=self.colors['line'], width=line_width
                    )
                    # Arrow head
                    arrow_size = int(6 * self.zoom_level)
                    self.canvas.create_polygon(
                        current_x - int(20 * self.zoom_level), line_y - arrow_size,
                        current_x - int(20 * self.zoom_level), line_y + arrow_size,
                        current_x - int(10 * self.zoom_level), line_y,
                        fill=self.colors['line'], outline=self.colors['line']
                    )
            
            # Draw the card
            card_height = self._draw_task_card(chain_task_id, current_x, y)
            
            # Track the starting x for this branch
            branch_start_x = current_x
            
            # Get ONLY actual subtasks (not workflow siblings)
            subtasks = self.get_subtasks(chain_task_id)
            
            # Track maximum x used by this branch
            max_branch_x = current_x + self.card_width
            
            if subtasks:
                # Calculate position for subtasks (below this card)
                subtask_y = y + card_height + self.card_spacing_v
                subtask_x = current_x + self.level_indent
                
                # Draw vertical line down to subtasks
                card_pos = self.task_positions.get(chain_task_id)
                if card_pos:
                    cx, cy, cw, ch = card_pos
                    line_start_x = cx + cw // 2
                    line_start_y = cy + ch
                    line_end_y = subtask_y - int(20 * self.zoom_level)
                    line_width = int(3 * self.zoom_level)
                    
                    # Vertical line
                    self.canvas.create_line(
                        line_start_x, line_start_y,
                        line_start_x, line_end_y,
                        fill=self.colors['line'], width=line_width
                    )
                    # Circle at end
                    circle_r = int(5 * self.zoom_level)
                    self.canvas.create_oval(
                        line_start_x - circle_r, line_end_y - circle_r,
                        line_start_x + circle_r, line_end_y + circle_r,
                        fill=self.colors['line'], outline=self.colors['line']
                    )
                
                # Render all subtasks and track their width
                subtask_height = 0
                for sub_id in subtasks:
                    h = self._render_task_tree(sub_id, subtask_x, subtask_y + subtask_height, level + 1)
                    subtask_height += h + int(30 * self.zoom_level)
                    
                    # Update max_branch_x based on subtask positions
                    # Check all task positions created by subtask rendering
                    for tid, (tx, ty, tw, th) in self.task_positions.items():
                        if ty >= subtask_y:  # Only consider tasks at or below subtask level
                            max_branch_x = max(max_branch_x, tx + tw)
                
                max_height = max(max_height, card_height + self.card_spacing_v + subtask_height)
            else:
                max_height = max(max_height, card_height)
            
            # Store the width used by this branch
            branch_width = max_branch_x - branch_start_x
            branch_widths.append(branch_width)
            
            # Calculate next card position to avoid overlap
            # Use the maximum width of this branch plus spacing
            current_x = max_branch_x + self.card_spacing_h
        
        return max_height
    
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
        radius = int(12 * self.zoom_level)
        card = RoundedCard(
            self.canvas, x, y, self.card_width, self.card_height, radius,
            fill=card_color, outline=self.colors['border'], outline_width=int(2 * self.zoom_level)
        )
        
        # Store position
        self.task_positions[task_id] = (x, y, self.card_width, self.card_height)
        
        # Card content
        padding = int(16 * self.zoom_level)
        content_x = x + padding
        content_y = y + padding
        
        # Priority badge
        if priority != 999:
            badge_width = int(40 * self.zoom_level)
            badge_height = int(24 * self.zoom_level)
            badge = RoundedCard(
                self.canvas, content_x, content_y, badge_width, badge_height, int(6 * self.zoom_level),
                fill=self.colors['accent'], outline=self.colors['accent']
            )
            self.canvas.create_text(
                content_x + badge_width // 2, content_y + badge_height // 2,
                text=f"P{priority}", font=('Segoe UI', int(9 * self.zoom_level), 'bold'),
                fill='#ffffff'
            )
            content_y += badge_height + int(12 * self.zoom_level)
        
        # Title (bold)
        title = task['title']
        title_length = int(35 / self.zoom_level)
        if len(title) > title_length:
            title = title[:title_length-3] + '...'
        
        self.canvas.create_text(
            content_x, content_y,
            text=title, font=('Segoe UI', int(13 * self.zoom_level), 'bold'),
            fill='#ffffff' if completed else self.colors['text'],
            anchor='w', width=self.card_width - 2*padding
        )
        content_y += int(30 * self.zoom_level)
        
        # Description
        if task.get('description'):
            desc = task['description']
            desc_length = int(60 / self.zoom_level)
            if len(desc) > desc_length:
                desc = desc[:desc_length-3] + '...'
            
            self.canvas.create_text(
                content_x, content_y,
                text=desc, font=('Segoe UI', int(9 * self.zoom_level)),
                fill='#cccccc' if completed else self.colors['text_dim'],
                anchor='w', width=self.card_width - 2*padding
            )
            content_y += int(25 * self.zoom_level)  # Reduced from 35
        else:
            content_y += int(10 * self.zoom_level)  # Reduced from 20
        
        # Divider line
        self.canvas.create_line(
            x + padding, content_y, x + self.card_width - padding, content_y,
            fill=self.colors['border'], width=1
        )
        content_y += int(8 * self.zoom_level)  # Reduced from 12
        
        # Action buttons row
        btn_y = content_y
        btn_size = int(28 * self.zoom_level)
        btn_spacing = int(8 * self.zoom_level)
        
        # Left buttons: Workflow (→) and Subtask (↓)
        btn_x = content_x
        
        # Workflow button
        btn_rect = self.canvas.create_rectangle(
            btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
            fill=self.colors['accent'], outline='', tags="button"
        )
        self.canvas.create_text(
            btn_x + btn_size // 2, btn_y + btn_size // 2,
            text="→", font=('Segoe UI', int(11 * self.zoom_level), 'bold'), fill='#ffffff'
        )
        self.button_regions[btn_rect] = lambda tid=task_id: self.add_workflow_sibling(tid)
        btn_x += btn_size + btn_spacing
        
        # Subtask button
        btn_rect = self.canvas.create_rectangle(
            btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
            fill=self.colors['warning'], outline='', tags="button"
        )
        self.canvas.create_text(
            btn_x + btn_size // 2, btn_y + btn_size // 2,
            text="↓", font=('Segoe UI', int(11 * self.zoom_level), 'bold'), fill='#ffffff'
        )
        self.button_regions[btn_rect] = lambda tid=task_id: self.add_subtask(tid)
        
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
            font=('Segoe UI', int(14 * self.zoom_level), 'bold'),
            fill='#ffffff' if completed else self.colors['success']
        )
        self.button_regions[btn_rect] = lambda tid=task_id, c=completed: self.toggle_done_status(
            tid, "Todo" if c else "Done ✓"
        )
        btn_x -= btn_size + btn_spacing
        
        # Delete button
        btn_rect = self.canvas.create_rectangle(
            btn_x, btn_y, btn_x + btn_size, btn_y + btn_size,
            fill='', outline='', tags="button"
        )
        self.canvas.create_text(
            btn_x + btn_size // 2, btn_y + btn_size // 2,
            text="×", font=('Segoe UI', int(16 * self.zoom_level), 'bold'), fill='#ff4444'
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
            text="✎", font=('Segoe UI', int(14 * self.zoom_level)), fill=self.colors['text_dim']
        )
        self.button_regions[btn_rect] = lambda tid=task_id: self.edit_task(tid)
        
        return self.card_height
    
    def get_subtasks(self, parent_id: str) -> List[str]:
        """Get ONLY direct subtasks (children below), not workflow siblings"""
        subtasks = []
        for tid, t in self.tasks.items():
            if t.get('parent_id') == parent_id and not t.get('workflow_sibling_of'):
                subtasks.append(tid)
        
        subtasks.sort(key=lambda tid: self.tasks[tid].get('priority', 999) or 999)
        return subtasks
    
    def get_workflow_siblings(self, task_id: str) -> List[str]:
        """Get workflow siblings (tasks that follow horizontally)"""
        siblings = []
        
        # Find direct workflow siblings (tasks that reference this task)
        for tid, t in self.tasks.items():
            if t.get('workflow_sibling_of') == task_id:
                siblings.append(tid)
        
        siblings.sort(key=lambda tid: self.tasks[tid].get('created', ''))
        
        # Recursively get siblings of siblings
        all_siblings = siblings.copy()
        for sibling_id in siblings:
            all_siblings.extend(self.get_workflow_siblings(sibling_id))
        
        return all_siblings
    
    def toggle_done_status(self, task_id: str, status: str):
        """Toggle task completion status"""
        if task_id in self.tasks:
            self.tasks[task_id]['completed'] = (status == "Done ✓")
            self.save_data()
            self.refresh_pipeline()
    
    def add_subtask(self, parent_id: str):
        """Add a subtask below the parent"""
        self.show_task_dialog(parent_id=parent_id, is_workflow=False)
    
    def add_workflow_sibling(self, sibling_of_id: str):
        """Add a workflow sibling next to this task"""
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
            title_text = "Create Workflow Task"
        elif parent_id:
            title_text = "Create Subtask"
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
        
        priority_frame = tk.Frame(fields, bg=self.colors['bg'])
        priority_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(priority_frame, text="Priority (number):", font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(0, 10))
        priority_entry = tk.Entry(priority_frame, font=('Segoe UI', 10),
                                 bg=self.colors['card_bg'], fg=self.colors['text'],
                                 insertbackground=self.colors['text'], relief=tk.FLAT, bd=2, width=10)
        priority_entry.insert(0, "999")
        priority_entry.pack(side=tk.LEFT)
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=20)
        
        def create_task():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("Warning", "Please enter a title")
                return
            try:
                priority_val = int(priority_entry.get().strip())
                if priority_val < 0:
                    priority_val = 0
            except ValueError:
                priority_val = 999
            
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
        
        priority_frame = tk.Frame(fields, bg=self.colors['bg'])
        priority_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(priority_frame, text="Priority:", font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(0, 10))
        priority_entry = tk.Entry(priority_frame, font=('Segoe UI', 10),
                                 bg=self.colors['card_bg'], fg=self.colors['text'],
                                 insertbackground=self.colors['text'], relief=tk.FLAT, bd=2, width=10)
        priority_entry.insert(0, str(task.get('priority', 999)))
        priority_entry.pack(side=tk.LEFT)
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=20)
        
        def save_changes():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("Warning", "Please enter a title")
                return
            try:
                priority_val = int(priority_entry.get().strip())
                if priority_val < 0:
                    priority_val = 0
            except ValueError:
                priority_val = 999
            
            self.tasks[task_id]['title'] = title
            self.tasks[task_id]['description'] = desc_text.get('1.0', 'end-1c').strip()
            self.tasks[task_id]['priority'] = priority_val
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
