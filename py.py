import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time
import threading
import random
import json
import os
import re
from datetime import datetime

class Process:
    """Simulates an OS process with PID, state, and resource usage"""
    def __init__(self, pid, name, memory_req, priority=1):
        self.pid = pid
        self.name = name
        self.state = "READY"  # READY, RUNNING, BLOCKED, TERMINATED
        self.memory_req = memory_req  # in MB
        self.memory_address = None
        self.priority = priority
        self.cpu_time = 0
        self.creation_time = time.time()
        self.message_queue = []  # For inter-process communication
        
    def __str__(self):
        return f"Process {self.pid}: {self.name} ({self.state})"
    
    def send_message(self, source_pid, message):
        """Add a message to the process's message queue"""
        self.message_queue.append({"source": source_pid, "message": message, "time": time.time()})
        
    def get_messages(self):
        """Get all messages in the queue"""
        return self.message_queue
    
    def clear_messages(self):
        """Clear all messages"""
        self.message_queue = []

class MemoryManager:
    """Manages memory allocation using a simple segmentation approach"""
    def __init__(self, total_memory=1024):  # 1024 MB total memory
        self.total_memory = total_memory
        self.available_memory = total_memory
        # Memory blocks: (start_address, size, is_free)
        self.memory_blocks = [(0, total_memory, True)]
        
    def allocate(self, size):
        """First-fit memory allocation algorithm"""
        for i, (start, block_size, is_free) in enumerate(self.memory_blocks):
            if is_free and block_size >= size:
                # Allocate memory
                self.memory_blocks[i] = (start, size, False)
                
                # If there's remaining space, create a new free block
                if block_size > size:
                    self.memory_blocks.insert(i+1, (start + size, block_size - size, True))
                
                self.available_memory -= size
                return start
        return None  # No suitable memory block found

    def deallocate(self, address):
        """Free memory at the given address and merge adjacent free blocks"""
        for i, (start, size, is_free) in enumerate(self.memory_blocks):
            if start == address and not is_free:
                # Mark block as free
                self.memory_blocks[i] = (start, size, True)
                self.available_memory += size
                
                # Merge with adjacent free blocks
                self._merge_free_blocks()
                return True
        return False

    def _merge_free_blocks(self):
        """Merge adjacent free memory blocks"""
        i = 0
        while i < len(self.memory_blocks) - 1:
            curr_start, curr_size, curr_free = self.memory_blocks[i]
            next_start, next_size, next_free = self.memory_blocks[i+1]
            
            if curr_free and next_free:
                # Merge blocks
                self.memory_blocks[i] = (curr_start, curr_size + next_size, True)
                self.memory_blocks.pop(i+1)
            else:
                i += 1
                
    def get_fragmentation_percent(self):
        """Calculate memory fragmentation percentage"""
        free_blocks = sum(1 for _, _, is_free in self.memory_blocks if is_free)
        if free_blocks <= 1:
            return 0
        
        total_blocks = len(self.memory_blocks)
        # More free blocks means more fragmentation
        return (free_blocks - 1) / max(total_blocks, 1) * 100

class FileSystem:
    """Enhanced file system implementation with permissions and metadata"""
    def __init__(self):
        self.root = {
            "type": "dir", 
            "name": "root", 
            "children": {}, 
            "created": time.time(),
            "owner": "system",
            "permissions": "rwxr-xr-x"  # Owner: rwx, Group: r-x, Others: r-x
        }
        self.current_path = ["root"]
        self.current_user = "user"
        
        # Create initial directories
        self._mkdir("home")
        self._mkdir("system")
        self._mkdir("applications")
        self._mkdir("home/user")
        
        # Add some initial files
        self._write_file("system/welcome.txt", "Welcome to SimpleOS!")
        self._write_file("system/about.txt", "SimpleOS - A Python OS Simulation")
        
        # System log file
        self._write_file("system/logs/system.log", "--- System Log ---\n")
        
        # Add demo files for search
        self._write_file("home/user/document1.txt", "This is a sample document with important information.")
        self._write_file("home/user/document2.txt", "Another document containing data about projects.")
        self._write_file("home/user/notes.txt", "Remember to complete the OS simulation project.")
        
    def _get_current_dir(self):
        """Get the current directory object"""
        current = self.root
        for dir_name in self.current_path[1:]:  # Skip 'root'
            current = current["children"][dir_name]
        return current

    def _mkdir(self, path, permissions="rwxr-xr-x"):
        """Create a directory at the specified path with permissions"""
        if path.startswith("/"):
            path = path[1:]  # Remove leading slash
            
        parts = path.split("/")
        current = self.root
        
        for i, part in enumerate(parts):
            if part == "":
                continue
                
            if part not in current["children"]:
                current["children"][part] = {
                    "type": "dir",
                    "name": part,
                    "children": {},
                    "created": time.time(),
                    "owner": self.current_user,
                    "permissions": permissions
                }
            
            current = current["children"][part]

    def _write_file(self, path, content, permissions="rw-r--r--"):
        """Write content to a file at the specified path with permissions"""
        if path.startswith("/"):
            path = path[1:]
            
        parts = path.split("/")
        filename = parts[-1]
        directory = "/".join(parts[:-1])
        
        # Ensure directory exists
        if directory:
            self._mkdir(directory)
        
        # Navigate to the directory
        current = self.root
        for part in directory.split("/"):
            if part == "":
                continue
            current = current["children"][part]
        
        # Create or update the file
        current["children"][filename] = {
            "type": "file",
            "name": filename,
            "content": content,
            "size": len(content),
            "created": time.time(),
            "modified": time.time(),
            "owner": self.current_user,
            "permissions": permissions
        }

    def list_dir(self, path=None):
        """List contents of a directory"""
        if path is None:
            # Use current directory
            current = self._get_current_dir()
        else:
            # Navigate to specified path
            if path.startswith("/"):
                path = path[1:]
                
            if not path:
                current = self.root
            else:
                current = self.root
                for part in path.split("/"):
                    if part == "":
                        continue
                    if part not in current["children"]:
                        return []
                    current = current["children"][part]
        
        if current["type"] != "dir":
            return []
            
        return [
            {"name": name, "type": item["type"], 
             "size": item.get("size", 0) if item["type"] == "file" else 0,
             "owner": item.get("owner", "unknown"),
             "permissions": item.get("permissions", "----------")}
            for name, item in current["children"].items()
        ]

    def read_file(self, path):
        """Read content from a file"""
        if path.startswith("/"):
            path = path[1:]
            
        parts = path.split("/")
        filename = parts[-1]
        directory = "/".join(parts[:-1])
        
        # Navigate to the directory
        current = self.root
        for part in directory.split("/"):
            if part == "":
                continue
            if part not in current["children"]:
                return None
            current = current["children"][part]
        
        # Read the file
        if filename not in current["children"]:
            return None
            
        file_obj = current["children"][filename]
        if file_obj["type"] != "file":
            return None
            
        return file_obj["content"]
    
    def delete_file(self, path):
        """Delete a file or directory"""
        if path.startswith("/"):
            path = path[1:]
            
        parts = path.split("/")
        name = parts[-1]
        directory = "/".join(parts[:-1])
        
        # Navigate to the parent directory
        current = self.root
        for part in directory.split("/"):
            if part == "":
                continue
            if part not in current["children"]:
                return False
            current = current["children"][part]
        
        # Delete the file or directory
        if name in current["children"]:
            # Check permissions (simplified - owner can delete)
            file_obj = current["children"][name]
            if file_obj["owner"] != self.current_user and self.current_user != "system":
                return False
            
            # Perform deletion
            del current["children"][name]
            return True
            
        return False
    
    def search_files(self, query, path=""):
        """Search for files matching a query string"""
        results = []
        
        def _search_recursive(current_path, node):
            if node["type"] == "file" and query.lower() in node["name"].lower() or \
               (node["type"] == "file" and query.lower() in node.get("content", "").lower()):
                results.append({
                    "path": current_path + "/" + node["name"],
                    "type": "file",
                    "size": node.get("size", 0)
                })
            
            if node["type"] == "dir":
                for name, child in node["children"].items():
                    _search_recursive(current_path + "/" + node["name"] if current_path else "/" + node["name"], child)
        
        # Start search from specified path or root
        if not path:
            _search_recursive("", self.root)
        else:
            if path.startswith("/"):
                path = path[1:]
                
            current = self.root
            current_path = ""
            
            for part in path.split("/"):
                if part == "":
                    continue
                if part not in current["children"]:
                    return []
                current = current["children"][part]
                current_path = current_path + "/" + part if current_path else part
                
            _search_recursive(current_path, current)
            
        return results
    
    def append_to_log(self, log_content):
        """Append content to the system log file"""
        # Get current log content
        log_path = "system/logs/system.log"
        current_log = self.read_file(log_path) or "--- System Log ---\n"
        
        # Add timestamp and new content
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        updated_log = current_log + timestamp + log_content + "\n"
        
        # Write back to log file
        self._write_file(log_path, updated_log)

