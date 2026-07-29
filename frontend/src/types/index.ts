export interface User {
  id: string;
  email: string;
  username: string;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  repository_url: string;
  default_branch: string;
  dockerfile_path: string;
  build_context: string;
  health_check_path: string | null;
  active_deployment_id: string | null;
  created_at: string;
  updated_at: string;
}

export type DeploymentStatus = 'PENDING' | 'CLONING' | 'BUILDING' | 'STARTING' | 'RUNNING' | 'FAILED' | 'CANCELED' | 'ARCHIVED';

export interface Deployment {
  id: string;
  project_id: string;
  deployment_number: number;
  status: DeploymentStatus;
  branch: string;
  commit_sha: string | null;
  host_port?: number;
  deployment_url?: string;
  created_at: string;
  finished_at: string | null;
}

export interface EnvironmentVariable {
  id: string;
  project_id: string;
  key: string;
  value: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
}
