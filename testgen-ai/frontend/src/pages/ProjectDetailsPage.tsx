import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { Input } from '../components/UI/Input';
import { 
  ArrowLeft,
  Plus, 
  FileText, 
  Globe, 
  GitBranch,
  Zap,
  ExternalLink,
  Calendar,
  MoreVertical,
  Edit,
  Trash2,
  Download,
  Eye
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';

export default function ProjectDetailsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [showAddContextModal, setShowAddContextModal] = useState(false);
  const [newContextSource, setNewContextSource] = useState({
    source_type: 'jira' as 'jira' | 'url' | 'file',
    source_config: {} as Record<string, any>,
  });

  const queryClient = useQueryClient();

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => apiClient.getProject(Number(projectId)),
    enabled: !!projectId,
  });

  const { data: contextSources = [], isLoading: contextsLoading } = useQuery({
    queryKey: ['contextSources', projectId],
    queryFn: () => apiClient.getContextSources(Number(projectId)),
    enabled: !!projectId,
  });

  const { data: testGenerations = [], isLoading: generationsLoading } = useQuery({
    queryKey: ['testGenerations', projectId],
    queryFn: () => apiClient.getTestGenerations(Number(projectId)),
    enabled: !!projectId,
  });

  const addContextMutation = useMutation({
    mutationFn: (contextData: any) => apiClient.createContextSource(Number(projectId), contextData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contextSources', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      setShowAddContextModal(false);
      setNewContextSource({ source_type: 'jira', source_config: {} });
      toast.success('Context source added successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to add context source');
    },
  });

  const deleteContextMutation = useMutation({
    mutationFn: (sourceId: number) => apiClient.deleteContextSource(Number(projectId), sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contextSources', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      toast.success('Context source deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete context source');
    },
  });

  const handleAddContext = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate based on source type
    let config = {};
    if (newContextSource.source_type === 'jira') {
      const jiraUrl = (e.target as any).jira_url?.value;
      const username = (e.target as any).username?.value;
      const apiToken = (e.target as any).api_token?.value;
      const issueKeys = (e.target as any).issue_keys?.value;
      
      if (!jiraUrl || !username || !apiToken || !issueKeys) {
        toast.error('Please fill in all Jira fields');
        return;
      }
      
      config = {
        jira_url: jiraUrl,
        username: username,
        api_token: apiToken,
        issue_keys: issueKeys.split(',').map((key: string) => key.trim()),
      };
    } else if (newContextSource.source_type === 'url') {
      const url = (e.target as any).url?.value;
      if (!url) {
        toast.error('Please enter a URL');
        return;
      }
      config = { url };
    }
    
    addContextMutation.mutate({
      source_type: newContextSource.source_type,
      source_config: config,
    });
  };

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'jira':
        return <FileText className="w-5 h-5 text-blue-600" />;
      case 'url':
        return <Globe className="w-5 h-5 text-green-600" />;
      case 'file':
        return <GitBranch className="w-5 h-5 text-purple-600" />;
      default:
        return <FileText className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'processing':
        return <Badge variant="warning">Processing</Badge>;
      case 'failed':
        return <Badge variant="error">Failed</Badge>;
      default:
        return <Badge variant="secondary">Pending</Badge>;
    }
  };

  if (projectLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded animate-pulse"></div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64 bg-gray-200 rounded-lg animate-pulse"></div>
          <div className="h-64 bg-gray-200 rounded-lg animate-pulse"></div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Project not found</h2>
        <p className="text-gray-600 mb-4">The project you're looking for doesn't exist.</p>
        <Link to="/projects">
          <Button>Back to Projects</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/projects">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{project.name}</h1>
            <p className="text-gray-600 mt-1">
              {project.description || 'No description provided'}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <Button onClick={() => setShowAddContextModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Context
          </Button>
          {contextSources.length > 0 && (
            <Link to={`/projects/${projectId}/generate`}>
              <Button>
                <Zap className="w-4 h-4 mr-2" />
                Generate Tests
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Project Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Project Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {project.application_url && (
              <div className="flex items-center space-x-2">
                <ExternalLink className="w-4 h-4 text-gray-400" />
                <a
                  href={project.application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary-600 hover:text-primary-700 truncate"
                >
                  {project.application_url}
                </a>
              </div>
            )}
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <Calendar className="w-4 h-4" />
              <span>
                Created {formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}
              </span>
            </div>
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-1">
                <FileText className="w-4 h-4 text-gray-400" />
                <span className="text-gray-600">
                  {contextSources.length} context sources
                </span>
              </div>
              <div className="flex items-center space-x-1">
                <Zap className="w-4 h-4 text-gray-400" />
                <span className="text-gray-600">
                  {testGenerations.length} generations
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Context Sources</CardTitle>
            <CardDescription>
              Sources of context for test generation
            </CardDescription>
          </CardHeader>
          <CardContent>
            {contextSources.length > 0 ? (
              <div className="space-y-3">
                {contextSources.map((source) => (
                  <div key={source.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      {getSourceIcon(source.source_type)}
                      <div>
                        <p className="font-medium text-gray-900 capitalize">
                          {source.source_type} Source
                        </p>
                        <p className="text-sm text-gray-600">
                          {formatDistanceToNow(new Date(source.created_at), { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteContextMutation.mutate(source.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600 mb-3">No context sources yet</p>
                <Button size="sm" onClick={() => setShowAddContextModal(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Context Source
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Generations</CardTitle>
            <CardDescription>
              Latest test generation attempts
            </CardDescription>
          </CardHeader>
          <CardContent>
            {testGenerations.length > 0 ? (
              <div className="space-y-3">
                {testGenerations.slice(0, 3).map((generation) => (
                  <div key={generation.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">{generation.feature_name}</p>
                      <p className="text-sm text-gray-600">
                        {formatDistanceToNow(new Date(generation.created_at), { addSuffix: true })}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      {getStatusBadge(generation.status)}
                      {generation.status === 'completed' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            // Download files
                            apiClient.downloadGenerationFiles(generation.id).then(blob => {
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `${generation.feature_name}_tests.zip`;
                              document.body.appendChild(a);
                              a.click();
                              document.body.removeChild(a);
                              URL.revokeObjectURL(url);
                            });
                          }}
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6">
                <Zap className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600 mb-3">No generations yet</p>
                <p className="text-sm text-gray-500">
                  Add context sources to start generating tests
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add Context Modal */}
      {showAddContextModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Add Context Source</CardTitle>
              <CardDescription>
                Add a new source of context for test generation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAddContext} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source Type
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    value={newContextSource.source_type}
                    onChange={(e) => setNewContextSource(prev => ({ 
                      ...prev, 
                      source_type: e.target.value as 'jira' | 'url' | 'file' 
                    }))}
                  >
                    <option value="jira">Jira Issues</option>
                    <option value="url">Web Application</option>
                    <option value="file">Documentation File</option>
                  </select>
                </div>

                {newContextSource.source_type === 'jira' && (
                  <>
                    <Input
                      label="Jira URL"
                      placeholder="https://yourcompany.atlassian.net"
                      name="jira_url"
                      required
                    />
                    <Input
                      label="Username"
                      placeholder="your.email@company.com"
                      name="username"
                      required
                    />
                    <Input
                      label="API Token"
                      type="password"
                      placeholder="Your Jira API token"
                      name="api_token"
                      required
                    />
                    <Input
                      label="Issue Keys"
                      placeholder="PROJ-123, PROJ-124, PROJ-125"
                      name="issue_keys"
                      helperText="Comma-separated list of Jira issue keys"
                      required
                    />
                  </>
                )}

                {newContextSource.source_type === 'url' && (
                  <Input
                    label="Application URL"
                    type="url"
                    placeholder="https://example.com"
                    name="url"
                    required
                  />
                )}

                {newContextSource.source_type === 'file' && (
                  <div className="text-center py-8">
                    <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600">File upload coming soon</p>
                  </div>
                )}

                <div className="flex items-center space-x-3 pt-4">
                  <Button
                    type="submit"
                    loading={addContextMutation.isPending}
                    className="flex-1"
                    disabled={newContextSource.source_type === 'file'}
                  >
                    Add Context Source
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowAddContextModal(false)}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