class ProcessScheduler:
    """Implements process scheduling algorithms with priority support"""
    def __init__(self, memory_manager):
        self.processes = {}
        self.ready_queue = []
        self.running_process = None
        self.next_pid = 1000
        self.memory_manager = memory_manager
        self.time_quantum = 2  # For round-robin scheduling
        self.scheduling_algorithm = "priority"  # "round-robin" or "priority"
        
    def create_process(self, name, memory_req, priority=1):
        """Create a new process and add it to the ready queue"""
        pid = self.next_pid
        self.next_pid += 1
        
        process = Process(pid, name, memory_req, priority)
        
        # Allocate memory
        memory_address = self.memory_manager.allocate(memory_req)
        if memory_address is None:
            return None  # Not enough memory
            
        process.memory_address = memory_address
        self.processes[pid] = process
        self.ready_queue.append(pid)
        
        return pid

    def terminate_process(self, pid):
        """Terminate a process and free its resources"""
        if pid not in self.processes:
            return False
            
        process = self.processes[pid]
        
        # Free memory
        if process.memory_address is not None:
            self.memory_manager.deallocate(process.memory_address)
            
        # Update process state
        process.state = "TERMINATED"
        
        # Remove from queues
        if pid in self.ready_queue:
            self.ready_queue.remove(pid)
        if self.running_process == pid:
            self.running_process = None
            
        return True

    def schedule_next_process(self):
        """Schedule the next process using selected algorithm"""
        if self.running_process is not None:
            # Put current process back in the queue
            current = self.processes[self.running_process]
            current.state = "READY"
            self.ready_queue.append(self.running_process)
            self.running_process = None
            
        if not self.ready_queue:
            return None
        
        if self.scheduling_algorithm == "round-robin":
            # Round Robin - Just take the next process in queue
            next_pid = self.ready_queue.pop(0)
        else:  # Priority scheduling
            # Find highest priority process
            highest_priority = 0
            highest_index = 0
            
            for i, pid in enumerate(self.ready_queue):
                process = self.processes[pid]
                if process.priority > highest_priority:
                    highest_priority = process.priority
                    highest_index = i
                    
            next_pid = self.ready_queue.pop(highest_index)
            
        next_process = self.processes[next_pid]
        next_process.state = "RUNNING"
        self.running_process = next_pid
        
        return next_pid
    
    def set_scheduling_algorithm(self, algorithm):
        """Set the scheduling algorithm to use"""
        if algorithm in ["round-robin", "priority"]:
            self.scheduling_algorithm = algorithm
            return True
        return False

    def get_process_info(self, pid):
        """Get information about a process"""
        if pid not in self.processes:
            return None
        return self.processes[pid]

    def get_all_processes(self):
        """Get all processes"""
        return self.processes
    
    def send_message(self, source_pid, target_pid, message):
        """Send a message from one process to another"""
        if source_pid not in self.processes or target_pid not in self.processes:
            return False
        
        source = self.processes[source_pid]
        target = self.processes[target_pid]
        
        if source.state == "TERMINATED" or target.state == "TERMINATED":
            return False
            
        target.send_message(source_pid, message)
        return True

