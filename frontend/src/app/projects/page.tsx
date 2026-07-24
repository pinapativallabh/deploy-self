"use client";

import DashboardLayout from '@/components/layout/DashboardLayout';
import { apiClient } from '@/lib/api/client';
import { Project } from '@/types';
import { Package, Plus, GitBranch, FileCode } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProjects() {
      try {
        const data = await apiClient<Project[]>('/projects');
        setProjects(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }
    loadProjects();
  }, []);

  return (
    <DashboardLayout>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-1">Projects</h1>
          <p className="text-neutral-400">Manage your applications and deployments</p>
        </div>
        <Link 
          href="/projects/new"
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors flex items-center gap-2 shadow-lg shadow-indigo-500/20"
        >
          <Plus className="w-5 h-5" />
          New Project
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="h-48 bg-neutral-900 border border-neutral-800 rounded-2xl animate-pulse"></div>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-neutral-900 border border-neutral-800 border-dashed rounded-2xl p-16 text-center max-w-2xl mx-auto mt-12">
          <div className="w-20 h-20 bg-neutral-800 rounded-full flex items-center justify-center mx-auto mb-6">
            <Package className="w-10 h-10 text-neutral-500" />
          </div>
          <h3 className="text-2xl font-bold text-white mb-3">No projects found</h3>
          <p className="text-neutral-400 mb-8 max-w-md mx-auto leading-relaxed">
            You haven't created any projects yet. Get started by creating your first project and deploying your application.
          </p>
          <Link 
            href="/projects/new"
            className="inline-flex items-center gap-2 bg-white text-black hover:bg-neutral-200 px-6 py-3 rounded-xl font-semibold transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
          >
            <Plus className="w-5 h-5" />
            Create Your First Project
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {projects.map(project => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <div className="bg-neutral-900 hover:bg-neutral-800/80 border border-neutral-800 hover:border-neutral-600 transition-all duration-200 rounded-2xl p-6 group cursor-pointer h-full flex flex-col relative overflow-hidden">
                {/* Decorative gradient blob */}
                <div className="absolute -top-12 -right-12 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl group-hover:bg-indigo-500/20 transition-all duration-500"></div>
                
                <div className="relative">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-xl font-bold text-white group-hover:text-indigo-400 transition-colors">{project.name}</h3>
                  </div>
                  
                  <p className="text-sm text-neutral-400 mb-6 flex-1 line-clamp-2 min-h-[2.5rem]">
                    {project.description || 'No description provided for this project.'}
                  </p>
                  
                  <div className="space-y-3 pt-4 border-t border-neutral-800/60">
                    <div className="flex items-center gap-2 text-xs text-neutral-400">
                      <FileCode className="w-4 h-4 text-neutral-500" />
                      <span className="truncate">{project.repository_url.split('/').slice(-2).join('/') || project.repository_url}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-neutral-400">
                      <GitBranch className="w-4 h-4 text-neutral-500" />
                      <span className="font-medium bg-neutral-800 px-2 py-0.5 rounded text-neutral-300">{project.default_branch}</span>
                    </div>
                  </div>
                  
                  <div className="mt-6 flex items-center justify-between text-xs text-neutral-500 font-medium">
                    <span>Created {formatDistanceToNow(new Date(project.created_at))} ago</span>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
