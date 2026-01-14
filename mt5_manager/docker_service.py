import docker
import tarfile
import io
import os
from typing import List, Dict, Optional

class DockerService:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            print(f"Error connecting to Docker: {e}")
            self.client = None

    def list_mt5_containers(self) -> List[Dict]:
        """Lists all containers with names starting with 'trading_mt5_'."""
        if not self.client:
            return []
        
        containers = []
        try:
            # Filter specifically for our MT5 containers
            all_containers = self.client.containers.list(all=True)
            for container in all_containers:
                if container.name.startswith("trading_mt5_"):
                    # Extract port mappings
                    ports = container.attrs['NetworkSettings']['Ports']
                    vnc_port = "N/A"
                    api_port = "N/A"
                    
                    if ports:
                        # 3000/tcp -> VNC
                        vnc_data = ports.get('3000/tcp')
                        if vnc_data:
                            vnc_port = vnc_data[0]['HostPort']
                        
                        # 8001/tcp -> API
                        api_data = ports.get('8001/tcp')
                        if api_data:
                            api_port = api_data[0]['HostPort']

                    containers.append({
                        "id": container.short_id,
                        "name": container.name,
                        "status": container.status,
                        "vnc_port": vnc_port,
                        "api_port": api_port,
                        "obj": container
                    })
        except Exception as e:
            print(f"Error listing containers: {e}")
            
        return containers

    def create_mt5_container(self, account_name: str, vnc_port: int, api_port: int, password: str = "trading") -> Optional[str]:
        """Creates and starts a new MT5 container."""
        if not self.client:
            return "Docker client not connected"

        container_name = f"trading_mt5_{account_name}"
        volume_name = f"mt5_config_{account_name}"
        
        try:
            self.client.containers.run(
                image="gmag11/metatrader5_vnc:latest",
                name=container_name,
                ports={
                    '3000/tcp': vnc_port,
                    '8001/tcp': api_port
                },
                environment={
                    "CUSTOM_USER": "trader",
                    "PASSWORD": "",
                    "VNCPASSWORD": "",
                    "VNC_DISABLE_AUTH": "true"
                },
                volumes={
                    volume_name: {'bind': '/config', 'mode': 'rw'}
                },
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                network="trading_network" # Ensure this matches the existing network
            )
            return None # Success
        except docker.errors.APIError as e:
            return f"Docker API Error: {e}"
        except Exception as e:
            return f"Error creating container: {e}"

    def upload_expert(self, container_id: str, file_path: str) -> Optional[str]:
        """Uploads an .ex5 or .mq5 file to the container's Expert folder."""
        if not self.client:
            return "Docker client not connected"

        try:
            container = self.client.containers.get(container_id)
            
            # Create a tar archive in memory
            file_name = os.path.basename(file_path)
            file_data = open(file_path, 'rb').read()
            
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tar_info = tarfile.TarInfo(name=file_name)
                tar_info.size = len(file_data)
                tar.addfile(tar_info, io.BytesIO(file_data))
            
            tar_stream.seek(0)
            
            # Destination path in the container
            # Based on research: /config/MQL5/Experts/
            dest_path = "/config/MQL5/Experts/"
            
            container.put_archive(
                path=dest_path,
                data=tar_stream
            )
            
            # Optional: Restart container to load the EA?
            # container.restart() 
            # User might want to restart manually or refresh in MT5, strictly restarting might be too aggressive
            
            return None # Success
        except Exception as e:
            return f"Error uploading file: {e}"

    def remove_container(self, container_id: str) -> Optional[str]:
        """Stops and removes a container."""
        if not self.client:
            return "Docker client not connected"

        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove()
            return None
        except Exception as e:
            return f"Error removing container: {e}"

    def kill_all_mt5_containers(self) -> List[str]:
        """Stops ALL MT5 containers immediately. Returns list of errors if any."""
        if not self.client:
            return ["Docker client not connected"]
        
        errors = []
        containers = self.list_mt5_containers()
        for c in containers:
            try:
                # Force kill for immediate stop
                c['obj'].kill()
            except Exception as e:
                errors.append(f"Failed to kill {c['name']}: {e}")
        return errors

    def stop_container(self, container_id: str) -> Optional[str]:
        """Stops a running container gracefully."""
        if not self.client:
            return "Docker client not connected"
        
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=30)
            return None
        except Exception as e:
            return f"Error stopping container: {e}"

    def start_container(self, container_id: str) -> Optional[str]:
        """Starts a stopped container."""
        if not self.client:
            return "Docker client not connected"
        
        try:
            container = self.client.containers.get(container_id)
            container.start()
            return None
        except Exception as e:
            return f"Error starting container: {e}"

    def restart_container(self, container_id: str) -> Optional[str]:
        """Restarts a container."""
        if not self.client:
            return "Docker client not connected"
        
        try:
            container = self.client.containers.get(container_id)
            container.restart(timeout=30)
            return None
        except Exception as e:
            return f"Error restarting container: {e}"

    def get_container_stats(self, container_id: str) -> Dict:
        """Returns CPU%, Memory usage, and Uptime for a container."""
        if not self.client:
            return {"error": "Docker client not connected"}
        
        try:
            container = self.client.containers.get(container_id)
            
            # Get container info for uptime
            info = container.attrs
            started_at = info.get('State', {}).get('StartedAt', '')
            
            # Calculate uptime
            uptime_str = "N/A"
            if started_at and container.status == 'running':
                from datetime import datetime, timezone
                # Parse ISO format with timezone
                started_at = started_at.replace('Z', '+00:00')
                try:
                    start_time = datetime.fromisoformat(started_at[:26] + '+00:00')
                    now = datetime.now(timezone.utc)
                    delta = now - start_time
                    
                    days = delta.days
                    hours, remainder = divmod(delta.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    if days > 0:
                        uptime_str = f"{days}d {hours}h"
                    elif hours > 0:
                        uptime_str = f"{hours}h {minutes}m"
                    else:
                        uptime_str = f"{minutes}m"
                except:
                    uptime_str = "N/A"
            
            # Get stats (non-streaming for quick snapshot)
            if container.status != 'running':
                return {
                    "cpu_percent": 0.0,
                    "memory_mb": 0,
                    "memory_percent": 0.0,
                    "uptime": "Stopped"
                }
            
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            cpu_percent = 0.0
            if system_delta > 0:
                num_cpus = stats['cpu_stats'].get('online_cpus', 1) or 1
                cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
            
            # Calculate memory
            memory_usage = stats['memory_stats'].get('usage', 0)
            memory_limit = stats['memory_stats'].get('limit', 1)
            memory_mb = memory_usage / (1024 * 1024)
            memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0
            
            return {
                "cpu_percent": round(cpu_percent, 1),
                "memory_mb": round(memory_mb, 0),
                "memory_percent": round(memory_percent, 1),
                "uptime": uptime_str
            }
            
        except Exception as e:
            return {
                "cpu_percent": 0.0,
                "memory_mb": 0,
                "memory_percent": 0.0,
                "uptime": "Error",
                "error": str(e)
            }

    def get_log_list(self, container_id: str, log_type: str) -> List[str]:
        """
        Lists log files for a given type.
        log_type: 'experts' or 'journal'
        """
        if not self.client:
            return []

        try:
            container = self.client.containers.get(container_id)
            
            # Determine path based on type
            # Experts: /config/MQL5/Logs/
            # Journal: /config/Logs/
            if log_type == 'experts':
                path = "/config/MQL5/Logs/"
            elif log_type == 'journal':
                path = "/config/Logs/"
            else:
                return []
            
            # Execute ls command
            cmd = f"ls -1 {path}"
            result = container.exec_run(cmd)
            
            if result.exit_code != 0:
                print(f"Error listing logs: {result.output.decode('utf-8')}")
                return []
                
            files = result.output.decode('utf-8').splitlines()
            # Filter for .log files and sort descending (newest first)
            log_files = [f for f in files if f.endswith('.log')]
            log_files.sort(reverse=True)
            
            return log_files

        except Exception as e:
            print(f"Error getting log list: {e}")
            return []

    def read_log_content(self, container_id: str, log_type: str, filename: str) -> Optional[str]:
        """Reads the content of a specific log file."""
        if not self.client:
            return "Docker client not connected"

        try:
            container = self.client.containers.get(container_id)
            
            if log_type == 'experts':
                path = f"/config/MQL5/Logs/{filename}"
            elif log_type == 'journal':
                path = f"/config/Logs/{filename}"
            else:
                return "Invalid log type"
            
            # Read file using cat
            # output is bytes
            cmd = f"cat {path}"
            result = container.exec_run(cmd)
             
            if result.exit_code != 0:
                return f"Error reading file: {result.output.decode('utf-8', errors='ignore')}"
            
            # MT5 logs are typically UTF-16 LE, but sometimes they might be simple ASCII/UTF-8 depending on wine/linux Setup.
            # However, standard MT5 on Windows writes UTF-16.
            # Let's try attempting to decode as utf-16 first, then utf-8.
            raw_data = result.output
            
            try:
                # Try UTF-16 first (common for MT5)
                # UTF-16 logs often start with BOM \xff\xfe
                content = raw_data.decode('utf-16')
            except UnicodeDecodeError:
                try:
                    content = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    content = raw_data.decode('utf-8', errors='replace')
            
            return content

        except Exception as e:
            return f"Error reading log content: {e}"

    def get_next_available_ports(self, start_vnc=3000, start_api=8001) -> tuple[int, int]:
        """Calculates the next available ports based on existing containers."""
        containers = self.list_mt5_containers()
        
        used_vnc = set()
        used_api = set()
        
        for c in containers:
            if c['vnc_port'] != "N/A":
                used_vnc.add(int(c['vnc_port']))
            if c['api_port'] != "N/A":
                used_api.add(int(c['api_port']))
        
        # Find next free VNC
        vnc = start_vnc
        while vnc in used_vnc:
            vnc += 1
            
        # Find next free API
        api = start_api
        while api in used_api:
            api += 1
            
        return vnc, api

