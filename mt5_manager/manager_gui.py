import customtkinter as ctk
from tkinter import filedialog, messagebox
import webbrowser
import threading
import time
from docker_service import DockerService

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AnimatedButton(ctk.CTkButton):
    """Button with hover animation effect"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_height = kwargs.get('height', 36)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, e):
        self.configure(height=self.default_height + 2)
    
    def _on_leave(self, e):
        self.configure(height=self.default_height)

class LoadingSpinner(ctk.CTkFrame):
    """Animated loading indicator"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(fg_color="transparent")
        
        self.label = ctk.CTkLabel(self, text="⟳ Loading...", 
                                 font=ctk.CTkFont(size=14))
        self.label.pack(pady=20)
        
        self.is_spinning = False
        self.rotation = 0
        
    def start(self):
        self.is_spinning = True
        self._spin()
    
    def stop(self):
        self.is_spinning = False
    
    def _spin(self):
        if not self.is_spinning:
            return
        
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.rotation = (self.rotation + 1) % len(spinners)
        self.label.configure(text=f"{spinners[self.rotation]} Loading...")
        self.after(80, self._spin)

class StatusBadge(ctk.CTkLabel):
    """Animated status badge"""
    def __init__(self, parent, status, **kwargs):
        self.status = status.lower()
        
        if "running" in self.status:
            text = "● Running"
            color = "#2CC985"
        elif "paused" in self.status:
            text = "⏸ Paused"
            color = "#FFA500"
        else:
            text = "■ Stopped"
            color = "#FF4444"
        
        super().__init__(parent, text=text, text_color=color, 
                        font=ctk.CTkFont(size=12, weight="bold"),
                        **kwargs)
        
        if "running" in self.status:
            self._pulse()
    
    def _pulse(self):
        if not self.winfo_exists():
            return
        current = self.cget("text")
        if current.startswith("●"):
            self.configure(text="○ Running")
        else:
            self.configure(text="● Running")
        self.after(1000, self._pulse)

