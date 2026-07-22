import logging
from pathlib import Path
from typing import Optional, Dict

import docker
from docker.errors import BuildError, APIError, ContainerError, ImageNotFound

logger = logging.getLogger(__name__)

class DockerServiceException(Exception):
    pass


class DockerService:
    @staticmethod
    def _get_client() -> docker.DockerClient:
        try:
            return docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise DockerServiceException(f"Failed to connect to Docker daemon: {e}")

    @staticmethod
    def build_image(repo_path: str, image_tag: str, build_context: str = ".", dockerfile_path: str = "Dockerfile") -> str:
        """
        Builds a Docker image from a local repository.
        Returns the image tag.
        """
        client = DockerService._get_client()
        logger.info(f"Building docker image {image_tag} at {repo_path}")
        try:
            # We must resolve the absolute path to the build context
            context_path = str((Path(repo_path) / build_context).resolve())
            
            # The docker-py SDK build returns a tuple of (Image, build_logs)
            _, build_logs = client.images.build(
                path=context_path,
                dockerfile=dockerfile_path,
                tag=image_tag,
                rm=True,
                pull=True
            )
            
            # Log the build process for debug
            for chunk in build_logs:
                if 'stream' in chunk:
                    logger.debug(chunk['stream'].strip())

            logger.info(f"Successfully built image {image_tag}")
            return image_tag
            
        except BuildError as e:
            # Build error contains the build logs
            error_log = ""
            for chunk in e.build_log:
                if 'stream' in chunk:
                    error_log += chunk['stream']
                elif 'error' in chunk:
                    error_log += chunk['error']
            logger.error(f"Failed to build image {image_tag}: {error_log}")
            raise DockerServiceException(f"Docker build failed: {error_log}")
        except APIError as e:
            logger.error(f"Docker API error during build: {e}")
            raise DockerServiceException(f"Docker API error during build: {e}")

    @staticmethod
    def run_container(image_tag: str, container_name: str, env_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Runs a container in detached mode, publishing all exposed ports.
        Returns the container ID.
        """
        client = DockerService._get_client()
        logger.info(f"Starting container {container_name} from {image_tag}")
        try:
            container = client.containers.run(
                image_tag,
                name=container_name,
                detach=True,
                environment=env_vars or {},
                publish_all_ports=True,
                restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}
            )
            logger.info(f"Successfully started container {container_name} (ID: {container.id})")
            return container.id
        except ContainerError as e:
            logger.error(f"Container {container_name} failed to run: {e.stderr}")
            raise DockerServiceException(f"Container failed to start: {e.stderr}")
        except APIError as e:
            logger.error(f"Docker API error starting container {container_name}: {e}")
            raise DockerServiceException(f"Docker API error starting container: {e}")

    @staticmethod
    def get_container_ports(container_name_or_id: str) -> Dict[str, int]:
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            container.reload()
            ports = container.attrs['NetworkSettings']['Ports']
            # ports looks like {'8000/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '32768'}]}
            mapped_ports = {}
            if ports:
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        mapped_ports[container_port] = int(host_bindings[0]['HostPort'])
            return mapped_ports
        except docker.errors.NotFound:
            return {}
        except APIError as e:
            raise DockerServiceException(f"Failed to get container ports: {e}")

    @staticmethod
    def stop_and_remove_container(container_name_or_id: str) -> None:
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            logger.info(f"Stopping container {container_name_or_id}")
            container.stop(timeout=10)
            logger.info(f"Removing container {container_name_or_id}")
            container.remove(force=True)
        except docker.errors.NotFound:
            logger.warning(f"Container {container_name_or_id} not found, nothing to remove")
        except APIError as e:
            logger.error(f"Failed to stop/remove container {container_name_or_id}: {e}")
            raise DockerServiceException(f"Failed to stop/remove container: {e}")

    @staticmethod
    def get_container_status(container_name_or_id: str) -> Optional[str]:
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            container.reload()
            return container.status # 'created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead'
        except docker.errors.NotFound:
            return None
        except APIError as e:
            raise DockerServiceException(f"Failed to get container status: {e}")
