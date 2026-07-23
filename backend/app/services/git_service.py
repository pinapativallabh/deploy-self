import logging
import os
from pathlib import Path

from git import Repo, exc

logger = logging.getLogger(__name__)

class GitServiceException(Exception):
    pass


class GitService:
    # Use a generic path or allow configuration
    CLONE_BASE_DIR = Path("/tmp/bonk_repos") if os.name != "nt" else Path(os.getenv("TEMP", "C:/Temp")) / "bonk_repos"

    @staticmethod
    def clone_repo(repository_url: str, branch: str, project_id: str, commit_sha: str = None) -> tuple[str, str]:
        """
        Clones a repository, or fetches and checks out the branch if already cloned.
        If commit_sha is provided, it will check out that specific commit.
        Returns a tuple of (local_repository_path, commit_sha).
        """
        try:
            GitService.CLONE_BASE_DIR.mkdir(parents=True, exist_ok=True)
            repo_path = GitService.CLONE_BASE_DIR / str(project_id)

            if repo_path.exists() and (repo_path / ".git").exists():
                logger.info(f"Reusing existing clone at {repo_path} for project {project_id}")
                repo = Repo(repo_path)
                
                # Fetch all remotes
                for remote in repo.remotes:
                    remote.fetch()

            else:
                logger.info(f"Cloning {repository_url} to {repo_path} for project {project_id}")
                repo = Repo.clone_from(repository_url, repo_path)

            if commit_sha:
                repo.git.checkout(commit_sha)
                repo.git.clean("-fdx")
                logger.info(f"Successfully checked out commit {commit_sha} for project {project_id}")
                return str(repo_path), commit_sha
            else:
                # Ensure branch exists locally
                if branch in repo.heads:
                    repo.heads[branch].checkout()
                else:
                    repo.git.checkout(f"origin/{branch}", b=branch)

                # Hard reset to remote state to avoid any local changes/conflicts
                repo.git.reset("--hard", f"origin/{branch}")
                repo.git.clean("-fdx") # Clean untracked files

                new_commit_sha = repo.head.commit.hexsha
                logger.info(f"Successfully checked out {branch} at {new_commit_sha} for project {project_id}")
                
                return str(repo_path), new_commit_sha

        except exc.GitCommandError as e:
            logger.error(f"Git command failed for project {project_id}: {e}")
            raise GitServiceException(f"Git execution failed: {e}")
        except Exception as e:
            logger.error(f"Failed to clone/update repository for project {project_id}: {e}")
            raise GitServiceException(f"Failed to prepare repository: {e}")
