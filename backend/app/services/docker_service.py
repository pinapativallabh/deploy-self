class DockerService:
    @staticmethod
    def build_image(project_name: str, commit_sha: str, build_context: str, dockerfile_path: str) -> str:
        """
        Stub for building a docker image.
        In a real implementation, this would run `docker build`.
        Returns the image tag.
        """
        return f"{project_name}:{commit_sha}"

    @staticmethod
    def run_container(image_tag: str, env_vars: dict = None) -> str:
        """
        Stub for running a container.
        Returns the container ID.
        """
        return "fake_container_id_67890"

    @staticmethod
    def stop_container(container_id: str) -> None:
        """
        Stub for stopping a container.
        """
        pass
