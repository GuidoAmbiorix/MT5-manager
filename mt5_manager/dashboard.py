from nicegui import ui, app
from docker_service import DockerService
import asyncio

# --- Configuration ---
ui.dark_mode().enable()

# --- Services ---
docker_service = DockerService()

# --- State ---
containers = []

# --- UI Functions ---

async def refresh_containers():
    """Fetches container list and updates the grid."""
    global containers
    # Run synchronous docker call in a separate thread to avoid blocking the event loop
    try:
        containers = await asyncio.to_thread(docker_service.list_mt5_containers)
    except Exception as e:
        ui.notify(f"Error fetching containers: {e}", type='negative')
        containers = []
    
    container_grid.clear()
    
    if not containers:
        with container_grid:
            ui.label("No active MT5 instances found.").classes("text-slate-400 italic col-span-full text-center mt-10")
        return

    with container_grid:
        for c in containers:
            create_container_card(c)

def create_container_card(c):
    """Creates a card for a single container."""
    is_running = "running" in c['status'].lower()
    status_color = "text-green-400" if is_running else "text-red-400"
    status_icon = "fiber_manual_record"
    
    with ui.card().classes("bg-slate-800 border border-slate-700 w-full hover:border-slate-500 transition-colors duration-200"):
        # Header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(c['name']).classes("text-lg font-bold text-slate-100")
            ui.icon(status_icon).classes(f"{status_color} text-xl animate-pulse" if is_running else f"{status_color} text-xl")

        ui.separator().classes("bg-slate-700 my-2")

        # Info
        with ui.grid(columns=2).classes("w-full gap-2 text-sm text-slate-300"):
            ui.label("Status:")
            ui.label(c['status']).classes(status_color)
            
            ui.label("VNC Port:")
            if c['vnc_port'] != "N/A":
                # Link to VNC (assuming localhost for now, or relative path if proxied)
                # Since we are in a container, localhost refers to the user's browser localhost if ports are mapped.
                ui.link(c['vnc_port'], f"http://localhost:{c['vnc_port']}", new_tab=True).classes("text-blue-400 hover:underline")
            else:
                ui.label("N/A")

            ui.label("API Port:")
            ui.label(c['api_port'])

        # Actions
        with ui.row().classes("w-full mt-4 justify-end gap-2"):
            # Logs
            ui.button(icon="description", on_click=lambda _, cid=c['id'], name=c['name']: open_logs(cid, name)).props("round flat size=sm color=grey").tooltip("View Logs")
            
            # VNC Quick Button
            if c['vnc_port'] != "N/A":
                 ui.button(icon="monitor", on_click=lambda _, p=c['vnc_port']: ui.open(f"http://localhost:{p}", new_tab=True)).props("round flat size=sm color=blue").tooltip("Open VNC")

            # Delete
            ui.button(icon="delete", on_click=lambda _, cid=c['id']: delete_instance(cid)).props("round flat size=sm color=red").tooltip("Delete Instance")

# --- Actions ---

async def create_instance_dialog():
    with ui.dialog() as dialog, ui.card().classes("bg-slate-800 border border-slate-600 min-w-[400px]"):
        ui.label("Create New MT5 Instance").classes("text-xl font-bold mb-4 text-slate-100")
        
        name_input = ui.input("Account Name").props("autofocus outlined dark").classes("w-full mb-4 text-slate-100")
        
        async def create():
            name = name_input.value.strip()
            if not name:
                ui.notify("Please enter a name", type='warning')
                return
            
            dialog.close()
            ui.notify(f"Creating instance '{name}'...", type='info', spinner=True)
            
            # Calculate ports
            # We need to run get_next_available_ports in thread safest way or just optimistically
            try:
                vnc, api = await asyncio.to_thread(docker_service.get_next_available_ports)
                err = await asyncio.to_thread(docker_service.create_mt5_container, name, vnc, api)
                
                if err:
                    ui.notify(f"Failed: {err}", type='negative')
                else:
                    ui.notify("Instance created successfully!", type='positive')
                    await refresh_containers()
            except Exception as e:
                ui.notify(f"Error: {e}", type='negative')

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
            ui.button("Create", on_click=create).props("color=green")
    
    dialog.open()

