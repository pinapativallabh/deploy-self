"use client";

import DashboardLayout from '@/components/layout/DashboardLayout';
import { apiClient } from '@/lib/api/client';
import { Project } from '@/types';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function NewProjectPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    repository_url: '',
    default_branch: 'master',
    dockerfile_path: 'Dockerfile',
    build_context: '.',
    health_check_path: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const payload: Record<string, string> = { ...formData };
      if (!payload.description) delete payload.description;
      if (!payload.health_check_path) payload.health_check_path = '/health';

      const project = await apiClient<Project>('/projects', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      router.push(`/projects/${project.id}`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to create project');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="mb-8">
        <Link href="/projects" className="inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors mb-4">
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </Link>
        <h1 className="text-3xl font-bold text-white tracking-tight mb-1">Create New Project</h1>
        <p className="text-neutral-400">Configure a new repository for deployment</p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-3xl bg-neutral-900 border border-neutral-800 rounded-2xl p-8">
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-xl mb-6 text-sm flex items-start gap-3">
            <div className="mt-0.5">⚠️</div>
            <div>{error}</div>
          </div>
        )}

        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">Project Name *</label>
              <input
                name="name"
                required
                value={formData.name}
                onChange={handleChange}
                placeholder="my-awesome-app"
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">Repository URL *</label>
              <input
                name="repository_url"
                required
                value={formData.repository_url}
                onChange={handleChange}
                placeholder="https://github.com/user/repo.git"
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-2">Description</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows={3}
              placeholder="A brief description of your project..."
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all resize-none"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 border-t border-neutral-800">
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">Default Branch</label>
              <input
                name="default_branch"
                required
                value={formData.default_branch}
                onChange={handleChange}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all font-mono text-sm"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">Dockerfile Path</label>
              <input
                name="dockerfile_path"
                required
                value={formData.dockerfile_path}
                onChange={handleChange}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all font-mono text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">Build Context</label>
              <input
                name="build_context"
                required
                value={formData.build_context}
                onChange={handleChange}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all font-mono text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">Health Check Path (Optional)</label>
              <input
                name="health_check_path"
                value={formData.health_check_path}
                onChange={handleChange}
                placeholder="/api/health"
                className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all font-mono text-sm"
              />
            </div>
          </div>
        </div>

        <div className="mt-10 flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl px-8 py-3 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </DashboardLayout>
  );
}
