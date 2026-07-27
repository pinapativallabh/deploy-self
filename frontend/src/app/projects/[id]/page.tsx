"use client";

import DashboardLayout from '@/components/layout/DashboardLayout';
import { apiClient } from '@/lib/api/client';
import { Project, Deployment, EnvironmentVariable } from '@/types';
import { ArrowLeft, Rocket, Settings, RotateCcw, Play, RefreshCw, Terminal, Plus, Trash2, ShieldAlert, ExternalLink, Square, PlaySquare, Trash } from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';

export default function ProjectDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const [project, setProject] = useState<Project | null>(null);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [envVars, setEnvVars] = useState<EnvironmentVariable[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  
  const [activeTab, setActiveTab] = useState<'deployments' | 'settings'>('deployments');
  const [newEnv, setNewEnv] = useState({ key: '', value: '' });

  const loadData = useCallback(async () => {
    try {
      const [projData, depsData, envsData] = await Promise.all([
        apiClient<Project>(`/projects/${projectId}`),
        apiClient<Deployment[]>(`/projects/${projectId}/deployments`),
        apiClient<EnvironmentVariable[]>(`/projects/${projectId}/environment`)
      ]);
      setProject(projData);
      setDeployments(depsData);
      setEnvVars(envsData);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
    // Poll for deployments every 5s if there are pending/building deployments
    const interval = setInterval(() => {
      apiClient<Deployment[]>(`/projects/${projectId}/deployments`)
        .then(setDeployments)
        .catch(console.error);
    }, 5000);
    return () => clearInterval(interval);
  }, [projectId, loadData]);

  const handleDeploy = async () => {
    setActionLoading(true);
    try {
      await apiClient(`/projects/${projectId}/deployments`, {
        method: 'POST',
        body: JSON.stringify({ branch: project?.default_branch })
      });
      await loadData();
    } catch (error) {
      console.error(error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestart = async () => {
    setActionLoading(true);
    try {
      await apiClient(`/projects/${projectId}/restart`, {
        method: 'POST',
      });
      await loadData();
    } catch (error) {
      console.error(error);
      alert('Failed to restart');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await apiClient(`/projects/${projectId}/stop`, { method: 'POST' });
      await loadData();
    } catch (error) {
      console.error(error);
      alert('Failed to stop');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async () => {
    setActionLoading(true);
    try {
      await apiClient(`/projects/${projectId}/start`, { method: 'POST' });
      await loadData();
    } catch (error) {
      console.error(error);
      alert('Failed to start');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemove = async () => {
    if (!confirm('Are you sure you want to remove the deployment?')) return;
    setActionLoading(true);
    try {
      await apiClient(`/projects/${projectId}/runtime`, { method: 'DELETE' });
      await loadData();
    } catch (error) {
      console.error(error);
      alert('Failed to remove deployment');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!confirm('Are you sure you want to delete this project? This will remove all deployments, code, and settings. This cannot be undone.')) return;
    setActionLoading(true);
    try {
      await apiClient(`/projects/${projectId}`, { method: 'DELETE' });
      router.push('/projects');
    } catch (error) {
      console.error(error);
      alert('Failed to delete project');
      setActionLoading(false);
    }
  };

  const handleRollback = async (deploymentId: string) => {
    if (!confirm('Are you sure you want to rollback to this deployment?')) return;
    setActionLoading(true);
    try {
      await apiClient(`/projects/${projectId}/deployments/${deploymentId}/rollback`, {
        method: 'POST',
      });
      await loadData();
    } catch (error) {
      console.error(error);
      alert('Rollback failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddEnv = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient(`/projects/${projectId}/environment`, {
        method: 'POST',
        body: JSON.stringify(newEnv)
      });
      setNewEnv({ key: '', value: '' });
      await loadData();
    } catch (error) {
      console.error(error);
    }
  };

  const handleDeleteEnv = async (id: string) => {
    try {
      await apiClient(`/projects/${projectId}/environment/${id}`, {
        method: 'DELETE'
      });
      await loadData();
    } catch (error) {
      console.error(error);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="animate-pulse space-y-8">
          <div className="h-10 w-1/3 bg-neutral-900 rounded"></div>
          <div className="h-32 bg-neutral-900 rounded-2xl"></div>
          <div className="h-64 bg-neutral-900 rounded-2xl"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (!project) {
    return (
      <DashboardLayout>
        <div className="text-center py-20">
          <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Project not found</h2>
          <Link href="/projects" className="text-indigo-400 hover:underline">Return to projects</Link>
        </div>
      </DashboardLayout>
    );
  }

  const activeDeployment = deployments.find(d => d.status === 'RUNNING');
  const sortedDeployments = [...deployments].sort((a, b) => b.deployment_number - a.deployment_number);

  const StatusBadge = ({ status }: { status: string }) => {
    const colors: Record<string, string> = {
      'RUNNING': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      'PENDING': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      'BUILDING': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      'STARTING': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      'FAILED': 'bg-red-500/10 text-red-400 border-red-500/20',
      'CANCELED': 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20',
      'ARCHIVED': 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20',
    };
    return (
      <span className={`px-2.5 py-1 text-xs font-medium border rounded-full ${colors[status] || 'bg-neutral-800 text-neutral-400'}`}>
        {status}
      </span>
    );
  };

  return (
    <DashboardLayout>
      <div className="mb-6">
        <Link href="/projects" className="inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors mb-4">
          <ArrowLeft className="w-4 h-4" />
          Projects
        </Link>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              {project.name}
              {activeDeployment && <span className="flex h-3 w-3 relative"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span></span>}
            </h1>
            <p className="text-neutral-400 mt-1 font-mono text-sm">{project.repository_url}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {activeDeployment && (
              <>
                {activeDeployment.deployment_url && (
                  <a 
                    href={activeDeployment.deployment_url}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Open Application
                  </a>
                )}
                <button 
                  onClick={handleRestart}
                  disabled={actionLoading}
                  className="bg-neutral-800 hover:bg-neutral-700 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                  title="Restart Deployment"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button 
                  onClick={handleStop}
                  disabled={actionLoading}
                  className="bg-neutral-800 hover:bg-neutral-700 text-amber-400 px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                  title="Stop Deployment"
                >
                  <Square className="w-4 h-4" />
                </button>
                <button 
                  onClick={handleStart}
                  disabled={actionLoading}
                  className="bg-neutral-800 hover:bg-neutral-700 text-emerald-400 px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                  title="Start Deployment"
                >
                  <PlaySquare className="w-4 h-4" />
                </button>
                <button 
                  onClick={handleRemove}
                  disabled={actionLoading}
                  className="bg-neutral-800 hover:bg-red-900/50 text-red-400 px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                  title="Remove Deployment"
                >
                  <Trash className="w-4 h-4" />
                </button>
              </>
            )}
            <button 
              onClick={handleDeploy}
              disabled={actionLoading}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <Rocket className="w-4 h-4" />
              Deploy Now
            </button>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6 border-b border-neutral-800 mb-8">
        <button 
          onClick={() => setActiveTab('deployments')}
          className={`pb-4 text-sm font-medium transition-colors relative ${activeTab === 'deployments' ? 'text-indigo-400' : 'text-neutral-400 hover:text-white'}`}
        >
          <div className="flex items-center gap-2"><Play className="w-4 h-4" /> Deployments</div>
          {activeTab === 'deployments' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-t-full"></div>}
        </button>
        <button 
          onClick={() => setActiveTab('settings')}
          className={`pb-4 text-sm font-medium transition-colors relative ${activeTab === 'settings' ? 'text-indigo-400' : 'text-neutral-400 hover:text-white'}`}
        >
          <div className="flex items-center gap-2"><Settings className="w-4 h-4" /> Settings & Env</div>
          {activeTab === 'settings' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-t-full"></div>}
        </button>
      </div>

      {activeTab === 'deployments' && (
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-neutral-800 flex justify-between items-center">
            <h2 className="text-lg font-bold text-white">Deployment History</h2>
            <span className="text-sm text-neutral-400">{deployments.length} total deployments</span>
          </div>
          
          {deployments.length === 0 ? (
            <div className="p-12 text-center text-neutral-400">
              No deployments yet. Click &quot;Deploy Now&quot; to start your first deployment.
            </div>
          ) : (
            <div className="divide-y divide-neutral-800/50">
              {sortedDeployments.map((dep) => (
                <div key={dep.id} className="p-6 hover:bg-neutral-800/30 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="mt-1">
                      <StatusBadge status={dep.status} />
                    </div>
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-white font-medium">#{dep.deployment_number}</span>
                        <span className="text-neutral-400 text-sm">branch: {dep.branch}</span>
                        {dep.commit_sha && (
                          <span className="text-neutral-500 font-mono text-xs bg-neutral-950 px-2 py-0.5 rounded border border-neutral-800">
                            {dep.commit_sha.substring(0, 7)}
                          </span>
                        )}
                        {dep.deployment_url && (
                          <span className="text-indigo-400 text-sm flex items-center gap-1 ml-2">
                            <ExternalLink className="w-3 h-3" />
                            <a href={dep.deployment_url} target="_blank" rel="noreferrer" className="hover:underline">
                              {dep.deployment_url}
                            </a>
                          </span>
                        )}
                        {dep.host_port && (
                          <span className="text-neutral-500 text-xs ml-2">Port: {dep.host_port}</span>
                        )}
                      </div>
                      <div className="text-xs text-neutral-500">
                        {dep.finished_at 
                          ? `Finished ${formatDistanceToNow(new Date(dep.finished_at))} ago` 
                          : `Started ${formatDistanceToNow(new Date(dep.created_at))} ago`}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Link 
                      href={`/projects/${projectId}/deployments/${dep.id}/logs`}
                      className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-lg transition-colors"
                      title="View Logs"
                    >
                      <Terminal className="w-5 h-5" />
                    </Link>
                    {(dep.status === 'RUNNING' || dep.status === 'ARCHIVED') && (
                      <button 
                        onClick={() => handleRollback(dep.id)}
                        disabled={actionLoading || dep.status === 'RUNNING'}
                        className="p-2 text-neutral-400 hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-neutral-400"
                        title={dep.status === 'RUNNING' ? "Current active deployment" : "Rollback to this version"}
                      >
                        <RotateCcw className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="space-y-6">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-neutral-800">
              <h2 className="text-lg font-bold text-white mb-1">Environment Variables</h2>
              <p className="text-sm text-neutral-400">Manage secrets and configuration for your app.</p>
            </div>
            
            <div className="p-6">
              <form onSubmit={handleAddEnv} className="flex gap-4 mb-8">
                <input 
                  required
                  placeholder="KEY (e.g. DATABASE_URL)"
                  value={newEnv.key}
                  onChange={e => setNewEnv({...newEnv, key: e.target.value.toUpperCase()})}
                  className="flex-1 bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-2 text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <input 
                  required
                  placeholder="VALUE"
                  type="password"
                  value={newEnv.value}
                  onChange={e => setNewEnv({...newEnv, value: e.target.value})}
                  className="flex-1 bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-2 text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <button type="submit" className="bg-neutral-800 hover:bg-neutral-700 text-white px-4 py-2 rounded-xl flex items-center justify-center transition-colors">
                  <Plus className="w-5 h-5" />
                </button>
              </form>

              {envVars.length === 0 ? (
                <div className="text-center py-8 text-neutral-500 text-sm">
                  No environment variables defined.
                </div>
              ) : (
                <div className="border border-neutral-800 rounded-xl overflow-hidden">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-neutral-950 border-b border-neutral-800 text-neutral-400">
                      <tr>
                        <th className="px-4 py-3 font-medium">Key</th>
                        <th className="px-4 py-3 font-medium w-16">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-800">
                      {envVars.map(env => (
                        <tr key={env.id} className="hover:bg-neutral-800/30">
                          <td className="px-4 py-3 font-mono text-neutral-300">{env.key}</td>
                          <td className="px-4 py-3">
                            <button onClick={() => handleDeleteEnv(env.id)} className="text-neutral-500 hover:text-red-400 transition-colors">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
          
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl overflow-hidden">
             <div className="p-6 border-b border-neutral-800">
              <h2 className="text-lg font-bold text-white mb-1">Project Details</h2>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div>
                <span className="block text-neutral-500 mb-1">Repository</span>
                <span className="text-white font-mono">{project.repository_url}</span>
              </div>
              <div>
                <span className="block text-neutral-500 mb-1">Default Branch</span>
                <span className="text-white font-mono">{project.default_branch}</span>
              </div>
              <div>
                <span className="block text-neutral-500 mb-1">Build Context</span>
                <span className="text-white font-mono">{project.build_context}</span>
              </div>
              <div>
                <span className="block text-neutral-500 mb-1">Dockerfile</span>
                <span className="text-white font-mono">{project.dockerfile_path}</span>
              </div>
            </div>
          </div>
          <div className="bg-red-950/20 border border-red-900/50 rounded-2xl overflow-hidden">
             <div className="p-6 border-b border-red-900/50">
              <h2 className="text-lg font-bold text-red-500 mb-1">Danger Zone</h2>
              <p className="text-sm text-red-400/80">Irreversible and destructive actions.</p>
            </div>
            <div className="p-6">
              <button 
                onClick={handleDeleteProject}
                disabled={actionLoading}
                className="bg-red-600 hover:bg-red-700 text-white px-5 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
                Delete Project
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