class LogViewerWindow(ctk.CTkToplevel):
    def __init__(self, master, docker_service, container_id, container_name):
        super().__init__(master)
        
        self.docker_service = docker_service
        self.container_id = container_id
        self.container_name = container_name
        self.current_log_type = "experts"
        
        self.title(f"📋 Logs: {container_name}")
        self.geometry("900x600")
        
        # Fade in animation
        self.attributes('-alpha', 0.0)
        self._fade_in()
        
        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header Frame with gradient effect
        self.header = ctk.CTkFrame(self, corner_radius=10, height=60)
        self.header.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        
        # Log Type Selector
        self.type_seg = ctk.CTkSegmentedButton(
            self.header, 
            values=["Experts", "Journal"],
            command=self._on_type_change,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.type_seg.pack(side="left", padx=15, pady=15)
        self.type_seg.set("Experts")
        
        # File Dropdown
        self.file_combo = ctk.CTkComboBox(
            self.header, 
            width=250,
            command=self._on_file_change,
            font=ctk.CTkFont(size=12)
        )
        self.file_combo.pack(side="left", padx=10, pady=15)
        
        # Refresh Button
        self.btn_refresh = AnimatedButton(
            self.header, 
            text="⟳ Refresh",
            width=100,
            height=32,
            command=self._load_file_list,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_refresh.pack(side="right", padx=15, pady=15)

        # Content Area with improved styling
        self.content_frame = ctk.CTkFrame(self, corner_radius=10)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        self.text_area = ctk.CTkTextbox(
            self.content_frame,
            font=("Consolas", 11),
            wrap="none"
        )
        self.text_area.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Load initial data
        self._load_file_list()
    
    def _fade_in(self, alpha=0.0):
        if alpha < 1.0:
            alpha += 0.1
            self.attributes('-alpha', alpha)
            self.after(20, lambda: self._fade_in(alpha))
        else:
            self.attributes('-alpha', 1.0)

    def _on_type_change(self, value):
        self.current_log_type = value.lower()
        self._load_file_list()

    def _load_file_list(self):
        files = self.docker_service.get_log_list(self.container_id, self.current_log_type)
        
        if files:
            self.file_combo.configure(values=files)
            self.file_combo.set(files[0])
            self._on_file_change(files[0])
        else:
            self.file_combo.configure(values=["No logs found"])
            self.file_combo.set("No logs found")
            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", f"📁 No {self.current_log_type} logs found.")

    def _on_file_change(self, filename):
        if filename == "No logs found":
            return
        threading.Thread(target=self._load_content_thread, args=(filename,), daemon=True).start()

    def _load_content_thread(self, filename):
        content = self.docker_service.read_log_content(self.container_id, self.current_log_type, filename)
        self.after(0, lambda: self._update_text_area(content))

    def _update_text_area(self, content):
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", content)
        self.text_area.see("end")


class ContainerCard(ctk.CTkFrame):
    """Individual container card with animations"""
    def __init__(self, parent, container_data, callbacks, **kwargs):
        super().__init__(parent, corner_radius=12, **kwargs)
        
        self.container = container_data
        self.callbacks = callbacks
        
        # Hover effect
        self.default_fg = self.cget("fg_color")
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        self._build_ui()
        
        # Slide in animation
        self._slide_in()
    
    def _slide_in(self):
        original_height = self.winfo_reqheight()
        self.configure(height=0)
        self._animate_height(0, 100)
    
    def _animate_height(self, current, target, step=10):
        if current < target:
            current = min(current + step, target)
            self.after(10, lambda: self._animate_height(current, target, step))
    
    def _on_enter(self, e):
        self.configure(border_width=2, border_color="#1f6aa5")
    
    def _on_leave(self, e):
        self.configure(border_width=0)
    
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        
        # Left section - Info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        # Name
        name_label = ctk.CTkLabel(
            info_frame,
            text=f"🖥️  {self.container['name']}",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.pack(anchor="w", pady=(0, 5))
        
        # Status and ports
        details_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        details_frame.pack(anchor="w")
        
        StatusBadge(details_frame, self.container['status']).pack(side="left", padx=(0, 15))
        
        if self.container['vnc_port'] != "N/A":
            port_label = ctk.CTkLabel(
                details_frame,
                text=f"🖼️ VNC: {self.container['vnc_port']}",
                font=ctk.CTkFont(size=11),
                text_color="#888"
            )
            port_label.pack(side="left", padx=(0, 15))
        
        if self.container['api_port'] != "N/A":
            api_label = ctk.CTkLabel(
                details_frame,
                text=f"🔌 API: {self.container['api_port']}",
                font=ctk.CTkFont(size=11),
                text_color="#888"
            )
            api_label.pack(side="left")
        
        # Right section - Actions
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e", padx=20, pady=15)
        
        if self.container['vnc_port'] != "N/A":
            btn_vnc = AnimatedButton(
                action_frame,
                text="🖥️ Open VNC",
                width=110,
                height=32,
                fg_color="#1f6aa5",
                hover_color="#1557a0",
                command=lambda: webbrowser.open(f"http://localhost:{self.container['vnc_port']}"),
                font=ctk.CTkFont(size=12, weight="bold")
            )
            btn_vnc.pack(side="left", padx=5)
        
        btn_logs = AnimatedButton(
            action_frame,
            text="📋 Logs",
            width=90,
            height=32,
            fg_color="#555",
            hover_color="#444",
            command=lambda: self.callbacks['logs'](self.container['id'], self.container['name']),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        btn_logs.pack(side="left", padx=5)
        
        btn_delete = AnimatedButton(
            action_frame,
            text="🗑️",
            width=40,
            height=32,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=lambda: self.callbacks['delete'](self.container['id']),
            font=ctk.CTkFont(size=14)
        )
        btn_delete.pack(side="left", padx=5)


class MT5ManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MT5 Instance Manager")
        self.geometry("1200x700")
        
        # Center window
        self.center_window()

        self.docker_service = DockerService()
        self.containers = []
        self.loading_spinner = None

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar with gradient effect
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Logo with animation
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="📊 MT5\nManager",
            font=ctk.CTkFont(size=24, weight="bold"),
            justify="center"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Version
        version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="v2.0",
            font=ctk.CTkFont(size=10),
            text_color="#666"
        )
        version_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Sidebar buttons
        self.btn_dashboard = AnimatedButton(
            self.sidebar_frame,
            text="📈 Dashboard",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.show_dashboard,
            anchor="w"
        )
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # Stats frame
        self.stats_frame = ctk.CTkFrame(self.sidebar_frame, corner_radius=10)
        self.stats_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
        self.stats_label = ctk.CTkLabel(
            self.stats_frame,
            text="Active Instances\n0",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.stats_label.pack(pady=15)
        
        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Header with title
        self.title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        title_label = ctk.CTkLabel(
            self.title_frame,
            text="Instance Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w"
        )
        title_label.pack(side="left")

        # Action buttons
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=60)
        self.header_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        self.btn_refresh = AnimatedButton(
            self.header_frame,
            text="⟳ Refresh",
            width=120,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.refresh_list
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_add = AnimatedButton(
            self.header_frame,
            text="➕ Add Instance",
            width=140,
            height=40,
            fg_color="#2CC985",
            hover_color="#229A66",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.open_add_dialog
        )
        self.btn_add.pack(side="left", padx=5)

        self.btn_upload = AnimatedButton(
            self.header_frame,
            text="📤 Upload Agent",
            width=140,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.upload_agent_dialog
        )
        self.btn_upload.pack(side="left", padx=5)

        self.btn_kill = AnimatedButton(
            self.header_frame,
            text="☢️ KILL SWITCH",
            width=140,
            height=40,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.kill_switch
        )
        self.btn_kill.pack(side="right", padx=5)

        # Container list
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            corner_radius=10,
            fg_color=("#E5E5E5", "#2B2B2B")
        )
        self.scrollable_frame.grid(row=2, column=0, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Initial Load
        self.refresh_list()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def show_dashboard(self):
        pass

    def refresh_list(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Show loading
        self.loading_spinner = LoadingSpinner(self.scrollable_frame)
        self.loading_spinner.pack(pady=40)
        self.loading_spinner.start()

        # Fetch in background
        threading.Thread(target=self._fetch_and_update_ui, daemon=True).start()

    def _fetch_and_update_ui(self):
        self.containers = self.docker_service.list_mt5_containers()
        time.sleep(0.5)  # Minimum loading time for UX
        self.after(0, self._render_list)

    def _render_list(self):
        if self.loading_spinner:
            self.loading_spinner.stop()
            self.loading_spinner.destroy()

        # Update stats
        running_count = sum(1 for c in self.containers if "running" in c['status'].lower())
        self.stats_label.configure(text=f"Active Instances\n{running_count}/{len(self.containers)}")

        if not self.containers:
            empty_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=10)
            empty_frame.pack(fill="both", expand=True, padx=20, pady=40)
            
            ctk.CTkLabel(
                empty_frame,
                text="🔍 No MT5 Containers Found",
                font=ctk.CTkFont(size=18, weight="bold")
            ).pack(pady=(40, 10))
            
            ctk.CTkLabel(
                empty_frame,
                text="Click '➕ Add Instance' to create your first trading instance",
                font=ctk.CTkFont(size=13),
                text_color="#888"
            ).pack(pady=(0, 40))
            return

        # Render container cards with staggered animation
        callbacks = {
            'logs': self.open_logs_window,
            'delete': self.delete_container
        }
        
        for i, container in enumerate(self.containers):
            card = ContainerCard(self.scrollable_frame, container, callbacks)
            card.pack(fill="x", padx=10, pady=5)
            # Stagger the animation
            self.after(i * 50, lambda c=card: c._slide_in())

    def open_add_dialog(self):
        dialog = ctk.CTkInputDialog(
            text="Enter Account Name (no spaces):",
            title="🆕 Create New MT5 Instance"
        )
        account_name = dialog.get_input()
        
        if account_name:
            vnc, api = self.docker_service.get_next_available_ports()
            threading.Thread(
                target=self._create_container_thread,
                args=(account_name, vnc, api),
                daemon=True
            ).start()

    def _create_container_thread(self, name, vnc, api):
        err = self.docker_service.create_mt5_container(name, vnc, api)
        if err:
            self.after(0, lambda: messagebox.showerror("Error", err))
        else:
            self.after(0, lambda: messagebox.showinfo("Success", f"✅ Instance '{name}' created successfully!"))
            self.after(0, self.refresh_list)

    def open_logs_window(self, container_id, container_name):
        LogViewerWindow(self, self.docker_service, container_id, container_name)

    def delete_container(self, container_id):
        if messagebox.askyesno("⚠️ Confirm Deletion", 
                              "Are you sure you want to delete this instance?\n\nThis action cannot be undone."):
            err = self.docker_service.remove_container(container_id)
            if err:
                messagebox.showerror("Error", err)
            else:
                messagebox.showinfo("Success", "✅ Instance deleted successfully!")
            self.refresh_list()

    def kill_switch(self):
        if messagebox.askyesno(
            "⚠️ EMERGENCY STOP",
            "⚠️ WARNING ⚠️\n\nThis will IMMEDIATELY STOP all active trading instances!\n\nAll running operations will be terminated.\n\nAre you absolutely sure?",
            icon='warning'
        ):
            errors = self.docker_service.kill_all_mt5_containers()
            if errors:
                msg = "\n".join(errors)
                messagebox.showerror("Partial Failure", f"⚠️ Some containers could not be stopped:\n\n{msg}")
            else:
                messagebox.showinfo("Success", "✅ All MT5 instances have been stopped.")
            self.refresh_list()

    def upload_agent_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Select MQL5 Expert Advisor",
            filetypes=[("MQL5 Executables", "*.ex5 *.mq5"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        if not messagebox.askyesno(
            "📤 Upload Agent",
            f"Upload this agent to ALL {len([c for c in self.containers if 'running' in c['status'].lower()])} active instances?"
        ):
            return

        threading.Thread(target=self._upload_thread, args=(file_path,), daemon=True).start()

    def _upload_thread(self, file_path):
        success_count = 0
        total = 0
        for c in self.containers:
            if "running" in c['status'].lower():
                total += 1
                err = self.docker_service.upload_expert(c['id'], file_path)
                if not err:
                    success_count += 1
        
        self.after(0, lambda: messagebox.showinfo(
            "Upload Complete",
            f"✅ Successfully uploaded to {success_count}/{total} active containers."
        ))


if __name__ == "__main__":
    app = MT5ManagerApp()
    app.mainloop()