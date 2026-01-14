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
                    "PASSWORD": password,
                    "VNCPASSWORD": password
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
