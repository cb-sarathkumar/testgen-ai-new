import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/UI/Card';
import { Button } from '../components/UI/Button';
import { Badge } from '../components/UI/Badge';
import { Input } from '../components/UI/Input';
import { 
  Settings, 
  Plus, 
  Key, 
  Zap, 
  FileText,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  ExternalLink,
  Info
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import toast from 'react-hot-toast';

export default function IntegrationsPage() {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newIntegration, setNewIntegration] = useState({
    integration_type: 'openai' as 'openai' | 'anthropic' | 'jira',
    credentials: {} as Record<string, string>,
  });
  const [showCredentials, setShowCredentials] = useState<Record<string, boolean>>({});

  const queryClient = useQueryClient();

  const { data: integrations = [], isLoading } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => apiClient.getIntegrations(),
  });

  const addIntegrationMutation = useMutation({
    mutationFn: (integrationData: any) => apiClient.createIntegration(integrationData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
      setShowAddModal(false);
      setNewIntegration({ integration_type: 'openai', credentials: {} });
      toast.success('Integration added successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to add integration');
    },
  });

  const deleteIntegrationMutation = useMutation({
    mutationFn: (integrationId: number) => apiClient.deleteIntegration(integrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
      toast.success('Integration deleted successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete integration');
    },
  });

  const handleAddIntegration = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate credentials based on integration type
    let credentials = {};
    if (newIntegration.integration_type === 'openai') {
      const apiKey = (e.target as any).api_key?.value;
      const baseUrl = (e.target as any).base_url?.value;
      if (!apiKey) {
        toast.error('OpenAI API key is required');
        return;
      }
      credentials = { api_key: apiKey };
      if (baseUrl && baseUrl.trim()) {
        credentials = { ...credentials, base_url: baseUrl.trim() };
      }
    } else if (newIntegration.integration_type === 'anthropic') {
      const apiKey = (e.target as any).api_key?.value;
      const baseUrl = (e.target as any).base_url?.value;
      if (!apiKey) {
        toast.error('Anthropic API key is required');
        return;
      }
      credentials = { api_key: apiKey };
      if (baseUrl && baseUrl.trim()) {
        credentials = { ...credentials, base_url: baseUrl.trim() };
      }
    } else if (newIntegration.integration_type === 'jira') {
      const url = (e.target as any).jira_url?.value;
      const username = (e.target as any).username?.value;
      const apiToken = (e.target as any).api_token?.value;
      
      if (!url || !username || !apiToken) {
        toast.error('All Jira fields are required');
        return;
      }
      credentials = { jira_url: url, username: username, api_token: apiToken };
    }
    
    addIntegrationMutation.mutate({
      integration_type: newIntegration.integration_type,
      credentials: credentials,
    });
  };

  const getIntegrationIcon = (type: string) => {
    switch (type) {
      case 'openai':
        return <Zap className="w-5 h-5 text-green-600" />;
      case 'anthropic':
        return <Zap className="w-5 h-5 text-orange-600" />;
      case 'jira':
        return <FileText className="w-5 h-5 text-blue-600" />;
      default:
        return <Key className="w-5 h-5 text-gray-600" />;
    }
  };

  const getIntegrationName = (type: string) => {
    switch (type) {
      case 'openai':
        return 'OpenAI';
      case 'anthropic':
        return 'Anthropic Claude';
      case 'jira':
        return 'Jira';
      default:
        return type;
    }
  };

  const getIntegrationDescription = (type: string) => {
    switch (type) {
      case 'openai':
        return 'Generate tests using OpenAI GPT models';
      case 'anthropic':
        return 'Generate tests using Anthropic Claude models';
      case 'jira':
        return 'Extract context from Jira issues and stories';
      default:
        return 'Integration for test generation';
    }
  };

  const toggleCredentialVisibility = (integrationId: number) => {
    setShowCredentials(prev => ({
      ...prev,
      [integrationId]: !prev[integrationId]
    }));
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded animate-pulse"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-200 rounded-lg animate-pulse"></div>
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
          <h1 className="text-3xl font-bold text-gray-900">Integrations</h1>
          <p className="text-gray-600 mt-1">
            Configure API keys and external service connections
          </p>
        </div>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Integration
        </Button>
      </div>

      {/* Integration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {integrations.map((integration) => (
          <Card key={integration.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getIntegrationIcon(integration.integration_type)}
                  <div>
                    <CardTitle className="text-lg">
                      {getIntegrationName(integration.integration_type)}
                    </CardTitle>
                    <CardDescription>
                      {getIntegrationDescription(integration.integration_type)}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge variant={integration.is_active ? 'success' : 'secondary'}>
                    {integration.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                Added {formatDistanceToNow(new Date(integration.created_at), { addSuffix: true })}
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toggleCredentialVisibility(integration.id)}
                >
                  {showCredentials[integration.id] ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                  <span className="ml-2">
                    {showCredentials[integration.id] ? 'Hide' : 'Show'} Credentials
                  </span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => deleteIntegrationMutation.mutate(integration.id)}
                >
                  <XCircle className="w-4 h-4" />
                </Button>
              </div>

              {showCredentials[integration.id] && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 mb-2">Stored credentials:</p>
                  <div className="space-y-1">
                    {integration.integration_type === 'openai' && (
                      <p className="text-sm font-mono bg-white p-2 rounded border">
                        API Key: ••••••••••••••••
                      </p>
                    )}
                    {integration.integration_type === 'anthropic' && (
                      <p className="text-sm font-mono bg-white p-2 rounded border">
                        API Key: ••••••••••••••••
                      </p>
                    )}
                    {integration.integration_type === 'jira' && (
                      <div className="space-y-1">
                        <p className="text-sm font-mono bg-white p-2 rounded border">
                          URL: ••••••••••••••••
                        </p>
                        <p className="text-sm font-mono bg-white p-2 rounded border">
                          Username: ••••••••••••••••
                        </p>
                        <p className="text-sm font-mono bg-white p-2 rounded border">
                          API Token: ••••••••••••••••
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Getting Started */}
      {integrations.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Getting Started with Integrations</CardTitle>
            <CardDescription>
              Set up your first integration to start generating intelligent test cases
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 border border-gray-200 rounded-lg">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-6 h-6 text-green-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">OpenAI</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Generate tests using GPT-4 and GPT-3.5 models. Get your API key from OpenAI.
                </p>
                <a
                  href="https://platform.openai.com/api-keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700"
                >
                  Get API Key
                  <ExternalLink className="w-3 h-3 ml-1" />
                </a>
              </div>

              <div className="text-center p-6 border border-gray-200 rounded-lg">
                <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-6 h-6 text-orange-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Anthropic</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Generate tests using Claude models. Get your API key from Anthropic.
                </p>
                <a
                  href="https://console.anthropic.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700"
                >
                  Get API Key
                  <ExternalLink className="w-3 h-3 ml-1" />
                </a>
              </div>

              <div className="text-center p-6 border border-gray-200 rounded-lg">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Jira</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Extract context from Jira issues, stories, and acceptance criteria.
                </p>
                <div className="text-sm text-gray-500">
                  Configure in projects
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Integration Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Add Integration</CardTitle>
              <CardDescription>
                Configure a new integration for test generation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAddIntegration} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Integration Type
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    value={newIntegration.integration_type}
                    onChange={(e) => setNewIntegration(prev => ({ 
                      ...prev, 
                      integration_type: e.target.value as 'openai' | 'anthropic' | 'jira' 
                    }))}
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic Claude</option>
                    <option value="jira">Jira</option>
                  </select>
                </div>

                {newIntegration.integration_type === 'openai' && (
                  <>
                    <Input
                      label="OpenAI API Key"
                      type="password"
                      placeholder="sk-..."
                      name="api_key"
                      required
                    />
                    <Input
                      label="Base URL (Optional)"
                      type="text"
                      placeholder="https://api.openai.com/v1"
                      name="base_url"
                      helperText="Leave empty to use default OpenAI endpoint. Use this for custom ChatGPT wrappers."
                    />
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start space-x-2">
                        <Info className="w-4 h-4 text-blue-600 mt-0.5" />
                        <div className="text-sm text-blue-800">
                          <p className="font-medium">Get your API key:</p>
                          <a
                            href="https://platform.openai.com/api-keys"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline hover:no-underline"
                          >
                            platform.openai.com/api-keys
                          </a>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {newIntegration.integration_type === 'anthropic' && (
                  <>
                    <Input
                      label="Anthropic API Key"
                      type="password"
                      placeholder="sk-ant-..."
                      name="api_key"
                      required
                    />
                    <Input
                      label="Base URL (Optional)"
                      type="text"
                      placeholder="https://api.anthropic.com"
                      name="base_url"
                      helperText="Leave empty to use default Anthropic endpoint. Use this for custom Claude wrappers."
                    />
                    <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                      <div className="flex items-start space-x-2">
                        <Info className="w-4 h-4 text-orange-600 mt-0.5" />
                        <div className="text-sm text-orange-800">
                          <p className="font-medium">Get your API key:</p>
                          <a
                            href="https://console.anthropic.com/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline hover:no-underline"
                          >
                            console.anthropic.com
                          </a>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {newIntegration.integration_type === 'jira' && (
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
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start space-x-2">
                        <Info className="w-4 h-4 text-blue-600 mt-0.5" />
                        <div className="text-sm text-blue-800">
                          <p className="font-medium">Get your API token:</p>
                          <a
                            href="https://id.atlassian.com/manage-profile/security/api-tokens"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline hover:no-underline"
                          >
                            id.atlassian.com/manage-profile/security/api-tokens
                          </a>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                <div className="flex items-center space-x-3 pt-4">
                  <Button
                    type="submit"
                    loading={addIntegrationMutation.isPending}
                    className="flex-1"
                  >
                    Add Integration
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowAddModal(false)}
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
