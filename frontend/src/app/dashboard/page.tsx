"use client";

import DashboardLayout from '@/components/layout/DashboardLayout';
import { apiClient } from '@/lib/api/client';
import { Project } from '@/types';
import { Package, Activity, Clock, Plus } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const data = await apiClient<Project[]>('/projects');
        setProjects(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
    const interval = setInterval(loadDashboard, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <DashboardLayout>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-1">Dashboard</h1>
          <p className="text-neutral-400">Overview of your infrastructure</p>
        </div>
        <Link 
          href="/projects/new"
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          New Project
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-indigo-500/10 text-indigo-400 rounded-xl flex items-center justify-center">
              <Package className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-400">Total Projects</p>
              <p className="text-2xl font-bold text-white">{loading ? '-' : projects.length}</p>
            </div>
          </div>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-emerald-500/10 text-emerald-400 rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-400">Active Deployments</p>
              <p className="text-2xl font-bold text-white">{loading ? '-' : projects.filter(p => p.active_deployment_id).length}</p>
            </div>
          </div>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-500/10 text-blue-400 rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-400">System Status</p>
              <p className="text-2xl font-bold text-emerald-400">Online</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-bold text-white mb-6">Recent Projects</h2>
        
        {loading ? (
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 bg-neutral-900 border border-neutral-800 rounded-2xl"></div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-neutral-900 border border-neutral-800 border-dashed rounded-2xl p-12 text-center">
            <Package className="w-12 h-12 text-neutral-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No projects yet</h3>
            <p className="text-neutral-400 mb-6">Create your first project to start deploying.</p>
            <Link 
              href="/projects/new"
              className="inline-flex items-center gap-2 bg-white text-black hover:bg-neutral-200 px-5 py-2.5 rounded-xl font-medium transition-colors"
            >
              <Plus className="w-5 h-5" />
              Create Project
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {projects.slice(0, 4).map(project => (
              <Link key={project.id} href={`/projects/${project.id}`}>
                <div className="bg-neutral-900 hover:bg-neutral-800/80 border border-neutral-800 hover:border-neutral-700 transition-all rounded-2xl p-6 group cursor-pointer h-full flex flex-col">
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors">{project.name}</h3>
                    <span className="px-2.5 py-1 text-xs font-medium bg-neutral-800 text-neutral-300 rounded-md">
                      {project.default_branch}
                    </span>
                  </div>
                  <p className="text-sm text-neutral-400 mb-6 flex-1 line-clamp-2">
                    {project.description || 'No description provided.'}
                  </p>
                  <div className="text-xs text-neutral-500 font-mono truncate">
                    {project.repository_url}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
