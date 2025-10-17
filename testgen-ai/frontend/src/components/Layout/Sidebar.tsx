import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderOpen, 
  Zap, 
  Settings,
  Plus,
  FileText,
  Globe,
  GitBranch
} from 'lucide-react';
import { cn } from '../../utils/cn';

export default function Sidebar() {
  const location = useLocation();

  const navigation = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: LayoutDashboard,
    },
    {
      name: 'Projects',
      href: '/projects',
      icon: FolderOpen,
    },
    {
      name: 'Integrations',
      href: '/integrations',
      icon: Settings,
    },
  ];

  const isActive = (path: string) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 min-h-screen">
      <div className="p-6">
        <div className="space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                  isActive(item.href)
                    ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-500'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.name}
              </Link>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div className="mt-8">
          <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Quick Actions
          </h3>
          <div className="mt-2 space-y-1">
            <Link
              to="/projects"
              className="flex items-center px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4 mr-3" />
              New Project
            </Link>
            <Link
              to="/integrations"
              className="flex items-center px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition-colors"
            >
              <Zap className="w-4 h-4 mr-3" />
              Setup AI
            </Link>
          </div>
        </div>

        {/* Context Sources Info */}
        <div className="mt-8">
          <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Context Sources
          </h3>
          <div className="mt-2 space-y-1">
            <div className="flex items-center px-3 py-2 text-sm text-gray-600">
              <FileText className="w-4 h-4 mr-3" />
              Jira Issues
            </div>
            <div className="flex items-center px-3 py-2 text-sm text-gray-600">
              <Globe className="w-4 h-4 mr-3" />
              Web Apps
            </div>
            <div className="flex items-center px-3 py-2 text-sm text-gray-600">
              <GitBranch className="w-4 h-4 mr-3" />
              Documentation
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
