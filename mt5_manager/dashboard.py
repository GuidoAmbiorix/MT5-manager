from nicegui import ui, app
from docker_service import DockerService
import asyncio
from datetime import datetime

# --- Configuration ---
ui.dark_mode().enable()

# --- Services ---
docker_service = DockerService()

# --- State ---
containers = []
is_loading = False

# --- Custom Styles ---
ui.add_head_html('''
<style>
    .glass-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .glass-header {
        background: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .status-pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    .card-hover {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .card-hover:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
    }
    
    .stat-card {
        background: linear-gradient(135deg, rgba(34, 211, 238, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%);
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #22d3ee 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-slide-in {
        animation: slideIn 0.4s ease-out forwards;
    }
    
    .scrollbar-thin::-webkit-scrollbar {
        width: 8px;
    }
    
    .scrollbar-thin::-webkit-scrollbar-track {
        background: rgba(30, 41, 59, 0.3);
        border-radius: 4px;
    }
    
    .scrollbar-thin::-webkit-scrollbar-thumb {
        background: rgba(148, 163, 184, 0.4);
        border-radius: 4px;
    }
    
    .scrollbar-thin::-webkit-scrollbar-thumb:hover {
        background: rgba(148, 163, 184, 0.6);
    }
</style>
''')

# --- UI Functions ---

async def refresh_containers():
    """Fetches container list and updates the grid."""
    global containers, is_loading
    is_loading = True
    
    try:
        containers = await asyncio.to_thread(docker_service.list_mt5_containers)
    except Exception as e:
        ui.notify(f"Error fetching containers: {e}", type='negative', position='top')
        containers = []
    finally:
        is_loading = False
    
    # Update stats
    update_stats()
    
    # Update grid
    container_grid.clear()
    
    if not containers:
        with container_grid:
            create_empty_state()
        return

    with container_grid:
        for i, c in enumerate(containers):
            create_container_card(c, i)

def update_stats():
    """Update statistics cards."""
    stats_container.clear()
    
    running = sum(1 for c in containers if "running" in c['status'].lower())
    stopped = len(containers) - running
    
    with stats_container:
        with ui.row().classes("w-full gap-4"):
            create_stat_card("Total Instances", len(containers), "deployed_code", "blue")
            create_stat_card("Running", running, "play_circle", "green")
            create_stat_card("Stopped", stopped, "stop_circle", "red")
            create_stat_card("Uptime", "99.9%", "trending_up", "cyan")

def create_stat_card(title, value, icon, color):
    """Creates a statistics card."""
    color_classes = {
        "blue": "from-blue-500/20 to-blue-600/10 border-blue-500/30",
        "green": "from-green-500/20 to-green-600/10 border-green-500/30",
        "red": "from-red-500/20 to-red-600/10 border-red-500/30",
        "cyan": "from-cyan-500/20 to-cyan-600/10 border-cyan-500/30"
    }
    
    icon_colors = {
        "blue": "text-blue-400",
        "green": "text-green-400",
        "red": "text-red-400",
        "cyan": "text-cyan-400"
    }
    
    with ui.card().classes(f"bg-gradient-to-br {color_classes[color]} border flex-1 min-w-[200px]"):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-1"):
                ui.label(title).classes("text-sm text-slate-400 font-medium")
                ui.label(str(value)).classes(f"text-3xl font-bold {icon_colors[color]}")
            ui.icon(icon).classes(f"{icon_colors[color]} text-4xl opacity-50")

def create_empty_state():
    """Creates an empty state UI."""
    with ui.column().classes("w-full items-center justify-center py-20 col-span-full"):
        ui.icon("inventory_2").classes("text-slate-600 text-8xl mb-4 opacity-50")
        ui.label("No MT5 Instances Found").classes("text-2xl text-slate-300 font-light mb-2")
        ui.label("Get started by creating your first trading instance").classes("text-slate-500 mb-6")
        ui.button("Create Instance", icon="add", on_click=create_instance_dialog).props("color=green size=lg")

