"use client";

import { useAuth } from '@/hooks/use-auth';
import { LayoutDashboard, LogOut, Package, Server } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();

  if (loading) {
    return <div className="min-h-screen bg-neutral-950 flex items-center justify-center text-neutral-400">Loading...</div>;
  }

  if (!user) {
    return null; // Will redirect in useAuth
  }

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Projects', href: '/projects', icon: Package },
  ];

  return (
    <div className="min-h-screen bg-neutral-950 flex">
      {/* Sidebar */}
      <div className="w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col">
        <div className="p-6">
          <Link href="/dashboard" className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Server className="w-8 h-8 text-indigo-500" />
            Bonk
          </Link>
        </div>

        <nav className="flex-1 px-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${
                  isActive 
                    ? 'bg-indigo-600/10 text-indigo-400' 
                    : 'text-neutral-400 hover:bg-neutral-800 hover:text-white'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-neutral-800">
          <div className="flex items-center gap-3 px-4 py-3 text-sm text-neutral-400 mb-2">
            <div className="w-8 h-8 rounded-full bg-neutral-800 flex items-center justify-center text-white font-medium">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-white font-medium">{user.username}</p>
              <p className="truncate text-xs">{user.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-neutral-400 hover:bg-red-500/10 hover:text-red-400 transition-all font-medium text-sm"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
