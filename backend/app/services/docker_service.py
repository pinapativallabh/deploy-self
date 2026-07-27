import logging
from pathlib import Path
from typing import Optional, Dict

import docker
from docker.errors import BuildError, APIError, ContainerError, ImageNotFound

logger = logging.getLogger(__name__)

class DockerServiceException(Exception):
    pass

class DockerServiceBuildException(DockerServiceException):
    def __init__(self, message: str, logs: str):
        super().__init__(message)
        self.logs = logs

class DockerService:
    _client = None

    @staticmethod
    def _get_client() -> docker.DockerClient:
        if DockerService._client is None:
            try:
                DockerService._client = docker.from_env()
            except Exception as e:
                logger.error(f"Failed to connect to Docker daemon: {e}")
                raise DockerServiceException(f"Failed to connect to Docker daemon: {e}")
        return DockerService._client

    @staticmethod
    def build_image(repo_path: str, image_tag: str, build_context: str = ".", dockerfile_path: str = "Dockerfile") -> tuple[str, str]:
        """
        Builds a Docker image from a local repository.
        Returns the (image_tag, build_logs).
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
            build_logs_str = ""
            for chunk in build_logs:
                if 'stream' in chunk:
                    line = chunk['stream']
                    logger.debug(line.strip())
                    build_logs_str += line

            logger.info(f"Successfully built image {image_tag}")
            return image_tag, build_logs_str
            
        except BuildError as e:
            # Build error contains the build logs
            error_log = ""
            for chunk in e.build_log:
                if 'stream' in chunk:
                    error_log += chunk['stream']
                elif 'error' in chunk:
                    error_log += chunk['error']
            logger.error(f"Failed to build image {image_tag}: {error_log}")
            raise DockerServiceBuildException(f"Docker build failed", logs=error_log)
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

    @staticmethod
    def restart_container(container_name_or_id: str) -> None:
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            logger.info(f"Restarting container {container_name_or_id}")
            container.restart(timeout=10)
        except docker.errors.NotFound:
            raise DockerServiceException(f"Container {container_name_or_id} not found")
        except APIError as e:
            logger.error(f"Failed to restart container {container_name_or_id}: {e}")
            raise DockerServiceException(f"Failed to restart container: {e}")

    @staticmethod
    def stop_container(container_name_or_id: str) -> None:
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            logger.info(f"Stopping container {container_name_or_id}")
            container.stop(timeout=10)
        except docker.errors.NotFound:
            raise DockerServiceException(f"Container {container_name_or_id} not found")
        except APIError as e:
            logger.error(f"Failed to stop container {container_name_or_id}: {e}")
            raise DockerServiceException(f"Failed to stop container: {e}")

    @staticmethod
    def start_container(container_name_or_id: str) -> None:
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            logger.info(f"Starting container {container_name_or_id}")
            container.start()
        except docker.errors.NotFound:
            raise DockerServiceException(f"Container {container_name_or_id} not found")
        except APIError as e:
            logger.error(f"Failed to start container {container_name_or_id}: {e}")
            raise DockerServiceException(f"Failed to start container: {e}")

    @staticmethod
    def remove_container(container_name_or_id: str) -> None:
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            logger.info(f"Removing container {container_name_or_id}")
            container.remove(force=True)
        except docker.errors.NotFound:
            pass # already removed
        except APIError as e:
            logger.error(f"Failed to remove container {container_name_or_id}: {e}")
            raise DockerServiceException(f"Failed to remove container: {e}")

    @staticmethod
    def get_container_logs(container_name_or_id: str, tail: str | int = "all", follow: bool = False, timestamps: bool = False):
        """Get logs with various options."""
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            return container.logs(tail=tail, stream=follow, timestamps=timestamps, stdout=True, stderr=True)
        except docker.errors.NotFound:
            raise DockerServiceException(f"Container {container_name_or_id} not found")
        except APIError as e:
            logger.error(f"Failed to get container logs for {container_name_or_id}: {e}")
            raise DockerServiceException(f"Failed to get logs: {e}")

    @staticmethod
    def tail_logs(container_name_or_id: str, tail: int = 100, timestamps: bool = False) -> str:
        logs_bytes = DockerService.get_container_logs(container_name_or_id, tail=tail, follow=False, timestamps=timestamps)
        return logs_bytes.decode('utf-8', errors='replace')

    @staticmethod
    def stream_logs(container_name_or_id: str, tail: str | int = "all", timestamps: bool = False):
        # Alias for follow logs
        return DockerService.get_container_logs(container_name_or_id, tail=tail, follow=True, timestamps=timestamps)

    @staticmethod
    def follow_logs(container_name_or_id: str, tail: str | int = 10, timestamps: bool = False):
        return DockerService.get_container_logs(container_name_or_id, tail=tail, follow=True, timestamps=timestamps)

    @staticmethod
    def latest_logs(container_name_or_id: str, timestamps: bool = False) -> str:
        # Latest logs might mean tail 100 or something
        return DockerService.tail_logs(container_name_or_id, tail=100, timestamps=timestamps)

    @staticmethod
    def inspect_container(container_name_or_id: str) -> dict:
        import copy
        client = DockerService._get_client()
        try:
            container = client.containers.get(container_name_or_id)
            attrs = copy.deepcopy(container.attrs)
            if "Config" in attrs and "Env" in attrs["Config"]:
                attrs["Config"]["Env"] = ["<REDACTED>"]
            if "ContainerConfig" in attrs and "Env" in attrs["ContainerConfig"]:
                attrs["ContainerConfig"]["Env"] = ["<REDACTED>"]
            return attrs
        except docker.errors.NotFound:
            raise DockerServiceException(f"Container {container_name_or_id} not found")
        except APIError as e:
            logger.error(f"Failed to inspect container {container_name_or_id}: {e}")
            raise DockerServiceException(f"Failed to inspect container: {e}")

    @staticmethod
    def prune_resources() -> None:
        """
        Removes stopped containers, dangling images, networks, and build cache.
        Helps clean up failed or orphan containers.
        """
        client = DockerService._get_client()
        try:
            client.containers.prune()
            client.images.prune(filters={'dangling': True})
            # The Docker socket targets the host daemon. Network pruning could
            # disrupt unrelated applications, so only Bonk-safe resources are pruned.
            logger.info("Successfully pruned stopped containers and dangling images")
        except APIError as e:
            logger.error(f"Docker API error during prune: {e}")
            raise DockerServiceException(f"Failed to prune resources: {e}")

    @staticmethod
    def cleanup_project_resources(project_id: str) -> None:
        """
        Stop and remove all containers and images associated with a project.
        """
        client = DockerService._get_client()
        try:
            containers = client.containers.list(all=True, filters={"name": f"bonk-{project_id}"})
            for container in containers:
                logger.info(f"Removing container {container.name} for project {project_id}")
                try:
                    container.stop(timeout=5)
                except Exception:
                    pass
                try:
                    container.remove(force=True)
                except Exception:
                    pass
                    
            images = client.images.list(filters={"reference": f"bonk-{project_id}:*"})
            for image in images:
                logger.info(f"Removing image {image.tags} for project {project_id}")
                try:
                    client.images.remove(image.id, force=True)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to cleanup docker resources for project {project_id}: {e}")
