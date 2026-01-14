import customtkinter as ctk
from tkinter import filedialog, messagebox
import webbrowser
import threading
from docker_service import DockerService

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LogViewerWindow(ctk.CTkToplevel):
    def __init__(self, master, docker_service, container_id, container_name):
        super().__init__(master)
        
        self.docker_service = docker_service
        self.container_id = container_id
        self.container_name = container_name
        self.current_log_type = "experts" # Default
        
        self.title(f"Logs: {container_name}")
        self.geometry("900x600")
        
        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header Frame
        self.header = ctk.CTkFrame(self)
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Log Type Selector
        self.type_seg = ctk.CTkSegmentedButton(self.header, values=["Experts", "Journal"], command=self._on_type_change)
        self.type_seg.pack(side="left", padx=10)
        self.type_seg.set("Experts")
        
        # File Dropdown
        self.file_combo = ctk.CTkComboBox(self.header, width=200, command=self._on_file_change)
        self.file_combo.pack(side="left", padx=10)
        
        # Refresh Button
        self.btn_refresh = ctk.CTkButton(self.header, text="Refresh", width=80, command=self._load_file_list)
        self.btn_refresh.pack(side="right", padx=10)

        # Content Area
        self.text_area = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Load initial data
        self._load_file_list()

    def _on_type_change(self, value):
        self.current_log_type = value.lower()
        self._load_file_list()

    def _load_file_list(self):
        # Fetch files in background thread? Or sync for simplicity first. 
        # The docker call is fast enough usually.
        files = self.docker_service.get_log_list(self.container_id, self.current_log_type)
        
        if files:
            self.file_combo.configure(values=files)
            self.file_combo.set(files[0])
            self._on_file_change(files[0]) # Load content of first file
        else:
            self.file_combo.configure(values=["No logs found"])
            self.file_combo.set("No logs found")
            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", f"No {self.current_log_type} logs found.")

    def _on_file_change(self, filename):
        if filename == "No logs found":
            return
            
        threading.Thread(target=self._load_content_thread, args=(filename,)).start()

    def _load_content_thread(self, filename):
        content = self.docker_service.read_log_content(self.container_id, self.current_log_type, filename)
        self.after(0, lambda: self._update_text_area(content))

    def _update_text_area(self, content):
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", content)
        self.text_area.see("end") # Scroll to bottom by default


