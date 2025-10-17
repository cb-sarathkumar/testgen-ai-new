import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { 
  Plus, 
  FolderOpen, 
  Zap, 
  Clock, 
  CheckCircle, 
  XCircle,
  TrendingUp,
  FileText,
  Globe,
  GitBranch
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function Dashboard() {
  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.getProjects(),
  });

  const { data: user } = useQuery({
    queryKey: ['user'],
    queryFn: () => apiClient.getCurrentUser(),
  });

  // Calculate stats
  const totalProjects = projects.length;
  const totalContextSources = projects.reduce((sum, project) => sum + project.context_sources_count, 0);
  const totalGenerations = projects.reduce((sum, project) => sum + project.test_generations_count, 0);
  const recentProjects = projects.slice(0, 3);

  const quickActions = [
    {
      title: 'New Project',
      description: 'Create a new test project',
      icon: Plus,
      href: '/projects',
      color: 'bg-primary-500',
    },
    {
      title: 'Setup Integrations',
      description: 'Configure AI and Jira APIs',
      icon: Zap,
      href: '/integrations',
      color: 'bg-green-500',
    },
    {
      title: 'View Projects',
      description: 'Manage your test projects',
      icon: FolderOpen,
      href: '/projects',
      color: 'bg-blue-500',
    },
  ];

  const contextTypes = [
    {
      name: 'Jira Issues',
      icon: FileText,
      description: 'Extract user stories and acceptance criteria',
      color: 'text-blue-600',
    },
    {
      name: 'Web Applications',
      icon: Globe,
      description: 'Analyze live applications and forms',
      color: 'text-green-600',
    },
    {
      name: 'Documentation',
      icon: GitBranch,
      description: 'Process requirements and API specs',
      color: 'text-purple-600',
    },
  ];

  if (projectsLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded animate-pulse"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-200 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.full_name?.split(' ')[0]}!
          </h1>
          <p className="text-gray-600 mt-1">
            Generate intelligent test cases with AI-powered automation
          </p>
        </div>
        <Link to="/projects">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-primary-100 rounded-lg">
                <FolderOpen className="w-6 h-6 text-primary-600" />
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">{totalProjects}</p>
                <p className="text-sm text-gray-600">Total Projects</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <FileText className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">{totalContextSources}</p>
                <p className="text-sm text-gray-600">Context Sources</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Zap className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">{totalGenerations}</p>
                <p className="text-sm text-gray-600">Test Generations</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">
                  {user?.api_quotas.openai + user?.api_quotas.anthropic || 0}
                </p>
                <p className="text-sm text-gray-600">API Quota</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Get started with common tasks
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <Link
                  key={action.title}
                  to={action.href}
                  className="flex items-center p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className={`p-2 rounded-lg ${action.color}`}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <div className="ml-3">
                    <p className="font-medium text-gray-900">{action.title}</p>
                    <p className="text-sm text-gray-600">{action.description}</p>
                  </div>
                </Link>
              );
            })}
          </CardContent>
        </Card>

        {/* Recent Projects */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Projects</CardTitle>
            <CardDescription>
              Your latest test projects
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recentProjects.length > 0 ? (
              <div className="space-y-3">
                {recentProjects.map((project) => (
                  <Link
                    key={project.id}
                    to={`/projects/${project.id}`}
                    className="block p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{project.name}</p>
                        <p className="text-sm text-gray-600">
                          {project.context_sources_count} sources • {project.test_generations_count} generations
                        </p>
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}
                      </div>
                    </div>
                  </Link>
                ))}
                {projects.length > 3 && (
                  <Link
                    to="/projects"
                    className="block text-center text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    View all projects
                  </Link>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <FolderOpen className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600 mb-3">No projects yet</p>
                <Link to="/projects">
                  <Button size="sm">Create your first project</Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Context Sources */}
        <Card>
          <CardHeader>
            <CardTitle>Context Sources</CardTitle>
            <CardDescription>
              Supported integration types
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {contextTypes.map((source) => {
              const Icon = source.icon;
              return (
                <div key={source.name} className="flex items-center space-x-3">
                  <Icon className={`w-5 h-5 ${source.color}`} />
                  <div>
                    <p className="font-medium text-gray-900">{source.name}</p>
                    <p className="text-sm text-gray-600">{source.description}</p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      {/* Getting Started */}
      {totalProjects === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Getting Started</CardTitle>
            <CardDescription>
              Follow these steps to start generating intelligent test cases
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-primary-600 font-bold">1</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Setup Integrations</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Configure your OpenAI or Anthropic API keys and Jira credentials
                </p>
                <Link to="/integrations">
                  <Button variant="outline" size="sm">Setup APIs</Button>
                </Link>
              </div>
              
              <div className="text-center">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-green-600 font-bold">2</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Create Project</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Create a new project and add context sources from Jira or web apps
                </p>
                <Link to="/projects">
                  <Button variant="outline" size="sm">New Project</Button>
                </Link>
              </div>
              
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-blue-600 font-bold">3</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Generate Tests</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Use AI to generate comprehensive Cucumber Selenium test suites
                </p>
                <Button variant="outline" size="sm" disabled>
                  Generate Tests
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