class SimpleOS:
    """Main OS class that integrates all components"""
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleOS")
        self.root.geometry("800x600")
        
        # Theme support
        self.current_theme = "light"
        self.themes = {
            "light": {
                "bg": "#f0f0f0", 
                "fg": "#000000",
                "accent": "#007bff",
                "terminal_bg": "#ffffff",
                "terminal_fg": "#000000"
            },
            "dark": {
                "bg": "#2d2d2d", 
                "fg": "#ffffff",
                "accent": "#00bfff",
                "terminal_bg": "#000000",
                "terminal_fg": "#00ff00"
            }
        }
        
        # Initialize OS components
        self.memory_manager = MemoryManager(1024)  # 1GB RAM
        self.process_scheduler = ProcessScheduler(self.memory_manager)
        self.file_system = FileSystem()
        
        # Notification system
        self.notifications = []
        
        # Create system processes
        self.process_scheduler.create_process("System", 128, 10)
        self.process_scheduler.create_process("WindowManager", 64, 8)
        
        # Set up the UI
        self.setup_ui()
        
        # Start the OS scheduler
        self.scheduler_thread = threading.Thread(target=self.os_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # Log system start
        self.log_system_event("System started")

    def setup_ui(self):
        """Set up the main UI components"""
        # Apply theme to root
        self.apply_theme()
        
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Desktop tab
        self.desktop_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.desktop_frame, text="Desktop")
        
        # Process Manager tab
        self.process_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.process_frame, text="Process Manager")
        
        # File Explorer tab
        self.file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_frame, text="File Explorer")
        
        # Memory Monitor tab
        self.memory_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.memory_frame, text="Memory Monitor")
        
        # Terminal tab
        self.terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.terminal_frame, text="Terminal")
        
        # System Logs tab
        self.logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_frame, text="System Logs")
        
        # Set up each tab
        self.setup_desktop()
        self.setup_process_manager()
        self.setup_file_explorer()
        self.setup_memory_monitor()
        self.setup_terminal()
        self.setup_system_logs()
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="SimpleOS running...", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Notification area
        self.notification_frame = ttk.Frame(self.root)
        self.notification_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Clock update
        self.update_clock()

    def apply_theme(self):
        """Apply the current theme to the UI"""
        theme = self.themes[self.current_theme]
        
        # Configure root window
        self.root.configure(bg=theme["bg"])
        
        # Configure ttk styles
        style = ttk.Style()
        style.configure("TFrame", background=theme["bg"])
        style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        style.configure("TButton", background=theme["accent"])
        style.configure("TNotebook", background=theme["bg"])
        style.configure("TNotebook.Tab", background=theme["bg"], foreground=theme["fg"])
        
        # Apply to existing widgets
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Canvas):
                widget.configure(bg=theme["bg"])

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()
        
        # Update terminal colors if it exists
        if hasattr(self, "terminal_output"):
            theme = self.themes[self.current_theme]
            self.terminal_output.configure(
                bg=theme["terminal_bg"], 
                fg=theme["terminal_fg"]
            )
            
        self.show_notification("Theme changed to " + self.current_theme)

    def setup_desktop(self):
        """Set up the desktop with application icons"""
        # Desktop layout
        self.desktop_canvas = tk.Canvas(self.desktop_frame, bg=self.themes[self.current_theme]["bg"])
        self.desktop_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Application icons
        self.create_desktop_icon("Text Editor", 50, 50, self.open_text_editor)
        self.create_desktop_icon("Calculator", 150, 50, self.open_calculator)
        self.create_desktop_icon("Clock", 250, 50, self.open_clock)
        self.create_desktop_icon("Search", 350, 50, self.open_search)
        
        # Theme toggle
        self.create_desktop_icon("Toggle Theme", 450, 50, self.toggle_theme)
        
        # Desktop context menu
        self.desktop_menu = tk.Menu(self.root, tearoff=0)
        self.desktop_menu.add_command(label="New Folder", command=self.create_new_folder)
        self.desktop_menu.add_command(label="Refresh", command=lambda: self.update_status("Desktop refreshed"))
        self.desktop_menu.add_separator()
        self.desktop_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        
        self.desktop_canvas.bind("<Button-3>", self.show_desktop_menu)

    def create_desktop_icon(self, name, x, y, command):
        """Create an icon on the desktop"""
        icon_frame = tk.Frame(self.desktop_canvas, width=60, height=80, bg=self.themes[self.current_theme]["bg"])
        icon_id = self.desktop_canvas.create_window(x, y, window=icon_frame, anchor=tk.NW)
        
        # Icon representation (a colored rectangle)
        icon = tk.Canvas(icon_frame, width=40, height=40, bg=self.themes[self.current_theme]["bg"], highlightthickness=0)
        icon.create_rectangle(5, 5, 35, 35, fill=self.get_app_color(name), outline="black")
        icon.pack(pady=(5, 0))
        
        # Icon label
        label = tk.Label(icon_frame, text=name, bg=self.themes[self.current_theme]["bg"], fg=self.themes[self.current_theme]["fg"], wraplength=60)
        label.pack()
        
        # Bind click events
        icon.bind("<Button-1>", lambda e: command())
        label.bind("<Button-1>", lambda e: command())

    def get_app_color(self, app_name):
        """Return a color based on the application name"""
        colors = {
            "Text Editor": "#8cc",
            "Calculator": "#c8c",
            "Clock": "#cc8",
            "File Explorer": "#8c8",
            "Process Manager": "#c88",
            "Search": "#88c",
            "Toggle Theme": "#ccc"
        }
        return colors.get(app_name, "#ccc")

    def show_desktop_menu(self, event):
        """Show the desktop context menu"""
        self.desktop_menu.post(event.x_root, event.y_root)

    def create_new_folder(self):
        """Create a new folder on the desktop"""
        folder_name = simpledialog.askstring("New Folder", "Enter folder name:")
        if folder_name:
            self.file_system._mkdir(f"home/user/{folder_name}")
            self.update_status(f"Created folder: {folder_name}")
            self.refresh_file_explorer()
            self.log_system_event(f"Created folder: home/user/{folder_name}")

    def setup_process_manager(self):
        """Set up the process manager tab"""
        # Controls frame
        controls_frame = ttk.Frame(self.process_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="New Process", command=self.create_new_process).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Terminate", command=self.terminate_selected_process).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_process_list).pack(side=tk.LEFT, padx=5)
        
        # Scheduling algorithm selection
        ttk.Label(controls_frame, text="Scheduling:").pack(side=tk.LEFT, padx=(20, 5))
        self.scheduling_var = tk.StringVar(value="priority")
        ttk.Radiobutton(controls_frame, text="Priority", variable=self.scheduling_var, value="priority", 
                       command=self.change_scheduling).pack(side=tk.LEFT)
        ttk.Radiobutton(controls_frame, text="Round Robin", variable=self.scheduling_var, value="round-robin", 
                       command=self.change_scheduling).pack(side=tk.LEFT)
        
        # Process list
        columns = ("PID", "Name", "State", "Memory", "Priority", "CPU Time")
        self.process_tree = ttk.Treeview(self.process_frame, columns=columns, show="headings")
        
        for col in columns:
            self.process_tree.heading(col, text=col)
            width = 80 if col != "Name" else 150
            self.process_tree.column(col, width=width)
        
        self.process_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Process communication frame
        comm_frame = ttk.LabelFrame(self.process_frame, text="Inter-Process Communication")
        comm_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(comm_frame, text="From PID:").grid(row=0, column=0, padx=5, pady=5)
        self.source_pid_var = tk.StringVar()
        source_pid_entry = ttk.Entry(comm_frame, textvariable=self.source_pid_var, width=10)
        source_pid_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(comm_frame, text="To PID:").grid(row=0, column=2, padx=5, pady=5)
        self.target_pid_var = tk.StringVar()
        target_pid_entry = ttk.Entry(comm_frame, textvariable=self.target_pid_var, width=10)
        target_pid_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(comm_frame, text="Message:").grid(row=0, column=4, padx=5, pady=5)
        self.message_var = tk.StringVar()
        message_entry = ttk.Entry(comm_frame, textvariable=self.message_var, width=30)
        message_entry.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Button(comm_frame, text="Send Message", command=self.send_process_message).grid(row=0, column=6, padx=5, pady=5)
        
        # Message log
        ttk.Label(comm_frame, text="Message Log:").grid(row=1, column=0, columnspan=7, padx=5, pady=(10, 0), sticky=tk.W)
        self.message_log = tk.Text(comm_frame, height=5, width=80)
        self.message_log.grid(row=2, column=0, columnspan=7, padx=5, pady=5)
        
        # Initial process list
        self.refresh_process_list()
        
    def change_scheduling(self):
        """Change the scheduling algorithm"""
        algorithm = self.scheduling_var.get()
        if self.process_scheduler.set_scheduling_algorithm(algorithm):
            self.update_status(f"Scheduling algorithm changed to {algorithm}")
            self.log_system_event(f"Scheduling algorithm changed to {algorithm}")
        else:
            messagebox.showerror("Error", "Invalid scheduling algorithm")

    def send_process_message(self):
        """Send a message from one process to another"""
        try:
            source_pid = int(self.source_pid_var.get())
            target_pid = int(self.target_pid_var.get())
            message = self.message_var.get()
            
            if not message:
                messagebox.showerror("Error", "Message cannot be empty")
                return
                
            if self.process_scheduler.send_message(source_pid, target_pid, message):
                self.update_status(f"Message sent from PID {source_pid} to PID {target_pid}")
                self.refresh_message_log()
                self.log_system_event(f"IPC: Message sent from PID {source_pid} to PID {target_pid}")
            else:
                messagebox.showerror("Error", "Failed to send message. Check PIDs.")
        except ValueError:
            messagebox.showerror("Error", "Invalid PID")

    def refresh_message_log(self):
        """Refresh the message log display"""
        self.message_log.delete(1.0, tk.END)
        
        # Show messages from all processes
        for pid, process in self.process_scheduler.get_all_processes().items():
            messages = process.get_messages()
            if messages:
                self.message_log.insert(tk.END, f"--- Messages for PID {pid} ({process.name}) ---\n")
                for msg in messages:
                    source_pid = msg["source"]
                    source_name = self.process_scheduler.get_process_info(source_pid).name
                    timestamp = datetime.fromtimestamp(msg["time"]).strftime("%H:%M:%S")
                    self.message_log.insert(tk.END, f"[{timestamp}] From {source_name} (PID {source_pid}): {msg['message']}\n")

    def create_new_process(self):
        """Create a new user process"""
        name = simpledialog.askstring("New Process", "Process Name:")
        if not name:
            return
            
        memory = simpledialog.askinteger("Memory Requirement", "Memory (MB):", minvalue=1, maxvalue=512)
        if not memory:
            return
            
        priority = simpledialog.askinteger("Priority", "Priority (1-10):", minvalue=1, maxvalue=10)
        if not priority:
            priority = 5
            
        pid = self.process_scheduler.create_process(name, memory, priority)
        if pid:
            self.update_status(f"Created process: {name} (PID: {pid})")
            self.refresh_process_list()
            self.log_system_event(f"Created process: {name} (PID: {pid})")
            self.show_notification(f"New process created: {name}")
        else:
            messagebox.showerror("Error", "Not enough memory to create process")

    def terminate_selected_process(self):
        """Terminate the selected process"""
        selected = self.process_tree.selection()
        if not selected:
            return
            
        pid = int(self.process_tree.item(selected[0])["values"][0])
        process = self.process_scheduler.get_process_info(pid)
        
        if process and process.name not in ["System", "WindowManager"]:
            if self.process_scheduler.terminate_process(pid):
                self.update_status(f"Terminated process: {process.name} (PID: {pid})")
                self.refresh_process_list()
                self.log_system_event(f"Terminated process: {process.name} (PID: {pid})")
            else:
                messagebox.showerror("Error", "Failed to terminate process")
        else:
            messagebox.showerror("Error", "Cannot terminate system processes")

    def refresh_process_list(self):
        """Refresh the process list display"""
        # Clear current items
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
            
        # Add all processes
        for pid, process in self.process_scheduler.get_all_processes().items():
            if process.state != "TERMINATED":
                self.process_tree.insert("", tk.END, values=(
                    pid,
                    process.name,
                    process.state,
                    f"{process.memory_req} MB",
                    process.priority,
                    f"{process.cpu_time:.1f}s"
                ))
        
        # Also refresh message log
        self.refresh_message_log()

    def setup_file_explorer(self):
        """Set up the file explorer tab with enhanced features"""
        # Path and controls frame
        path_frame = ttk.Frame(self.file_frame)
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(path_frame, text="Path:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar(value="/root")
        ttk.Entry(path_frame, textvariable=self.path_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Go", command=self.navigate_to_path).pack(side=tk.LEFT, padx=5)
        
        # File operations frame
        ops_frame = ttk.Frame(self.file_frame)
        ops_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(ops_frame, text="New File", command=self.create_new_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(ops_frame, text="New Folder", command=self.create_new_folder_in_explorer).pack(side=tk.LEFT, padx=5)
        ttk.Button(ops_frame, text="Delete", command=self.delete_selected_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(ops_frame, text="Open", command=self.open_selected_file).pack(side=tk.LEFT, padx=5)
        
        # Search frame
        search_frame = ttk.Frame(self.file_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="Search Files", command=self.search_files).pack(side=tk.LEFT, padx=5)
        
        # File list
        columns = ("Name", "Type", "Size", "Owner", "Permissions")
        self.file_tree = ttk.Treeview(self.file_frame, columns=columns, show="headings")
        
        column_widths = {
            "Name": 200,
            "Type": 80,
            "Size": 80,
            "Owner": 100,
            "Permissions": 100
        }
        
        for col in columns:
            self.file_tree.heading(col, text=col)
            self.file_tree.column(col, width=column_widths.get(col, 100))
        
        self.file_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_tree.bind("<Double-1>", self.on_file_double_click)
        
        # Initial file list
        self.refresh_file_explorer()

    def navigate_to_path(self):
        """Navigate to the specified path"""
        path = self.path_var.get()
        if not path.startswith("/"):
            path = "/" + path
        self.path_var.set(path)
        self.refresh_file_explorer()

    def refresh_file_explorer(self):
        """Refresh the file explorer display"""
        # Clear current items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        # Get path without leading slash for the file system
        path = self.path_var.get()
        if path.startswith("/"):
            path = path[1:]
            
        # List directory contents
        contents = self.file_system.list_dir(path)
        
        # Add all files and directories
        for item in contents:
            item_type = "Directory" if item["type"] == "dir" else "File"
            size = f"{item['size']} bytes" if item["type"] == "file" else ""
            
            self.file_tree.insert("", tk.END, values=(
                item["name"],
                item_type,
                size,
                item["owner"],
                item["permissions"]
            ))

    def on_file_double_click(self, event):
        """Handle double-click on file or directory"""
        selected = self.file_tree.selection()
        if not selected:
            return
            
        item_name = self.file_tree.item(selected[0])["values"][0]
        item_type = self.file_tree.item(selected[0])["values"][1]
        
        current_path = self.path_var.get()
        if not current_path.endswith("/"):
            current_path += "/"
            
        if item_type == "Directory":
            # Navigate to directory
            new_path = current_path + item_name
            self.path_var.set(new_path)
            self.refresh_file_explorer()
        else:
            # Open file
            file_path = current_path[1:] + item_name if current_path.startswith("/") else current_path + item_name
            content = self.file_system.read_file(file_path)
            if content is not None:
                self.open_text_editor(file_path, content)

    def create_new_file(self):
        """Create a new file in the current directory"""
        file_name = simpledialog.askstring("New File", "File Name:")
        if not file_name:
            return
            
        current_path = self.path_var.get()
        if not current_path.startswith("/"):
            current_path = "/" + current_path
        if not current_path.endswith("/"):
            current_path += "/"
            
        file_path = current_path[1:] + file_name
        self.file_system._write_file(file_path, "")
        self.update_status(f"Created file: {file_name}")
        self.refresh_file_explorer()
        self.log_system_event(f"Created file: {file_path}")
        
        # Open the new file
        self.open_text_editor(file_path, "")

    def create_new_folder_in_explorer(self):
        """Create a new folder in the current directory"""
        folder_name = simpledialog.askstring("New Folder", "Folder Name:")
        if not folder_name:
            return
            
        current_path = self.path_var.get()
        if not current_path.startswith("/"):
            current_path = "/" + current_path
        if not current_path.endswith("/"):
            current_path += "/"
            
        folder_path = current_path[1:] + folder_name
        self.file_system._mkdir(folder_path)
        self.update_status(f"Created folder: {folder_name}")
        self.refresh_file_explorer()
        self.log_system_event(f"Created folder: {folder_path}")

    def delete_selected_file(self):
        """Delete the selected file or directory"""
        selected = self.file_tree.selection()
        if not selected:
            return
            
        item_name = self.file_tree.item(selected[0])["values"][0]
        
        # Confirmation dialog
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{item_name}'?"):
            return
            
        current_path = self.path_var.get()
        if not current_path.startswith("/"):
            current_path = "/" + current_path
        if not current_path.endswith("/"):
            current_path += "/"
            
        file_path = current_path[1:] + item_name
        
        if self.file_system.delete_file(file_path):
            self.update_status(f"Deleted: {item_name}")
            self.refresh_file_explorer()
            self.log_system_event(f"Deleted: {file_path}")
        else:
            messagebox.showerror("Error", f"Could not delete '{item_name}'. Permission denied or not found.")

    def search_files(self):
        """Search for files based on the search query"""
        query = self.search_var.get()
        if not query:
            messagebox.showinfo("Search", "Please enter a search term")
            return
            
        # Get path for search scope
        path = self.path_var.get()
        if path.startswith("/"):
            path = path[1:]
            
        results = self.file_system.search_files(query, path)
        
        if not results:
            messagebox.showinfo("Search Results", "No files found matching your query")
            return
            
        # Show results in a new window
        results_window = tk.Toplevel(self.root)
        results_window.title(f"Search Results for '{query}'")
        results_window.geometry("600x400")
        
        ttk.Label(results_window, text=f"Found {len(results)} results for '{query}'").pack(padx=10, pady=10)
        
        # Results list
        columns = ("Path", "Type", "Size")
        results_tree = ttk.Treeview(results_window, columns=columns, show="headings")
        
        for col in columns:
            results_tree.heading(col, text=col)
            width = 100 if col == "Size" else 400 if col == "Path" else 100
            results_tree.column(col, width=width)
        
        results_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add results to the tree
        for item in results:
            results_tree.insert("", tk.END, values=(
                item["path"],
                "Directory" if item["type"] == "dir" else "File",
                f"{item['size']} bytes" if item["type"] == "file" else ""
            ))
            
        # Double-click to open file or navigate to directory
        def on_result_double_click(event):
            selected = results_tree.selection()
            if not selected:
                return
                
            path = results_tree.item(selected[0])["values"][0]
            item_type = results_tree.item(selected[0])["values"][1]
            
            if item_type == "Directory":
                # Navigate to directory in file explorer
                self.path_var.set("/" + path)
                self.refresh_file_explorer()
                results_window.destroy()
            else:
                # Open file
                content = self.file_system.read_file(path)
                if content is not None:
                    self.open_text_editor(path, content)
                    results_window.destroy()
                    
        results_tree.bind("<Double-1>", on_result_double_click)

    def open_search(self):
        """Open the search application"""
        # Create a new process for the search
        pid = self.process_scheduler.create_process("Search", 16, 4)
        
        if pid:
            # Create a new window for search
            search_window = tk.Toplevel(self.root)
            search_window.title("File Search")
            search_window.geometry("500x300")
            
            # Search controls
            controls_frame = ttk.Frame(search_window)
            controls_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Label(controls_frame, text="Search Term:").grid(row=0, column=0, padx=5, pady=5)
            search_var = tk.StringVar()
            search_entry = ttk.Entry(controls_frame, textvariable=search_var, width=30)
            search_entry.grid(row=0, column=1, padx=5, pady=5)
            search_entry.focus()
            
            ttk.Label(controls_frame, text="Location:").grid(row=1, column=0, padx=5, pady=5)
            location_var = tk.StringVar(value="/")
            location_entry = ttk.Entry(controls_frame, textvariable=location_var, width=30)
            location_entry.grid(row=1, column=1, padx=5, pady=5)
            
            # Results display
            ttk.Label(search_window, text="Results:").pack(anchor=tk.W, padx=10)
            
            results_text = tk.Text(search_window, height=10, width=60)
            results_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Search function
            def perform_search():
                query = search_var.get()
                path = location_var.get()
                
                if not query:
                    messagebox.showinfo("Search", "Please enter a search term")
                    return
                    
                if path.startswith("/"):
                    path = path[1:]
                    
                results = self.file_system.search_files(query, path)
                
                # Clear previous results
                results_text.delete(1.0, tk.END)
                
                if not results:
                    results_text.insert(tk.END, "No files found matching your query.\n")
                    return
                    
                results_text.insert(tk.END, f"Found {len(results)} results for '{query}':\n\n")
                
                for item in results:
                    results_text.insert(tk.END, f"- {item['path']} ({item['type']})\n")
                    
                self.log_system_event(f"Search performed for '{query}' in '{path}'. Found {len(results)} results.")
            
            # Search button
            ttk.Button(controls_frame, text="Search", command=perform_search).grid(row=0, column=2, rowspan=2, padx=10, pady=5)
            
            # Bind Enter key to search
            search_entry.bind("<Return>", lambda e: perform_search())
            
            # Handle window close
            search_window.protocol("WM_DELETE_WINDOW", lambda: self.close_application(search_window, pid))

    def open_selected_file(self):
        """Open the selected file"""
        selected = self.file_tree.selection()
        if not selected:
            return
            
        item_name = self.file_tree.item(selected[0])["values"][0]
        item_type = self.file_tree.item(selected[0])["values"][1]
        
        if item_type != "File":
            return
            
        current_path = self.path_var.get()
        if not current_path.startswith("/"):
            current_path = "/" + current_path
        if not current_path.endswith("/"):
            current_path += "/"
            
        file_path = current_path[1:] + item_name
        content = self.file_system.read_file(file_path)
        
        if content is not None:
            self.open_text_editor(file_path, content)

    def setup_memory_monitor(self):
        """Set up the memory monitor tab"""
        # Memory usage frame
        usage_frame = ttk.LabelFrame(self.memory_frame, text="Memory Usage")
        usage_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Memory usage bar
        self.memory_usage_var = tk.DoubleVar(value=0)
        ttk.Label(usage_frame, text="Used Memory:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.memory_usage_bar = ttk.Progressbar(usage_frame, variable=self.memory_usage_var, maximum=100)
        self.memory_usage_bar.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.memory_usage_label = ttk.Label(usage_frame, text="0 MB / 1024 MB")
        self.memory_usage_label.grid(row=0, column=2, padx=5, pady=5)
        
        # Memory allocation table
        ttk.Label(usage_frame, text="Memory Allocation Table:").grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
        
        columns = ("Address", "Size", "Status", "Process")
        self.memory_tree = ttk.Treeview(usage_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.memory_tree.heading(col, text=col)
            width = 100
            self.memory_tree.column(col, width=width)
        
        self.memory_tree.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.NSEW)
        
        # Configure grid
        usage_frame.columnconfigure(1, weight=1)
        usage_frame.rowconfigure(2, weight=1)
        
        # Memory stats frame
        stats_frame = ttk.LabelFrame(self.memory_frame, text="Memory Statistics")
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(stats_frame, text="Total Memory:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(stats_frame, text="1024 MB").grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(stats_frame, text="Free Memory:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.free_memory_label = ttk.Label(stats_frame, text="1024 MB")
        self.free_memory_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(stats_frame, text="Fragmentation:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.fragmentation_label = ttk.Label(stats_frame, text="0%")
        self.fragmentation_label.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Refresh button
        ttk.Button(self.memory_frame, text="Refresh", command=self.refresh_memory_monitor).pack(pady=10)
        
        # Initial memory monitor
        self.refresh_memory_monitor()

    def refresh_memory_monitor(self):
        """Refresh the memory monitor display"""
        # Update memory usage
        used_memory = self.memory_manager.total_memory - self.memory_manager.available_memory
        usage_percent = (used_memory / self.memory_manager.total_memory) * 100
        
        self.memory_usage_var.set(usage_percent)
        self.memory_usage_label.config(text=f"{used_memory} MB / {self.memory_manager.total_memory} MB")
        self.free_memory_label.config(text=f"{self.memory_manager.available_memory} MB")
        
        # Calculate fragmentation
        fragmentation = self.memory_manager.get_fragmentation_percent()
        self.fragmentation_label.config(text=f"{fragmentation:.1f}%")
        
        # Clear current items in memory table
        for item in self.memory_tree.get_children():
            self.memory_tree.delete(item)
            
        # Add all memory blocks
        process_map = {}
        for pid, process in self.process_scheduler.get_all_processes().items():
            if process.memory_address is not None:
                process_map[process.memory_address] = process.name
                
        for start, size, is_free in self.memory_manager.memory_blocks:
            status = "Free" if is_free else "Allocated"
            process_name = process_map.get(start, "-") if not is_free else "-"
            
            self.memory_tree.insert("", tk.END, values=(
                f"0x{start:08x}",
                f"{size} MB",
                status,
                process_name
            ))

    def setup_terminal(self):
        """Set up the terminal tab with enhanced features"""
        # Terminal output
        terminal_frame = ttk.Frame(self.terminal_frame)
        terminal_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        theme = self.themes[self.current_theme]
        self.terminal_output = tk.Text(terminal_frame, bg=theme["terminal_bg"], fg=theme["terminal_fg"], font=("Courier", 10))
        self.terminal_output.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        self.terminal_output.insert(tk.END, "SimpleOS Terminal v1.0\n")
        self.terminal_output.insert(tk.END, "Type 'help' for a list of commands\n\n")
        self.terminal_output.insert(tk.END, "$ ")
        
        # Terminal input with autocomplete
        input_frame = ttk.Frame(terminal_frame)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(input_frame, text="$").pack(side=tk.LEFT, padx=5)
        self.terminal_input = ttk.Entry(input_frame)
        self.terminal_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.terminal_input.bind("<Return>", self.process_terminal_command)
        self.terminal_input.bind("<Tab>", self.autocomplete_command)
        
        # Command history
        self.command_history = []
        self.history_index = -1
        self.terminal_input.bind("<Up>", self.previous_command)
        self.terminal_input.bind("<Down>", self.next_command)
        
        # Autocomplete dropdown
        self.autocomplete_listbox = tk.Listbox(input_frame, height=5, width=30)
        
        # List of available commands for autocomplete
        self.available_commands = [
            "help", "ls", "cd", "cat", "ps", "kill", "mem", "clear", 
            "mkdir", "touch", "rm", "search", "cp", "mv", "theme", "logs"
        ]

    def autocomplete_command(self, event):
        """Autocomplete terminal commands"""
        current_input = self.terminal_input.get()
        
        if not current_input:
            return "break"  # Prevent default tab behavior
            
        # Find matching commands
        matches = [cmd for cmd in self.available_commands if cmd.startswith(current_input)]
        
        if len(matches) == 1:
            # One match, complete the command
            self.terminal_input.delete(0, tk.END)
            self.terminal_input.insert(0, matches[0] + " ")
        elif len(matches) > 1:
            # Multiple matches, show dropdown
            self.autocomplete_listbox.delete(0, tk.END)
            for match in matches:
                self.autocomplete_listbox.insert(tk.END, match)
                
            # Calculate position for dropdown
            x, y, width, height = self.terminal_input.bbox("insert")
            
            # Position listbox below input
            self.autocomplete_listbox.place(
                x=x, 
                y=y + height + 2,
                width=150
            )
            
            # Bind click on listbox item
            def on_listbox_click(event):
                if self.autocomplete_listbox.curselection():
                    index = self.autocomplete_listbox.curselection()[0]
                    value = self.autocomplete_listbox.get(index)
                    self.terminal_input.delete(0, tk.END)
                    self.terminal_input.insert(0, value + " ")
                    self.autocomplete_listbox.place_forget()
                    
            self.autocomplete_listbox.bind("<ButtonRelease-1>", on_listbox_click)
            
            # Bind escape to hide dropdown
            def hide_dropdown(event):
                self.autocomplete_listbox.place_forget()
                
            self.terminal_input.bind("<Escape>", hide_dropdown)
            
        return "break"  # Prevent default tab behavior

    def previous_command(self, event):
        """Navigate to previous command in history"""
        if self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.terminal_input.delete(0, tk.END)
                self.terminal_input.insert(0, self.command_history[-(self.history_index+1)])
        return "break"  # Prevent default behavior

    def next_command(self, event):
        """Navigate to next command in history"""
        if self.command_history:
            if self.history_index > 0:
                self.history_index -= 1
                self.terminal_input.delete(0, tk.END)
                self.terminal_input.insert(0, self.command_history[-(self.history_index+1)])
            elif self.history_index == 0:
                self.history_index = -1
                self.terminal_input.delete(0, tk.END)
        return "break"  # Prevent default behavior

    def process_terminal_command(self, event):
        """Process a terminal command with enhanced features"""
        command = self.terminal_input.get()
        self.terminal_input.delete(0, tk.END)
        
        # Add command to history if not empty
        if command and (not self.command_history or command != self.command_history[-1]):
            self.command_history.append(command)
            self.history_index = -1
            
        # Hide autocomplete dropdown
        self.autocomplete_listbox.place_forget()
        
        # Add command to output
        self.terminal_output.insert(tk.END, f"{command}\n")
        
        # Process command
        if command == "help":
            self.terminal_output.insert(tk.END, "Available commands:\n")
            self.terminal_output.insert(tk.END, "  help - Show this help\n")
            self.terminal_output.insert(tk.END, "  ls [path] - List directory contents\n")
            self.terminal_output.insert(tk.END, "  cd <path> - Change directory\n")
            self.terminal_output.insert(tk.END, "  cat <file> - Display file contents\n")
            self.terminal_output.insert(tk.END, "  ps - List processes\n")
            self.terminal_output.insert(tk.END, "  kill <pid> - Terminate a process\n")
            self.terminal_output.insert(tk.END, "  mem - Show memory usage\n")
            self.terminal_output.insert(tk.END, "  clear - Clear terminal\n")
            self.terminal_output.insert(tk.END, "  mkdir <path> - Create directory\n")
            self.terminal_output.insert(tk.END, "  touch <file> - Create empty file\n")
            self.terminal_output.insert(tk.END, "  rm <path> - Delete file or directory\n")
            self.terminal_output.insert(tk.END, "  search <term> - Search for files\n")
            self.terminal_output.insert(tk.END, "  theme - Toggle theme\n")
            self.terminal_output.insert(tk.END, "  logs - View system logs\n")
        elif command.startswith("ls"):
            parts = command.split()
            path = parts[1] if len(parts) > 1 else None
            
            contents = self.file_system.list_dir(path)
            for item in contents:
                item_type = "d" if item["type"] == "dir" else "-"
                size = f"{item['size']} bytes" if item["type"] == "file" else ""
                self.terminal_output.insert(tk.END, f"{item_type} {item['permissions']} {item['owner']:8} {item['name']:20} {size}\n")
        elif command.startswith("cd"):
            parts = command.split()
            if len(parts) < 2:
                self.terminal_output.insert(tk.END, "Usage: cd <path>\n")
            else:
                path = parts[1]
                # Handle relative paths
                current_path = self.path_var.get()
                if not path.startswith("/"):
                    if current_path.endswith("/"):
                        path = current_path + path
                    else:
                        path = current_path + "/" + path
                
                # Set path in file explorer
                try:
                    self.path_var.set(path)
                    self.refresh_file_explorer()  # This will fail if path doesn't exist
                    self.terminal_output.insert(tk.END, f"Changed directory to {path}\n")
                except:
                    self.terminal_output.insert(tk.END, f"Directory not found: {path}\n")
        elif command.startswith("cat"):
            parts = command.split()
            if len(parts) < 2:
                self.terminal_output.insert(tk.END, "Usage: cat <file>\n")
            else:
                file_path = parts[1]
                content = self.file_system.read_file(file_path)
                if content is not None:
                    self.terminal_output.insert(tk.END, f"{content}\n")
                else:
                    self.terminal_output.insert(tk.END, f"File not found: {file_path}\n")
        elif command == "ps":
            self.terminal_output.insert(tk.END, f"{'PID':6} {'NAME':15} {'STATE':10} {'MEM':8} {'PRI':5} CPU\n")
            for pid, process in self.process_scheduler.get_all_processes().items():
                if process.state != "TERMINATED":
                    self.terminal_output.insert(tk.END, f"{pid:6} {process.name:15} {process.state:10} {process.memory_req:4} MB {process.priority:5} {process.cpu_time:.1f}s\n")
        elif command.startswith("kill"):
            parts = command.split()
            if len(parts) < 2:
                self.terminal_output.insert(tk.END, "Usage: kill <pid>\n")
            else:
                try:
                    pid = int(parts[1])
                    process = self.process_scheduler.get_process_info(pid)
                    if process and process.name not in ["System", "WindowManager"]:
                        if self.process_scheduler.terminate_process(pid):
                            self.terminal_output.insert(tk.END, f"Process {pid} terminated\n")
                            self.refresh_process_list()
                            self.log_system_event(f"Process {pid} terminated via terminal")
                        else:
                            self.terminal_output.insert(tk.END, f"Failed to terminate process {pid}\n")
                    else:
                        self.terminal_output.insert(tk.END, "Cannot terminate system processes\n")
                except ValueError:
                    self.terminal_output.insert(tk.END, "Invalid PID\n")
        elif command == "mem":
            used_memory = self.memory_manager.total_memory - self.memory_manager.available_memory
            self.terminal_output.insert(tk.END, f"Memory Usage: {used_memory} MB / {self.memory_manager.total_memory} MB\n")
            self.terminal_output.insert(tk.END, f"Free Memory: {self.memory_manager.available_memory} MB\n")
            
            fragmentation = self.memory_manager.get_fragmentation_percent()
            self.terminal_output.insert(tk.END, f"Memory Fragmentation: {fragmentation:.1f}%\n")
            
            self.terminal_output.insert(tk.END, "Memory Blocks:\n")
            for start, size, is_free in self.memory_manager.memory_blocks:
                status = "Free" if is_free else "Allocated"
                self.terminal_output.insert(tk.END, f"  0x{start:08x} - {size} MB - {status}\n")
        elif command == "clear":
            self.terminal_output.delete(1.0, tk.END)
        elif command.startswith("mkdir"):
            parts = command.split()
            if len(parts) < 2:
                self.terminal_output.insert(tk.END, "Usage: mkdir <path>\n")
            else:
                path = parts[1]
                self.file_system._mkdir(path)
                self.terminal_output.insert(tk.END, f"Created directory: {path}\n")
                self.refresh_file_explorer()
                self.log_system_event(f"Created directory: {path}")
        elif command.startswith("touch"):
            parts = command.split()
            if len(parts) < 2:
                self.terminal_output.insert(tk.END, "Usage: touch <file>\n")
            else:
                path = parts[1]
                self.file_system._write_file(path, "")
                self.terminal_output.insert(tk.END, f"Created file: {path}\n")
                self.refresh_file_explorer()
                self.log_system_event(f"Created file: {path}")
        elif command.startswith("rm"):
            parts = command.split()
            if len(parts) < 2:
                self.terminal_output.insert(tk.END, "Usage: rm <path>\n")
            else:
                path = parts[1]
                if self.file_system.delete_file(path):
                    self.terminal_output.insert(tk.END, f"Deleted: {path}\n")
                    self.refresh_file_explorer()
                    self.log_system_event(f"Deleted: {path}")
                else:
                    self.terminal_output.insert(tk.END, f"Could not delete '{path}'. Permission denied or not found.\n")
        elif command.startswith("search"):
            parts = command.split()
            if len(parts) < 2:
                self.terminal_output.insert(tk.END, "Usage: search <term>\n")
            else:
                query = parts[1]
                path = parts[2] if len(parts) > 2 else ""
                
                results = self.file_system.search_files(query, path)
                
                if not results:
                    self.terminal_output.insert(tk.END, "No files found matching your query\n")
                else:
                    self.terminal_output.insert(tk.END, f"Found {len(results)} results for '{query}':\n")
                    for item in results:
                        self.terminal_output.insert(tk.END, f"- {item['path']} ({item['type']})\n")
        elif command == "theme":
            self.toggle_theme()
            self.terminal_output.insert(tk.END, f"Theme changed to {self.current_theme}\n")
        elif command == "logs":
            log_content = self.file_system.read_file("system/logs/system.log")
            if log_content:
                self.terminal_output.insert(tk.END, f"{log_content}\n")
            else:
                self.terminal_output.insert(tk.END, "No system logs found\n")
        else:
            self.terminal_output.insert(tk.END, f"Command not found: {command}\n")
        
        # Add new prompt
        self.terminal_output.insert(tk.END, "$ ")
        self.terminal_output.see(tk.END)

    def setup_system_logs(self):
        """Set up the system logs tab"""
        # Log content
        log_frame = ttk.Frame(self.logs_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_content = tk.Text(log_frame, font=("Courier", 10))
        self.log_content.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        # Controls
        controls_frame = ttk.Frame(self.logs_frame)
        controls_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_system_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Clear Logs", command=self.clear_system_logs).pack(side=tk.LEFT, padx=5)
        
        # Initial log display
        self.refresh_system_logs()

    def refresh_system_logs(self):
        """Refresh the system logs display"""
        log_content = self.file_system.read_file("system/logs/system.log")
        
        self.log_content.delete(1.0, tk.END)
        if log_content:
            self.log_content.insert(tk.END, log_content)
        else:
            self.log_content.insert(tk.END, "No system logs found")

    def clear_system_logs(self):
        """Clear the system logs"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all system logs?"):
            self.file_system._write_file("system/logs/system.log", "--- System Log ---\n")
            self.refresh_system_logs()
            self.update_status("System logs cleared")

    def log_system_event(self, message):
        """Log a system event to the system log file"""
        self.file_system.append_to_log(message)
        
        # Refresh logs if the tab is visible
        if self.notebook.index(self.notebook.select()) == 5:  # System Logs tab
            self.refresh_system_logs()

    def show_notification(self, message, duration=3000):
        """Show a notification message"""
        notification_id = len(self.notifications)
        
        # Create notification frame
        notification = ttk.Frame(self.notification_frame, style="Notification.TFrame")
        notification.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Notification content
        ttk.Label(notification, text=message).pack(side=tk.LEFT, padx=10, pady=5)
        
        # Close button
        close_button = ttk.Button(notification, text="×", width=2, 
                                command=lambda: self.close_notification(notification))
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Add to notifications list
        self.notifications.append((notification_id, notification))
        
        # Auto-close after duration
        self.root.after(duration, lambda: self.close_notification(notification))
        
        return notification_id

    def close_notification(self, notification):
        """Close a notification"""
        # Remove from list
        self.notifications = [(nid, n) for nid, n in self.notifications if n != notification]
        
        # Destroy widget
        notification.destroy()

    def open_text_editor(self, file_path=None, content=None):
        """Open the text editor application"""
        # Create a new process for the text editor
        pid = self.process_scheduler.create_process("TextEditor", 32, 5)
        
        if pid:
            # Create a new window for the text editor
            editor_window = tk.Toplevel(self.root)
            editor_window.title(f"Text Editor - {file_path if file_path else 'Untitled'}")
            editor_window.geometry("600x400")
            
            # Text area
            text_area = tk.Text(editor_window)
            text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Insert content if provided
            if content:
                text_area.insert(tk.END, content)
            
            # Menu bar
            menu_bar = tk.Menu(editor_window)
            
            # File menu
            file_menu = tk.Menu(menu_bar, tearoff=0)
            file_menu.add_command(label="Save", command=lambda: self.save_file(file_path, text_area.get(1.0, tk.END)))
            file_menu.add_command(label="Save As", command=lambda: self.save_file_as(text_area.get(1.0, tk.END)))
            file_menu.add_separator()
            file_menu.add_command(label="Close", command=lambda: self.close_application(editor_window, pid))
            
            menu_bar.add_cascade(label="File", menu=file_menu)
            editor_window.config(menu=menu_bar)
            
            # Handle window close
            editor_window.protocol("WM_DELETE_WINDOW", lambda: self.close_application(editor_window, pid))
            
            # Log the event
            self.log_system_event(f"Opened text editor for file: {file_path}")

    def save_file(self, file_path, content):
        """Save file content"""
        if not file_path:
            self.save_file_as(content)
            return
            
        self.file_system._write_file(file_path, content)
        self.update_status(f"Saved file: {file_path}")
        self.refresh_file_explorer()
        self.log_system_event(f"Saved file: {file_path}")

    def save_file_as(self, content):
        """Save file with a new name"""
        file_name = simpledialog.askstring("Save As", "File Name:")
        if not file_name:
            return
            
        current_path = self.path_var.get()
        if not current_path.startswith("/"):
            current_path = "/" + current_path
        if not current_path.endswith("/"):
            current_path += "/"
            
        file_path = current_path[1:] + file_name
        self.file_system._write_file(file_path, content)
        self.update_status(f"Saved file as: {file_path}")
        self.refresh_file_explorer()
        self.log_system_event(f"Saved file as: {file_path}")

    def open_calculator(self):
        """Open the calculator application"""
        # Create a new process for the calculator
        pid = self.process_scheduler.create_process("Calculator", 16, 3)
        
        if pid:
            # Create a new window for the calculator
            calc_window = tk.Toplevel(self.root)
            calc_window.title("Calculator")
            calc_window.geometry("300x400")
            
            # Display
            display_var = tk.StringVar(value="0")
            display = ttk.Entry(calc_window, textvariable=display_var, font=("Arial", 20), justify=tk.RIGHT)
            display.pack(fill=tk.X, padx=10, pady=10)
            
            # Buttons frame
            buttons_frame = ttk.Frame(calc_window)
            buttons_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Calculator state
            calc_state = {"operand1": None, "operator": None, "reset_display": False}
            
            # Button click handler
            def button_click(value):
                current = display_var.get()
                
                if value in "0123456789.":
                    if current == "0" or calc_state["reset_display"]:
                        display_var.set(value)
                        calc_state["reset_display"] = False
                    else:
                        display_var.set(current + value)
                elif value in "+-*/":
                    calc_state["operand1"] = float(current)
                    calc_state["operator"] = value
                    calc_state["reset_display"] = True
                elif value == "=":
                    if calc_state["operand1"] is not None and calc_state["operator"] is not None:
                        operand2 = float(current)
                        result = 0
                        
                        if calc_state["operator"] == "+":
                            result = calc_state["operand1"] + operand2
                        elif calc_state["operator"] == "-":
                            result = calc_state["operand1"] - operand2
                        elif calc_state["operator"] == "*":
                            result = calc_state["operand1"] * operand2
                        elif calc_state["operator"] == "/":
                            if operand2 != 0:
                                result = calc_state["operand1"] / operand2
                            else:
                                result = "Error"
                        
                        display_var.set(str(result))
                        calc_state["operand1"] = None
                        calc_state["operator"] = None
                        calc_state["reset_display"] = True
                elif value == "C":
                    display_var.set("0")
                    calc_state["operand1"] = None
                    calc_state["operator"] = None
                    calc_state["reset_display"] = False
            
            # Create calculator buttons
            buttons = [
                "7", "8", "9", "/",
                "4", "5", "6", "*",
                "1", "2", "3", "-",
                "0", ".", "=", "+"
            ]
            
            row, col = 0, 0
            for button in buttons:
                ttk.Button(buttons_frame, text=button, width=5, 
                          command=lambda b=button: button_click(b)).grid(row=row, column=col, padx=5, pady=5)
                col += 1
                if col > 3:
                    col = 0
                    row += 1
            
            # Clear button
            ttk.Button(buttons_frame, text="C", width=5, 
                      command=lambda: button_click("C")).grid(row=row, column=0, columnspan=4, padx=5, pady=5, sticky=tk.EW)
            
            # Handle window close
            calc_window.protocol("WM_DELETE_WINDOW", lambda: self.close_application(calc_window, pid))
            
            # Log the event
            self.log_system_event("Calculator application opened")

    def open_clock(self):
        """Open the clock application"""
        # Create a new process for the clock
        pid = self.process_scheduler.create_process("Clock", 8, 2)
        
        if pid:
            # Create a new window for the clock
            clock_window = tk.Toplevel(self.root)
            clock_window.title("Clock")
            clock_window.geometry("300x200")
            
            # Clock display
            time_var = tk.StringVar()
            date_var = tk.StringVar()
            
            time_label = ttk.Label(clock_window, textvariable=time_var, font=("Arial", 36))
            time_label.pack(pady=(20, 5))
            
            date_label = ttk.Label(clock_window, textvariable=date_var, font=("Arial", 14))
            date_label.pack(pady=5)
            
            # Update clock function
            def update_clock_display():
                if clock_window.winfo_exists():
                    now = datetime.now()
                    time_var.set(now.strftime("%H:%M:%S"))
                    date_var.set(now.strftime("%A, %B %d, %Y"))
                    clock_window.after(1000, update_clock_display)
            
            # Start clock update
            update_clock_display()
            
            # Handle window close
            clock_window.protocol("WM_DELETE_WINDOW", lambda: self.close_application(clock_window, pid))
            
            # Log the event
            self.log_system_event("Clock application opened")

    def close_application(self, window, pid):
        """Close an application window and terminate its process"""
        window.destroy()
        self.process_scheduler.terminate_process(pid)
        self.refresh_process_list()
        self.log_system_event(f"Application closed (PID: {pid})")

    def update_status(self, message):
        """Update the status bar message"""
        self.status_bar.config(text=message)

    def update_clock(self):
        """Update the clock in the status bar"""
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        self.status_bar.config(text=f"SimpleOS running... {time_str}")
        self.root.after(1000, self.update_clock)

    def os_scheduler(self):
        """OS scheduler thread that simulates process scheduling"""
        while True:
            # Schedule next process
            pid = self.process_scheduler.schedule_next_process()
            
            if pid is not None:
                # Simulate CPU time for the process
                process = self.process_scheduler.get_process_info(pid)
                if process:
                    # Simulate CPU usage
                    process.cpu_time += self.process_scheduler.time_quantum
                    
                    # Sleep to simulate time quantum
                    time.sleep(0.1)  # Reduced for responsiveness
            else:
                # No process to run, just wait
                time.sleep(0.1)

# Run the OS
if __name__ == "__main__":
    root = tk.Tk()
    os_instance = SimpleOS(root)
    root.mainloop()