class MT5ManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MT5 Instance Manager")
        self.geometry("1000x600")

        self.docker_service = DockerService()
        self.containers = []

        # --- Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MT5 Manager", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard)
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)
        
        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Header Buttons
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        self.btn_refresh = ctk.CTkButton(self.header_frame, text="Refresh List", command=self.refresh_list)
        self.btn_refresh.pack(side="left", padx=10)

        self.btn_add = ctk.CTkButton(self.header_frame, text="+ Add Instance", fg_color="#2CC985", hover_color="#229A66", command=self.open_add_dialog)
        self.btn_add.pack(side="right", padx=10)

        self.btn_upload = ctk.CTkButton(self.header_frame, text="Upload Agent", command=self.upload_agent_dialog)
        self.btn_upload.pack(side="right", padx=10)

        self.btn_kill = ctk.CTkButton(self.header_frame, text="☢ KILL SWITCH", fg_color="red", hover_color="darkred", command=self.kill_switch)
        self.btn_kill.pack(side="right", padx=30)

        # Table / List
        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Active Instances")
        self.scrollable_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # Initial Load
        self.refresh_list()

    def show_dashboard(self):
        pass # Already handling main view

    def refresh_list(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Fetch from Docker
        # Run in thread to avoid UI freeze
        threading.Thread(target=self._fetch_and_update_ui).start()

    def _fetch_and_update_ui(self):
        self.containers = self.docker_service.list_mt5_containers()
        self.after(0, self._render_list)

    def _render_list(self):
        if not self.containers:
            ctk.CTkLabel(self.scrollable_frame, text="No active MT5 containers found.").pack(pady=20)
            return

        # Header Row
        header = ctk.CTkFrame(self.scrollable_frame, height=30)
        header.pack(fill="x", pady=2)
        ctk.CTkLabel(header, text="Name", width=200, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Status", width=100, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(header, text="VNC Port", width=100, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(header, text="API Port", width=100, anchor="w").pack(side="left", padx=10)
        
        for c in self.containers:
            row = ctk.CTkFrame(self.scrollable_frame)
            row.pack(fill="x", pady=5)

            name_lbl = ctk.CTkLabel(row, text=c['name'], width=200, anchor="w", font=ctk.CTkFont(weight="bold"))
            name_lbl.pack(side="left", padx=10)

            status_color = "green" if "running" in c['status'].lower() else "red"
            status_lbl = ctk.CTkLabel(row, text=c['status'], text_color=status_color, width=100, anchor="w")
            status_lbl.pack(side="left", padx=10)

            vnc_lbl = ctk.CTkLabel(row, text=c['vnc_port'], width=100, anchor="w")
            vnc_lbl.pack(side="left", padx=10)
            
            api_lbl = ctk.CTkLabel(row, text=c['api_port'], width=100, anchor="w")
            api_lbl.pack(side="left", padx=10)

            # Actions
            if c['vnc_port'] != "N/A":
                btn_vnc = ctk.CTkButton(row, text="Open VNC", width=80, height=25, 
                                      command=lambda p=c['vnc_port']: webbrowser.open(f"http://localhost:{p}"))
                btn_vnc.pack(side="right", padx=5, pady=5)
            
            btn_logs = ctk.CTkButton(row, text="Logs", width=80, height=25, fg_color="#555", hover_color="#444",
                                       command=lambda cid=c['id'], cname=c['name']: self.open_logs_window(cid, cname))
            btn_logs.pack(side="right", padx=5)

            
            btn_del = ctk.CTkButton(row, text="X", width=30, height=25, fg_color="red", hover_color="darkred",
                                    command=lambda cid=c['id']: self.delete_container(cid))
            btn_del.pack(side="right", padx=5)


    def open_add_dialog(self):
        dialog = ctk.CTkInputDialog(text="Enter Account Name (No spaces):", title="New MT5 Instance")
        account_name = dialog.get_input()
        
        if account_name:
            # Determine ports
            vnc, api = self.docker_service.get_next_available_ports()
            
            # Show loading or status
            print(f"Creating {account_name} on VNC:{vnc}, API:{api}...")
            
            threading.Thread(target=self._create_container_thread, args=(account_name, vnc, api)).start()

    def _create_container_thread(self, name, vnc, api):
        err = self.docker_service.create_mt5_container(name, vnc, api)
        if err:
            self.after(0, lambda: messagebox.showerror("Error", err))
        else:
            self.after(0, self.refresh_list)

    def open_logs_window(self, container_id, container_name):
        # Prevent opening multiple windows for same container? 
        # For now, just open a new one. User has control.
        # pass docker_service instance
        LogViewerWindow(self, self.docker_service, container_id, container_name)


    def delete_container(self, container_id):
        if messagebox.askyesno("Confirm", "Delete this instance?"):
             err = self.docker_service.remove_container(container_id)
             if err:
                 messagebox.showerror("Error", err)
             self.refresh_list()

    def kill_switch(self):
        """Emergency stop for all containers."""
        if messagebox.askyesno("EMERGENCY STOP", "Are you sure you want to FORCE KILL ALL active trading instances?\n\nThis will stop all containers immediately.", icon='warning'):
            errors = self.docker_service.kill_all_mt5_containers()
            if errors:
                msg = "\n".join(errors)
                messagebox.showerror("Partial Failure", f"Some containers could not be killed:\n{msg}")
            else:
                messagebox.showinfo("Success", "All MT5 instances have been killed.")
            self.refresh_list()

    def upload_agent_dialog(self):
        file_path = filedialog.askopenfilename(filetypes=[("MQL5 Executables", "*.ex5 *.mq5")])
        if not file_path:
            return

        # Simple for now: Upload to ALL active containers? Or let user choose? 
        # For this logic, let's ask "Upload to all active instances?"
        
        if not messagebox.askyesno("Upload Agent", "Upload this agent to ALL active MT5 instances?"):
            return

        threading.Thread(target=self._upload_thread, args=(file_path,)).start()

    def _upload_thread(self, file_path):
        success_count = 0
        for c in self.containers:
            if "running" in c['status'].lower():
                err = self.docker_service.upload_expert(c['id'], file_path)
                if not err:
                    success_count += 1
                else:
                    print(f"Failed to upload to {c['name']}: {err}")
        
        self.after(0, lambda: messagebox.showinfo("Upload Complete", f"Uploaded to {success_count} containers."))

if __name__ == "__main__":
    app = MT5ManagerApp()
    app.mainloop()