async def delete_instance(container_id):
    # Confirm
    result = await ui.run_javascript(f'confirm("Are you sure you want to delete this instance?");')
    if result:  # Note: nicegui confirmation dialog is better, let's use UI dialog instead of JS alert
        pass # placeholder, let's do properly below
    else:
        return

    # Actually let's use a proper nicegui dialog
    # But for now, let's just make a specific dialog function or reuse logic
    # To keep it simple in this flow:
    
    with ui.dialog() as dialog, ui.card().classes("bg-slate-800 border border-red-500"):
        ui.label("Confirm Deletion").classes("text-lg font-bold text-red-500")
        ui.label("Are you sure you want to delete this container?").classes("text-slate-300")
        with ui.row().classes("w-full justify-end mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
            async def do_delete():
                dialog.close()
                err = await asyncio.to_thread(docker_service.remove_container, container_id)
                if err:
                    ui.notify(f"Error: {err}", type='negative')
                else:
                    ui.notify("Instance deleted", type='positive')
                    await refresh_containers()
            ui.button("Confirm", on_click=do_delete).props("color=red")
    dialog.open()


async def open_logs(container_id, container_name):
    # Drawer for logs
    log_drawer.clear()
    log_drawer.open()
    
    with log_drawer:
        ui.label(f"Logs: {container_name}").classes("text-xl font-bold mb-4 text-slate-100")
        
        # Controls
        with ui.row().classes("w-full gap-2 mb-4"):
            log_type = ui.select(["Experts", "Journal"], value="Experts", label="Type").props("outlined dense dark").classes("w-32")
            file_select = ui.select([], label="File").props("outlined dense dark").classes("flex-grow")
            
            async def refresh_files():
                files = await asyncio.to_thread(docker_service.get_log_list, container_id, log_type.value.lower())
                file_select.options = files
                if files:
                    file_select.value = files[0]
                else:
                    file_select.value = None
            
            ui.button(icon="refresh", on_click=refresh_files).props("flat round color=blue")
            
        content_area = ui.code('Loading...', language='text').classes('w-full h-screen overflow-auto bg-slate-900 p-2 rounded text-xs font-mono text-slate-300')

        async def load_content():
            if not file_select.value:
                content_area.content = "No file selected."
                return
            
            content_area.content = "Reading..."
            content = await asyncio.to_thread(docker_service.read_log_content, container_id, log_type.value.lower(), file_select.value)
            content_area.content = content

        # Bind events
        log_type.on_value_change(refresh_files)
        file_select.on_value_change(load_content)
        
        # Initial Load
        await refresh_files()

async def upload_agent_dialog():
    # NiceGUI allows file upload
    with ui.dialog() as dialog, ui.card().classes("bg-slate-800 border border-slate-600 w-[500px]"):
        ui.label("Upload Expert Advisor (.ex5 / .mq5)").classes("text-xl font-bold mb-2 text-slate-100")
        ui.label("This will upload the file to ALL active instances.").classes("text-sm text-slate-400 mb-4")
        
        async def handle_upload(e):
            # e.content is a temporary file or bytes
            # We need to save it or pass path. 
            # DockerService.upload_expert expects a file path.
            # So we save e.content to a temp file.
            import tempfile
            import os
            
            fname = e.name
            if not (fname.endswith('.ex5') or fname.endswith('.mq5')):
                ui.notify("Invalid file type. Must be .ex5 or .mq5", type='warning')
                return

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{fname}") as tmp:
                    tmp.write(e.content.read())
                    tmp_path = tmp.name
                
                ui.notify("Uploading to containers...", type='info', spinner=True)
                
                # Iterate and upload
                success_count = 0
                for c in containers:
                    if "running" in c['status'].lower():
                        err = await asyncio.to_thread(docker_service.upload_expert, c['id'], tmp_path)
                        if not err:
                            success_count += 1
                        else:
                            print(f"Failed upload to {c['name']}: {err}")
                
                ui.notify(f"Uploaded to {success_count} containers.", type='positive')
                os.unlink(tmp_path) # Cleanup
                dialog.close()

            except Exception as err:
                ui.notify(f"Upload error: {err}", type='negative')

        ui.upload(on_upload=handle_upload, auto_upload=True).props("accept=.ex5,.mq5 dark").classes("w-full")
        
        ui.button("Close", on_click=dialog.close).props("flat color=grey").classes("mt-4 w-full")
    
    dialog.open()

async def kill_switch():
    with ui.dialog() as dialog, ui.card().classes("bg-red-900 border border-red-500"):
        ui.icon("warning", size="3em").classes("text-red-500 mx-auto mb-2")
        ui.label("EMERGENCY STOP").classes("text-2xl font-bold text-red-500 text-center")
        ui.label("Are you sure you want to FORCE KILL ALL active instances?").classes("text-white text-center font-bold mt-2")
        ui.label("This action is irreversible.").classes("text-red-200 text-center text-sm mb-6")
        
        with ui.row().classes("w-full justify-center gap-4"):
            ui.button("CANCEL", on_click=dialog.close).props("flat color=white")
            async def do_kill():
                dialog.close()
                ui.notify("Initializing Kill Switch...", type='negative', spinner=True)
                errors = await asyncio.to_thread(docker_service.kill_all_mt5_containers)
                if errors:
                     ui.notify("Partial failure. Check console.", type='warning')
                else:
                     ui.notify("All containers killed.", type='positive')
                await refresh_containers()
                
            ui.button("CONFIRM KILL", on_click=do_kill).props("color=red")
    dialog.open()

# --- Layout Definition ---

# Logs Drawer
log_drawer = ui.right_drawer(fixed=False).classes("bg-slate-900 border-l border-slate-700 w-[600px] p-4").props("overlay")

# Header
with ui.header(elevated=True).classes("bg-slate-900/80 backdrop-blur-md border-b border-slate-700 h-16 items-center px-4"):
    ui.label("MT5 Manager").classes("text-xl font-bold bg-gradient-to-r from-green-400 to-emerald-600 text-transparent bg-clip-text")
    ui.space()
    ui.button("Add Instance", icon="add", on_click=create_instance_dialog).props("color=green")
    ui.button("Upload Agent", icon="upload", on_click=upload_agent_dialog).props("flat color=white")
    ui.separator().props("vertical").classes("mx-2 h-8")
    ui.button("KILL SWITCH", icon="dangerous", on_click=kill_switch).props("color=red")

# Main Content
with ui.column().classes("w-full max-w-7xl mx-auto p-6"):
    # Stats / Title
    with ui.row().classes("w-full items-center justify-between mb-6"):
        ui.label("Active Trading Instances").classes("text-2xl text-slate-200 font-light")
        ui.button(icon="refresh", on_click=refresh_containers).props("flat round color=grey")

    # Grid
    container_grid = ui.grid(columns=1).classes("w-full gap-4 sm:grid-cols-2 lg:grid-cols-3")
    
    # Initial Fetch
    ui.timer(0.1, refresh_containers, once=True)
    # Auto-refresh every 5 seconds
    ui.timer(5.0, refresh_containers)

# Run App
ui.run(title="MT5 Manager", port=8080, favicon="Chart")
