import logging
import os
from pathlib import Path

from git import Repo, exc
from app.core.config import settings

logger = logging.getLogger(__name__)

class GitServiceException(Exception):
    pass


class GitService:
    @staticmethod
    def get_clone_base_dir() -> Path:
        base_dir = Path(settings.REPO_CACHE_PATH)
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    @staticmethod
    def clone_repo(repository_url: str, branch: str, project_id: str, commit_sha: str = None) -> tuple[str, str]:
        """
        Clones a repository, or fetches and checks out the branch if already cloned.
        If commit_sha is provided, it will check out that specific commit.
        Returns a tuple of (local_repository_path, commit_sha).
        """
        try:
            base_dir = GitService.get_clone_base_dir()
            repo_path = base_dir / str(project_id)

            # Prevent terminal prompts and apply basic timeouts for git clone
            git_env = {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_SSH_COMMAND": f"ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout={settings.GIT_CLONE_TIMEOUT}",
            }

            if repo_path.exists() and (repo_path / ".git").exists():
                logger.info(f"Reusing existing clone at {repo_path} for project {project_id}")
                repo = Repo(repo_path)
                
                # Fetch all remotes
                for remote in repo.remotes:
                    remote.fetch(env=git_env)

            else:
                logger.info(f"Cloning {repository_url} to {repo_path} for project {project_id}")
                repo = Repo.clone_from(repository_url, repo_path, env=git_env)

            if commit_sha:
                repo.git.reset("--hard")
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

    @staticmethod
    def delete_repo(project_id: str) -> None:
        import shutil
        import stat
        
        base_dir = GitService.get_clone_base_dir()
        repo_path = base_dir / str(project_id)
        
        if not repo_path.exists():
            return
            
        def handle_remove_readonly(func, path, exc):
            import errno
            excvalue = exc[1]
            if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) # 0777
                func(path)
            else:
                raise
                
        try:
            shutil.rmtree(repo_path, ignore_errors=False, onerror=handle_remove_readonly)
            logger.info(f"Successfully deleted repository cache for project {project_id}")
        except Exception as e:
            logger.error(f"Failed to delete repository cache for project {project_id}: {e}")