def create_container_card(c, index):
    """Creates an enhanced card for a single container."""
    is_running = "running" in c['status'].lower()
    
    # Status configuration
    if is_running:
        status_color = "text-green-400"
        status_bg = "bg-green-500/20"
        status_border = "border-green-500/30"
        status_text = "Running"
    else:
        status_color = "text-red-400"
        status_bg = "bg-red-500/20"
        status_border = "border-red-500/30"
        status_text = "Stopped"
    
    with ui.card().classes(f"glass-card card-hover animate-slide-in w-full").style(f"animation-delay: {index * 0.05}s"):
        # Header with gradient
        with ui.row().classes("w-full items-center justify-between mb-3"):
            with ui.row().classes("items-center gap-3"):
                # Container icon
                ui.icon("dns").classes("text-slate-300 text-2xl bg-slate-700/50 p-2 rounded-lg")
                with ui.column().classes("gap-0"):
                    ui.label(c['name']).classes("text-lg font-bold text-slate-100")
                    ui.label(f"ID: {c['id'][:12]}").classes("text-xs text-slate-500 font-mono")
            
            # Status badge
            with ui.row().classes(f"{status_bg} {status_border} border rounded-full px-3 py-1 items-center gap-2"):
                ui.icon("fiber_manual_record").classes(f"{status_color} text-xs {'status-pulse' if is_running else ''}")
                ui.label(status_text).classes(f"{status_color} text-sm font-medium")

        ui.separator().classes("bg-slate-700/50 my-3")

        # Connection Info Grid
        with ui.grid(columns=2).classes("w-full gap-3 mb-4"):
            # VNC Port
            with ui.column().classes("gap-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("monitor").classes("text-blue-400 text-sm")
                    ui.label("VNC Port").classes("text-xs text-slate-400 font-medium uppercase tracking-wide")
                if c['vnc_port'] != "N/A":
                    ui.link(c['vnc_port'], f"http://localhost:{c['vnc_port']}", new_tab=True).classes("text-blue-400 hover:text-blue-300 font-mono text-sm font-semibold transition-colors")
                else:
                    ui.label("Not Available").classes("text-slate-600 text-sm")
            
            # API Port
            with ui.column().classes("gap-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("api").classes("text-purple-400 text-sm")
                    ui.label("API Port").classes("text-xs text-slate-400 font-medium uppercase tracking-wide")
                ui.label(c['api_port']).classes("text-purple-400 font-mono text-sm font-semibold")

        # Quick Stats
        with ui.row().classes("w-full gap-2 mb-4"):
            with ui.card().classes("bg-slate-700/30 flex-1 p-2 border border-slate-600/30"):
                ui.label("CPU").classes("text-xs text-slate-400")
                ui.label("12%").classes("text-sm text-cyan-400 font-semibold")
            
            with ui.card().classes("bg-slate-700/30 flex-1 p-2 border border-slate-600/30"):
                ui.label("Memory").classes("text-xs text-slate-400")
                ui.label("256MB").classes("text-sm text-green-400 font-semibold")
            
            with ui.card().classes("bg-slate-700/30 flex-1 p-2 border border-slate-600/30"):
                ui.label("Uptime").classes("text-xs text-slate-400")
                ui.label("2h 45m").classes("text-sm text-blue-400 font-semibold")

        ui.separator().classes("bg-slate-700/50 my-3")

        # Action Buttons
        with ui.row().classes("w-full justify-between items-center"):
            # Left actions
            with ui.row().classes("gap-1"):
                ui.button(icon="description", on_click=lambda cid=c['id'], name=c['name']: open_logs(cid, name)).props("round flat size=sm").classes("text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 transition-all").tooltip("View Logs")
                
                if c['vnc_port'] != "N/A":
                    ui.button(icon="monitor", on_click=lambda p=c['vnc_port']: ui.open(f"http://localhost:{p}", new_tab=True)).props("round flat size=sm").classes("text-slate-400 hover:text-green-400 hover:bg-green-500/10 transition-all").tooltip("Open VNC")
                
                ui.button(icon="restart_alt", on_click=lambda cid=c['id']: restart_instance(cid)).props("round flat size=sm").classes("text-slate-400 hover:text-yellow-400 hover:bg-yellow-500/10 transition-all").tooltip("Restart")
            
            # Right actions
            with ui.row().classes("gap-1"):
                if is_running:
                    ui.button(icon="stop_circle", on_click=lambda cid=c['id']: stop_instance(cid)).props("round flat size=sm").classes("text-slate-400 hover:text-orange-400 hover:bg-orange-500/10 transition-all").tooltip("Stop")
                else:
                    ui.button(icon="play_circle", on_click=lambda cid=c['id']: start_instance(cid)).props("round flat size=sm").classes("text-slate-400 hover:text-green-400 hover:bg-green-500/10 transition-all").tooltip("Start")
                
                ui.button(icon="delete", on_click=lambda cid=c['id'], name=c['name']: delete_instance(cid, name)).props("round flat size=sm").classes("text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all").tooltip("Delete")

# --- Actions ---

async def create_instance_dialog():
    with ui.dialog() as dialog, ui.card().classes("glass-card min-w-[500px] p-6"):
        # Header
        with ui.row().classes("w-full items-center gap-3 mb-6"):
            ui.icon("add_circle").classes("text-green-400 text-3xl")
            ui.label("Create New MT5 Instance").classes("text-2xl font-bold text-slate-100")
        
        ui.separator().classes("bg-slate-700/50 mb-6")
        
        # Form
        name_input = ui.input("Account Name").props("outlined dark").classes("w-full mb-4").style("color: white")
        
        with ui.expansion("Advanced Settings", icon="settings").classes("w-full mb-4 bg-slate-700/30 rounded-lg").props("dark"):
            ui.label("Coming soon: Custom port mapping, resource limits, etc.").classes("text-slate-400 text-sm p-4")
        
        async def create():
            name = name_input.value.strip()
            if not name:
                ui.notify("Please enter an instance name", type='warning', position='top')
                return
            
            dialog.close()
            ui.notify(f"Creating instance '{name}'...", type='info', position='top', spinner=True, timeout=0, close_button=True)
            
            try:
                vnc, api = await asyncio.to_thread(docker_service.get_next_available_ports)
                err = await asyncio.to_thread(docker_service.create_mt5_container, name, vnc, api)
                
                ui.notify(None)  # Clear spinner
                
                if err:
                    ui.notify(f"Failed to create instance: {err}", type='negative', position='top', timeout=5000)
                else:
                    ui.notify(f"Instance '{name}' created successfully!", type='positive', position='top', timeout=3000)
                    await refresh_containers()
            except Exception as e:
                ui.notify(None)  # Clear spinner
                ui.notify(f"Error: {str(e)}", type='negative', position='top', timeout=5000)

        with ui.row().classes("w-full justify-end gap-2 mt-6"):
            ui.button("Cancel", icon="close", on_click=dialog.close).props("flat").classes("text-slate-400")
            ui.button("Create Instance", icon="add", on_click=create).props("color=green")
    
    dialog.open()

async def delete_instance(container_id, container_name):
    with ui.dialog() as dialog, ui.card().classes("glass-card border-2 border-red-500/30 min-w-[450px] p-6"):
        # Warning Icon
        with ui.column().classes("w-full items-center mb-4"):
            ui.icon("warning").classes("text-red-500 text-6xl mb-2")
            ui.label("Confirm Deletion").classes("text-2xl font-bold text-red-500")
        
        ui.separator().classes("bg-red-500/30 mb-4")
        
        with ui.column().classes("w-full gap-2 mb-6"):
            ui.label(f"You are about to delete:").classes("text-slate-400 text-sm")
            with ui.card().classes("bg-red-500/10 border border-red-500/30 w-full p-3"):
                ui.label(container_name).classes("text-white font-mono text-lg font-bold")
            ui.label("This action cannot be undone. All data will be permanently lost.").classes("text-red-400 text-sm font-medium")
        
        async def do_delete():
            dialog.close()
            ui.notify(f"Deleting {container_name}...", type='info', position='top', spinner=True, timeout=0)
            
            err = await asyncio.to_thread(docker_service.remove_container, container_id)
            ui.notify(None)  # Clear spinner
            
            if err:
                ui.notify(f"Error: {err}", type='negative', position='top', timeout=5000)
            else:
                ui.notify(f"Instance deleted successfully", type='positive', position='top', timeout=3000)
                await refresh_containers()
        
        with ui.row().classes("w-full justify-center gap-3"):
            ui.button("Cancel", icon="close", on_click=dialog.close).props("size=lg flat").classes("text-slate-400")
            ui.button("Delete Forever", icon="delete_forever", on_click=do_delete).props("color=red size=lg")
    
    dialog.open()

async def stop_instance(container_id):
    ui.notify("Stopping instance...", type='info', position='top')
    # Implementation here
    await refresh_containers()

async def start_instance(container_id):
    ui.notify("Starting instance...", type='info', position='top')
    # Implementation here
    await refresh_containers()

async def restart_instance(container_id):
    ui.notify("Restarting instance...", type='info', position='top')
    # Implementation here
    await refresh_containers()

async def open_logs(container_id, container_name):
    log_drawer.clear()
    log_drawer.open()
    
    with log_drawer:
        # Header
        with ui.row().classes("w-full items-center justify-between mb-6"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("description").classes("text-blue-400 text-2xl")
                with ui.column().classes("gap-0"):
                    ui.label("Container Logs").classes("text-xl font-bold text-slate-100")
                    ui.label(container_name).classes("text-sm text-slate-400")
            ui.button(icon="close", on_click=log_drawer.close).props("flat round").classes("text-slate-400")
        
        ui.separator().classes("bg-slate-700 mb-4")
        
        # Controls
        with ui.row().classes("w-full gap-3 mb-4"):
            log_type = ui.select(["Experts", "Journal"], value="Experts", label="Log Type").props("outlined dense dark").classes("flex-1")
            file_select = ui.select([], label="Select File").props("outlined dense dark").classes("flex-1")
            
            async def refresh_files():
                files = await asyncio.to_thread(docker_service.get_log_list, container_id, log_type.value.lower())
                file_select.options = files
                if files:
                    file_select.value = files[0]
                else:
                    file_select.value = None
            
            ui.button(icon="refresh", on_click=refresh_files).props("flat round color=blue").tooltip("Refresh Files")
        
        # Log content with better styling
        with ui.card().classes("glass-card w-full flex-grow overflow-hidden"):
            content_area = ui.code('Loading logs...', language='text').classes('w-full h-[calc(100vh-250px)] scrollbar-thin overflow-auto bg-slate-950/50 p-4 rounded text-xs font-mono text-slate-300')

        async def load_content():
            if not file_select.value:
                content_area.content = "No file selected."
                return
            
            content_area.content = "Reading log file..."
            content = await asyncio.to_thread(docker_service.read_log_content, container_id, log_type.value.lower(), file_select.value)
            content_area.content = content or "Log file is empty."

        log_type.on_value_change(refresh_files)
        file_select.on_value_change(load_content)
        
        await refresh_files()

async def upload_agent_dialog():
    with ui.dialog() as dialog, ui.card().classes("glass-card min-w-[550px] p-6"):
        # Header
        with ui.row().classes("w-full items-center gap-3 mb-4"):
            ui.icon("upload_file").classes("text-cyan-400 text-3xl")
            ui.label("Upload Expert Advisor").classes("text-2xl font-bold text-slate-100")
        
        ui.separator().classes("bg-slate-700/50 mb-4")
        
        ui.label("Upload .ex5 or .mq5 files to all active instances").classes("text-slate-400 mb-4")
        
        with ui.card().classes("bg-slate-700/20 border-2 border-dashed border-slate-600 w-full p-8"):
            async def handle_upload(e):
                import tempfile
                import os
                
                fname = e.name
                if not (fname.endswith('.ex5') or fname.endswith('.mq5')):
                    ui.notify("Invalid file type. Must be .ex5 or .mq5", type='warning', position='top')
                    return

                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{fname}") as tmp:
                        tmp.write(e.content.read())
                        tmp_path = tmp.name
                    
                    dialog.close()
                    ui.notify("Uploading to containers...", type='info', position='top', spinner=True, timeout=0)
                    
                    success_count = 0
                    for c in containers:
                        if "running" in c['status'].lower():
                            err = await asyncio.to_thread(docker_service.upload_expert, c['id'], tmp_path)
                            if not err:
                                success_count += 1
                    
                    ui.notify(None)
                    ui.notify(f"Successfully uploaded to {success_count} containers", type='positive', position='top', timeout=3000)
                    os.unlink(tmp_path)

                except Exception as err:
                    ui.notify(None)
                    ui.notify(f"Upload error: {err}", type='negative', position='top', timeout=5000)

            with ui.column().classes("w-full items-center gap-3"):
                ui.icon("cloud_upload").classes("text-slate-500 text-6xl")
                ui.upload(on_upload=handle_upload, auto_upload=True).props("accept=.ex5,.mq5 dark").classes("w-full")
        
        ui.button("Close", icon="close", on_click=dialog.close).props("flat color=grey").classes("mt-4 w-full")
    
    dialog.open()

async def kill_switch():
    with ui.dialog() as dialog, ui.card().classes("bg-gradient-to-br from-red-900/80 to-red-950/80 border-2 border-red-500 min-w-[500px] p-8"):
        with ui.column().classes("w-full items-center gap-4"):
            ui.icon("warning").classes("text-red-500 text-8xl animate-pulse")
            ui.label("EMERGENCY STOP").classes("text-3xl font-bold text-red-500 text-center")
            
            with ui.card().classes("bg-red-950/50 border border-red-500/50 w-full p-4 mt-2"):
                ui.label("⚠️ This will FORCE KILL ALL active instances").classes("text-white text-center font-bold")
                ui.label("This action is IRREVERSIBLE").classes("text-red-300 text-center font-medium mt-2")
            
            ui.label("All running containers will be immediately terminated.").classes("text-red-200 text-center text-sm mb-4")
            
            async def do_kill():
                dialog.close()
                ui.notify("Executing Kill Switch...", type='negative', position='top', spinner=True, timeout=0)
                
                errors = await asyncio.to_thread(docker_service.kill_all_mt5_containers)
                ui.notify(None)
                
                if errors:
                    ui.notify("Partial failure. Check console.", type='warning', position='top', timeout=5000)
                else:
                    ui.notify("All containers terminated", type='positive', position='top', timeout=3000)
                
                await refresh_containers()
            
            with ui.row().classes("w-full justify-center gap-4 mt-4"):
                ui.button("CANCEL", icon="close", on_click=dialog.close).props("size=lg flat color=white")
                ui.button("EXECUTE KILL SWITCH", icon="dangerous", on_click=do_kill).props("color=red size=lg")
    
    dialog.open()

# --- Layout ---

# Logs Drawer with improved styling
log_drawer = ui.right_drawer(fixed=False).classes("glass-header w-[700px] p-6 scrollbar-thin").props("overlay")

# Header with glass effect
with ui.header(elevated=True).classes("glass-header h-20 items-center px-6"):
    with ui.row().classes("w-full max-w-7xl mx-auto items-center"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("show_chart").classes("text-cyan-400 text-3xl")
            ui.label("MT5 Manager").classes("text-2xl font-bold gradient-text")
        
        ui.space()
        
        with ui.row().classes("gap-2"):
            ui.button("New Instance", icon="add_circle", on_click=create_instance_dialog).props("color=green flat").classes("font-medium")
            ui.button("Upload EA", icon="upload_file", on_click=upload_agent_dialog).props("flat").classes("text-cyan-400 font-medium")
            
            ui.separator().props("vertical dark").classes("mx-2 h-10")
            
            ui.button("Emergency Stop", icon="dangerous", on_click=kill_switch).props("flat").classes("text-red-400 font-bold hover:bg-red-500/20")

# Main Content
with ui.column().classes("w-full min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6"):
    with ui.column().classes("w-full max-w-7xl mx-auto gap-6"):
        # Stats Row
        stats_container = ui.row().classes("w-full gap-4 mb-2")
        
        # Title and Controls
        with ui.row().classes("w-full items-center justify-between mb-4"):
            with ui.column().classes("gap-1"):
                ui.label("Trading Instances").classes("text-3xl text-slate-100 font-bold")
                ui.label(f"Last updated: {datetime.now().strftime('%H:%M:%S')}").classes("text-sm text-slate-500")
            
            with ui.row().classes("gap-2"):
                ui.button(icon="refresh", on_click=refresh_containers).props("round flat size=lg").classes("text-slate-400 hover:text-cyan-400 hover:bg-cyan-500/10").tooltip("Refresh")
                ui.button(icon="filter_list").props("round flat size=lg").classes("text-slate-400 hover:text-blue-400 hover:bg-blue-500/10").tooltip("Filter")

        # Container Grid
        container_grid = ui.grid(columns=1).classes("w-full gap-5 sm:grid-cols-2 xl:grid-cols-3")
        
        # Initial Load
        ui.timer(0.1, refresh_containers, once=True)
        # Auto-refresh
        ui.timer(10.0, refresh_containers)

# Run
ui.run(title="MT5 Manager", port=8080, favicon="📈", dark=True, reload=False)