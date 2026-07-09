export interface User {
  id: string;
  email: string;
  name?: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Service {
  id: string;
  projectId: string;
  name: string;
  repoUrl: string;
  branch: string;
  status: 'idle' | 'building' | 'deploying' | 'running' | 'failed' | 'stopped';
}

export interface Deployment {
  id: string;
  serviceId: string;
  status: 'queued' | 'building' | 'deploying' | 'success' | 'failed';
  commitHash?: string;
  commitMessage?: string;
  startedAt: string;
  finishedAt?: string;
}
