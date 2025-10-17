import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { useWebSocket } from '../hooks/useWebSocket';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { Input } from '../components/UI/Input';
import { ProgressBar } from '../components/UI/ProgressBar';
import { LoadingSpinner } from '../components/UI/LoadingSpinner';
import { CodePreview } from '../components/CodePreview';
import { 
  ArrowLeft,
  Zap, 
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Download,
  Eye,
  Settings,
  FileText,
  Globe,
  GitBranch
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';

export default function GenerationPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [generationConfig, setGenerationConfig] = useState({
    feature_name: '',
    llm_provider: 'openai',
    model: 'gpt-4',
    max_tokens: 4000,
    temperature: 0.1,
  });
  const [currentGeneration, setCurrentGeneration] = useState<any>(null);
  const [generatedFiles, setGeneratedFiles] = useState<Record<string, string>>({});

  const queryClient = useQueryClient();

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => apiClient.getProject(Number(projectId)),
    enabled: !!projectId,
  });

  const { data: contextSources = [] } = useQuery({
    queryKey: ['contextSources', projectId],
    queryFn: () => apiClient.getContextSources(Number(projectId)),
    enabled: !!projectId,
  });

  const { data: testGenerations = [] } = useQuery({
    queryKey: ['testGenerations', projectId],
    queryFn: () => apiClient.getTestGenerations(Number(projectId)),
    enabled: !!projectId,
  });

  // WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useWebSocket(
    currentGeneration?.id ? String(currentGeneration.id) : null,
    {
      onMessage: (message) => {
        if (message.status === 'processing') {
          toast.success(`Generation progress: ${message.stage} (${message.progress}%)`);
        } else if (message.status === 'completed') {
          setGeneratedFiles(message.files || {});
          toast.success('Test generation completed successfully!');
          queryClient.invalidateQueries({ queryKey: ['testGenerations', projectId] });
        } else if (message.status === 'failed') {
          toast.error(`Generation failed: ${message.error}`);
        }
      },
    }
  );

  const createGenerationMutation = useMutation({
    mutationFn: (config: any) => apiClient.createTestGeneration(Number(projectId), config),
    onSuccess: (generation) => {
      setCurrentGeneration(generation);
      toast.success('Test generation started!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start generation');
    },
  });

  const handleStartGeneration = (e: React.FormEvent) => {
    e.preventDefault();
    if (!generationConfig.feature_name.trim()) {
      toast.error('Feature name is required');
      return;
    }
    
    // Format the data according to the backend API
    const requestData = {
      feature_name: generationConfig.feature_name,
      config: {
        llm_provider: generationConfig.llm_provider,
        model: generationConfig.model,
        max_tokens: generationConfig.max_tokens,
        temperature: generationConfig.temperature,
      }
    };
    
    createGenerationMutation.mutate(requestData);
  };

  const handleDownloadFiles = async () => {
    if (!currentGeneration) return;
    
    try {
      const blob = await apiClient.downloadGenerationFiles(currentGeneration.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${generationConfig.feature_name}_tests.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Files downloaded successfully!');
    } catch (error) {
      toast.error('Failed to download files');
    }
  };

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'jira':
        return <FileText className="w-4 h-4 text-blue-600" />;
      case 'url':
        return <Globe className="w-4 h-4 text-green-600" />;
      case 'file':
        return <GitBranch className="w-4 h-4 text-purple-600" />;
      default:
        return <FileText className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'processing':
        return <LoadingSpinner size="sm" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
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

  if (contextSources.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Link to={`/projects/${projectId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Project
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Generate Tests</h1>
            <p className="text-gray-600 mt-1">Generate intelligent test cases for {project.name}</p>
          </div>
        </div>

        <Card>
          <CardContent className="p-12 text-center">
            <Zap className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Context Sources</h3>
            <p className="text-gray-600 mb-6">
              You need to add context sources before generating tests. Add Jira issues, 
              web application URLs, or documentation files to provide context for test generation.
            </p>
            <Link to={`/projects/${projectId}`}>
              <Button>
                <FileText className="w-4 h-4 mr-2" />
                Add Context Sources
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Link to={`/projects/${projectId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Project
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Generate Tests</h1>
          <p className="text-gray-600 mt-1">Generate intelligent test cases for {project.name}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Generation Form */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Zap className="w-5 h-5" />
                <span>Test Generation</span>
              </CardTitle>
              <CardDescription>
                Configure and start test generation with AI
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleStartGeneration} className="space-y-4">
                <Input
                  label="Feature Name"
                  placeholder="e.g., User Authentication, Shopping Cart"
                  value={generationConfig.feature_name}
                  onChange={(e) => setGenerationConfig(prev => ({ 
                    ...prev, 
                    feature_name: e.target.value 
                  }))}
                  required
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    LLM Provider
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    value={generationConfig.llm_provider}
                    onChange={(e) => setGenerationConfig(prev => ({ 
                      ...prev, 
                      llm_provider: e.target.value,
                      model: e.target.value === 'openai' ? 'gpt-4' : 'claude-3-sonnet-20240229'
                    }))}
                  >
                    <option value="openai">OpenAI GPT-4</option>
                    <option value="anthropic">Anthropic Claude</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Model
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    value={generationConfig.model}
                    onChange={(e) => setGenerationConfig(prev => ({ 
                      ...prev, 
                      model: e.target.value 
                    }))}
                  >
                    {generationConfig.llm_provider === 'openai' ? (
                      <>
                        <option value="gpt-4">GPT-4</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </>
                    ) : (
                      <>
                        <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                        <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                      </>
                    )}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Max Tokens"
                    type="number"
                    value={generationConfig.max_tokens}
                    onChange={(e) => setGenerationConfig(prev => ({ 
                      ...prev, 
                      max_tokens: Number(e.target.value) 
                    }))}
                  />
                  <Input
                    label="Temperature"
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={generationConfig.temperature}
                    onChange={(e) => setGenerationConfig(prev => ({ 
                      ...prev, 
                      temperature: Number(e.target.value) 
                    }))}
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  loading={createGenerationMutation.isPending}
                  disabled={currentGeneration?.status === 'processing'}
                >
                  <Play className="w-4 h-4 mr-2" />
                  Start Generation
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Context Sources */}
          <Card>
            <CardHeader>
              <CardTitle>Context Sources</CardTitle>
              <CardDescription>
                Available context for test generation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {contextSources.map((source) => (
                  <div key={source.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                    {getSourceIcon(source.source_type)}
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 capitalize">
                        {source.source_type} Source
                      </p>
                      <p className="text-sm text-gray-600">
                        {source.source_type === 'jira' && source.source_config.issue_keys?.length > 0 && (
                          `${source.source_config.issue_keys.length} issues`
                        )}
                        {source.source_type === 'url' && source.source_config.url && (
                          source.source_config.url
                        )}
                      </p>
                    </div>
                    <Badge variant="success">Ready</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Generation Status and Results */}
        <div className="space-y-6">
          {/* Current Generation Status */}
          {currentGeneration && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  {getStatusIcon(currentGeneration.status)}
                  <span>Generation Status</span>
                </CardTitle>
                <CardDescription>
                  {currentGeneration.feature_name}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">Progress</span>
                  <Badge variant={
                    currentGeneration.status === 'completed' ? 'success' :
                    currentGeneration.status === 'failed' ? 'error' :
                    currentGeneration.status === 'processing' ? 'warning' : 'secondary'
                  }>
                    {currentGeneration.status}
                  </Badge>
                </div>

                {currentGeneration.status === 'processing' && (
                  <ProgressBar value={lastMessage?.progress || 0} />
                )}

                {currentGeneration.status === 'completed' && (
                  <div className="flex items-center space-x-3">
                    <Button onClick={handleDownloadFiles}>
                      <Download className="w-4 h-4 mr-2" />
                      Download Files
                    </Button>
                    <Button variant="outline">
                      <Eye className="w-4 h-4 mr-2" />
                      View Code
                    </Button>
                  </div>
                )}

                {currentGeneration.status === 'failed' && currentGeneration.error_message && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-800">{currentGeneration.error_message}</p>
                  </div>
                )}

                <div className="text-xs text-gray-500">
                  Started {formatDistanceToNow(new Date(currentGeneration.created_at), { addSuffix: true })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Generated Files Preview */}
          {Object.keys(generatedFiles).length > 0 && (
            <CodePreview
              files={generatedFiles}
              title="Generated Test Files"
              onDownload={handleDownloadFiles}
            />
          )}

          {/* Previous Generations */}
          {testGenerations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Previous Generations</CardTitle>
                <CardDescription>
                  History of test generations for this project
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {testGenerations.slice(0, 5).map((generation) => (
                    <div key={generation.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(generation.status)}
                        <div>
                          <p className="font-medium text-gray-900">{generation.feature_name}</p>
                          <p className="text-sm text-gray-600">
                            {formatDistanceToNow(new Date(generation.created_at), { addSuffix: true })}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {generation.status === 'completed' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
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
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
