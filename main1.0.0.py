#!/usr/bin/env python3
"""
Sticky Todo Pipeline - A minimalist task management app with nested subtasks
Features: Always-on-top window, pipeline view, infinite nesting, JSON storage, numeric priority
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid


class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Todo Pipeline")
        self.root.geometry("1000x700")
        
        # Make window always on top (sticky)
        self.root.attributes('-topmost', True)
        
        # Disable maximize button, allow minimize
        self.root.resizable(True, True)
        
        # Data file
        self.data_file = "todo_data.json"
        self.tasks = {}
        self.current_view = "todo"  # 'todo' or 'done'
        self.load_data()
        
        # Color scheme - Brutalist minimal with warm accents
        self.colors = {
            'bg': '#1a1a1a',
            'card_bg': '#242424',
            'card_hover': '#2a2a2a',
            'accent': '#ff6b35',
            'accent_dim': '#d45a2a',
            'text': '#e8e8e8',
            'text_dim': '#888888',
            'border': '#333333',
            'success': '#4caf50',
            'warning': '#ffa726',
            'line': '#444444',
            'tab_active': '#ff6b35',
            'tab_inactive': '#333333'
        }
        
        self.setup_ui()
        self.refresh_pipeline()
    
    def setup_ui(self):
        """Setup the main UI"""
        self.root.configure(bg=self.colors['bg'])
        
        # Custom style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.colors['bg'], height=60)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="PIPELINE",
            font=('Courier New', 24, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['accent']
        )
        title_label.pack(side=tk.LEFT)
        
        # Tab buttons
        tab_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        tab_frame.pack(side=tk.LEFT, padx=50)
        
        self.todo_tab_btn = tk.Button(
            tab_frame,
            text="TODO",
            font=('Courier New', 12, 'bold'),
            bg=self.colors['tab_active'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            activeforeground='#ffffff',
            relief=tk.FLAT,
            cursor='hand2',
            width=10,
            command=lambda: self.switch_view('todo')
        )
        self.todo_tab_btn.pack(side=tk.LEFT, padx=5)
        
        self.done_tab_btn = tk.Button(
            tab_frame,
            text="DONE",
            font=('Courier New', 12, 'bold'),
            bg=self.colors['tab_inactive'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            activeforeground=self.colors['text'],
            relief=tk.FLAT,
            cursor='hand2',
            width=10,
            command=lambda: self.switch_view('done')
        )
        self.done_tab_btn.pack(side=tk.LEFT, padx=5)
        
        # Add task button
        add_btn = tk.Button(
            header_frame,
            text="+ NEW TASK",
            font=('Courier New', 11, 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            activeforeground='#ffffff',
            relief=tk.FLAT,
            cursor='hand2',
            command=lambda: self.show_task_dialog(None)
        )
        add_btn.pack(side=tk.RIGHT, padx=5)
        
        # Minimize button
        min_btn = tk.Button(
            header_frame,
            text="─",
            font=('Courier New', 16, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            activebackground=self.colors['card_hover'],
            activeforeground=self.colors['text'],
            relief=tk.FLAT,
            cursor='hand2',
            width=3,
            command=self.root.iconify
        )
        min_btn.pack(side=tk.RIGHT, padx=5)
        
        # Main pipeline container with scrollbars
        container = tk.Frame(self.root, bg=self.colors['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Canvas with both vertical and horizontal scrollbars
        self.canvas = tk.Canvas(
            container,
            bg=self.colors['bg'],
            highlightthickness=0
        )
        
        # Vertical scrollbar
        v_scrollbar = tk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview,
            bg=self.colors['card_bg'],
            troughcolor=self.colors['bg'],
            activebackground=self.colors['accent']
        )
        
        # Horizontal scrollbar
        h_scrollbar = tk.Scrollbar(
            container,
            orient="horizontal",
            command=self.canvas.xview,
            bg=self.colors['card_bg'],
            troughcolor=self.colors['bg'],
            activebackground=self.colors['accent']
        )
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors['bg'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and canvas
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Mouse wheel scrolling (vertical)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # Horizontal scrolling with Shift + Mouse wheel
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_h_mousewheel)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling (vertical)"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_h_mousewheel(self, event):
        """Handle horizontal mouse wheel scrolling (Shift + wheel)"""
        self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")
    
    def switch_view(self, view: str):
        """Switch between todo and done views"""
        self.current_view = view
        
        # Update tab button styles
        if view == 'todo':
            self.todo_tab_btn.configure(bg=self.colors['tab_active'], fg='#ffffff')
            self.done_tab_btn.configure(bg=self.colors['tab_inactive'], fg=self.colors['text_dim'])
        else:
            self.done_tab_btn.configure(bg=self.colors['tab_active'], fg='#ffffff')
            self.todo_tab_btn.configure(bg=self.colors['tab_inactive'], fg=self.colors['text_dim'])
        
        self.refresh_pipeline()
    
    def load_data(self):
        """Load tasks from JSON file"""
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
        """Save tasks to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {e}")
    
    def refresh_pipeline(self):
        """Refresh the pipeline view"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Get root tasks (tasks without parent) based on current view
        if self.current_view == 'todo':
            root_tasks = [
                task_id for task_id, task in self.tasks.items()
                if task.get('parent_id') is None and not task.get('completed', False)
            ]
        else:  # done view
            root_tasks = [
                task_id for task_id, task in self.tasks.items()
                if task.get('parent_id') is None and task.get('completed', False)
            ]
        
        # Filter to only first task in each workflow chain
        # (tasks that are not workflow siblings of an earlier task)
        tasks_to_render = []
        
        for task_id in root_tasks:
            task = self.tasks[task_id]
            current_created = task.get('created', '')
            
            # Check if any other root task was created before this one (same parent = None)
            is_first_in_chain = True
            for other_id in root_tasks:
                if other_id != task_id:
                    other_created = self.tasks[other_id].get('created', '')
                    if other_created < current_created:
                        # Found an earlier task with same parent, so this is not first
                        is_first_in_chain = False
                        break
            
            if is_first_in_chain:
                tasks_to_render.append(task_id)
        
        # Sort by creation time (earliest first)
        tasks_to_render.sort(key=lambda tid: self.tasks[tid].get('created', ''))
        
        if not tasks_to_render:
            # Empty state
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
            for task_id in tasks_to_render:
                self.render_task_card(self.scrollable_frame, task_id, level=0)
    
    def render_task_card(self, parent, task_id: str, level: int = 0, rendered_tasks: set = None):
        """Render a task in flowchart style"""
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
            if idx > 0:
                connector = tk.Label(task_row, text=" - ", font=('Courier New', 9), 
                                   bg=self.colors['bg'], fg=self.colors['line'])
                connector.pack(side=tk.LEFT)
            
            # Task text
            priority_text = f"[{task_priority}]" if task_priority != 999 else ""
            task_text = f"{priority_text} {chain_task['title']}" if priority_text else chain_task['title']
            
            if is_completed:
                task_text = f"✓ {task_text}"
            
            task_lbl = tk.Label(
                task_row,
                text=task_text,
                font=('Courier New', 10, 'overstrike' if is_completed else 'normal'),
                bg=self.colors['bg'],
                fg=self.colors['text_dim'] if is_completed else self.colors['text']
            )
            task_lbl.pack(side=tk.LEFT, padx=(0, 5))
            
            # Action buttons
            actions = tk.Frame(task_row, bg=self.colors['bg'])
            actions.pack(side=tk.LEFT)
            
            # + → button (add workflow)
            btn_workflow = tk.Label(actions, text="+→", font=('Courier New', 8), bg=self.colors['bg'], 
                                    fg=self.colors['accent'], cursor='hand2')
            btn_workflow.pack(side=tk.LEFT, padx=1)
            btn_workflow.bind('<Button-1>', lambda e, tid=chain_task_id: 
                            self.show_task_dialog(self.tasks[tid].get('parent_id'), insert_after=tid))
            
            # + ↓ button (add subtask)
            btn_subtask = tk.Label(actions, text="+↓", font=('Courier New', 8), bg=self.colors['bg'], 
                                   fg=self.colors['warning'], cursor='hand2')
            btn_subtask.pack(side=tk.LEFT, padx=1)
            btn_subtask.bind('<Button-1>', lambda e, tid=chain_task_id: self.show_task_dialog(tid))
            
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
                    self.render_task_card(task_column, subtask_id, level=level + 1, rendered_tasks=rendered_tasks)
    
    def get_subtasks(self, parent_id: str) -> List[str]:
        """Get all direct subtasks of a task"""
        subtasks = [
            task_id for task_id, task in self.tasks.items()
            if task.get('parent_id') == parent_id
        ]
        # Sort subtasks by priority too
        subtasks.sort(key=lambda tid: self.tasks[tid].get('priority', 999) if self.tasks[tid].get('priority') is not None else 999)
        return subtasks
    
    def get_workflow_siblings(self, task_id: str) -> List[str]:
        """Get workflow siblings (tasks with same parent created after this one)"""
        task = self.tasks.get(task_id)
        if not task:
            return []
        
        parent_id = task.get('parent_id')
        current_created = task.get('created', '')
        
        # Get all siblings with same parent
        siblings = [
            tid for tid, t in self.tasks.items()
            if t.get('parent_id') == parent_id and tid != task_id
        ]
        
        # Filter to only those created after current task
        later_siblings = [
            tid for tid in siblings
            if self.tasks[tid].get('created', '') > current_created
        ]
        
        # Sort by creation time
        later_siblings.sort(key=lambda tid: self.tasks[tid].get('created', ''))
        
        return later_siblings
    
    def toggle_done_status(self, task_id: str, status: str):
        """Toggle task done status from dropdown"""
        if task_id in self.tasks:
            self.tasks[task_id]['completed'] = (status == "Done ✓")
            self.save_data()
            self.refresh_pipeline()
    
    def move_to_done(self, task_id: str):
        """Move a task to done column"""
        if task_id in self.tasks:
            self.tasks[task_id]['completed'] = True
            self.save_data()
            self.refresh_pipeline()
    
    def move_to_todo(self, task_id: str):
        """Move a task back to todo column"""
        if task_id in self.tasks:
            self.tasks[task_id]['completed'] = False
            self.save_data()
            self.refresh_pipeline()
    
    def show_task_dialog(self, parent_id: Optional[str] = None, insert_after: Optional[str] = None):
        """Show dialog to create a new task"""
        is_workflow = insert_after is not None
        
        dialog = tk.Toplevel(self.root)
        dialog.title("New Workflow" if is_workflow else ("New Task" if parent_id is None else "New Subtask"))
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Title
        tk.Label(
            dialog,
            text="Create New Workflow" if is_workflow else ("Create New Task" if parent_id is None else "Create Subtask"),
            font=('Courier New', 14, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=(20, 10))
        
        # Input fields
        fields_frame = tk.Frame(dialog, bg=self.colors['bg'])
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        tk.Label(
            fields_frame,
            text="Title:",
            font=('Courier New', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(anchor='w')
        
        title_entry = tk.Entry(
            fields_frame,
            font=('Courier New', 11),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            bd=2
        )
        title_entry.pack(fill=tk.X, pady=(5, 15), ipady=5)
        title_entry.focus()
        
        tk.Label(
            fields_frame,
            text="Description (optional):",
            font=('Courier New', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(anchor='w')
        
        desc_text = tk.Text(
            fields_frame,
            font=('Courier New', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            bd=2,
            height=3,
            wrap=tk.WORD
        )
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        # Priority selection (numeric input)
        priority_frame = tk.Frame(fields_frame, bg=self.colors['bg'])
        priority_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            priority_frame,
            text="Priority (lower number = higher priority):",
            font=('Courier New', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        priority_entry = tk.Entry(
            priority_frame,
            font=('Courier New', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            bd=2,
            width=10
        )
        priority_entry.insert(0, "999")  # Default no priority
        priority_entry.pack(side=tk.LEFT)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=20)
        
        def create_task():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("Warning", "Please enter a title")
                return
            
            # Validate priority
            try:
                priority_val = int(priority_entry.get().strip())
                if priority_val < 0:
                    priority_val = 0
            except ValueError:
                priority_val = 999
            
            task_id = str(uuid.uuid4())
            created_date = datetime.now().isoformat()
            description = desc_text.get('1.0', 'end-1c').strip()
            
            self.tasks[task_id] = {
                'id': task_id,
                'title': title,
                'description': description,
                'completed': False,
                'parent_id': parent_id,
                'created': created_date,
                'priority': priority_val
            }
            
            self.save_data()
            self.refresh_pipeline()
            dialog.destroy()
        
        cancel_btn = tk.Button(
            btn_frame,
            text="CANCEL",
            font=('Courier New', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            activeforeground=self.colors['text'],
            relief=tk.FLAT,
            cursor='hand2',
            command=dialog.destroy,
            width=12
        )
        cancel_btn.pack(side=tk.LEFT)
        
        create_btn = tk.Button(
            btn_frame,
            text="CREATE",
            font=('Courier New', 10, 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            activeforeground='#ffffff',
            relief=tk.FLAT,
            cursor='hand2',
            command=create_task,
            width=12
        )
        create_btn.pack(side=tk.RIGHT)
        
        # Bind Enter key
        dialog.bind('<Return>', lambda e: create_task())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def edit_task(self, task_id: str):
        """Edit an existing task"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Task")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)
        
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Title
        tk.Label(
            dialog,
            text="Edit Task",
            font=('Courier New', 14, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(pady=(20, 10))
        
        # Input fields
        fields_frame = tk.Frame(dialog, bg=self.colors['bg'])
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        tk.Label(
            fields_frame,
            text="Title:",
            font=('Courier New', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(anchor='w')
        
        title_entry = tk.Entry(
            fields_frame,
            font=('Courier New', 11),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            bd=2
        )
        title_entry.insert(0, task['title'])
        title_entry.pack(fill=tk.X, pady=(5, 15), ipady=5)
        title_entry.focus()
        
        tk.Label(
            fields_frame,
            text="Description (optional):",
            font=('Courier New', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(anchor='w')
        
        desc_text = tk.Text(
            fields_frame,
            font=('Courier New', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            bd=2,
            height=3,
            wrap=tk.WORD
        )
        desc_text.insert('1.0', task.get('description', ''))
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        
        # Priority selection (numeric input)
        priority_frame = tk.Frame(fields_frame, bg=self.colors['bg'])
        priority_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            priority_frame,
            text="Priority (lower number = higher priority):",
            font=('Courier New', 10),
            bg=self.colors['bg'],
            fg=self.colors['text']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        priority_entry = tk.Entry(
            priority_frame,
            font=('Courier New', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            bd=2,
            width=10
        )
        current_priority = task.get('priority', 999)
        if current_priority is None:
            current_priority = 999
        priority_entry.insert(0, str(current_priority))
        priority_entry.pack(side=tk.LEFT)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=20)
        
        def save_changes():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("Warning", "Please enter a title")
                return
            
            # Validate priority
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
        
        cancel_btn = tk.Button(
            btn_frame,
            text="CANCEL",
            font=('Courier New', 10),
            bg=self.colors['card_bg'],
            fg=self.colors['text_dim'],
            activebackground=self.colors['card_hover'],
            activeforeground=self.colors['text'],
            relief=tk.FLAT,
            cursor='hand2',
            command=dialog.destroy,
            width=12
        )
        cancel_btn.pack(side=tk.LEFT)
        
        save_btn = tk.Button(
            btn_frame,
            text="SAVE",
            font=('Courier New', 10, 'bold'),
            bg=self.colors['accent'],
            fg='#ffffff',
            activebackground=self.colors['accent_dim'],
            activeforeground='#ffffff',
            relief=tk.FLAT,
            cursor='hand2',
            command=save_changes,
            width=12
        )
        save_btn.pack(side=tk.RIGHT)
        
        dialog.bind('<Return>', lambda e: save_changes())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def delete_task(self, task_id: str):
        """Delete a task and all its subtasks"""
        # Check if task has subtasks
        subtasks = self.get_subtasks(task_id)
        
        msg = "Are you sure you want to delete this task?"
        if subtasks:
            msg += f"\n\nThis will also delete {len(subtasks)} subtask(s)."
        
        if messagebox.askyesno("Confirm Delete", msg):
            # Delete task and all subtasks recursively
            self._delete_task_recursive(task_id)
            self.save_data()
            self.refresh_pipeline()
    
    def _delete_task_recursive(self, task_id: str):
        """Recursively delete a task and all its subtasks"""
        # Get subtasks first
        subtasks = self.get_subtasks(task_id)
        
        # Delete all subtasks
        for subtask_id in subtasks:
            self._delete_task_recursive(subtask_id)
        
        # Delete the task itself
        if task_id in self.tasks:
            del self.tasks[task_id]


def main():
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
