export interface User {
  id: number;
  email: string;
  full_name: string;
  api_quotas: {
    openai: number;
    anthropic: number;
  };
  created_at: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  application_url?: string;
  base_context: Record<string, any>;
  settings: Record<string, any>;
  created_at: string;
  context_sources_count: number;
  test_generations_count: number;
}

export interface ContextSource {
  id: number;
  source_type: 'jira' | 'url' | 'file';
  source_config: Record<string, any>;
  extracted_context: Record<string, any>;
  created_at: string;
}

export interface TestGeneration {
  id: number;
  feature_name: string;
  config: Record<string, any>;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  generated_files: Record<string, string>;
  error_message?: string;
  created_at: string;
}

export interface Integration {
  id: number;
  integration_type: 'openai' | 'anthropic' | 'jira';
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface WebSocketMessage {
  status: string;
  stage?: string;
  progress?: number;
  error?: string;
  files?: Record<string, string>;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  application_url?: string;
  base_context?: Record<string, any>;
}

export interface CreateContextSourceRequest {
  source_type: 'jira' | 'url' | 'file';
  source_config: Record<string, any>;
}

export interface CreateTestGenerationRequest {
  feature_name: string;
  config: Record<string, any>;
}

export interface CreateIntegrationRequest {
  integration_type: 'openai' | 'anthropic' | 'jira';
  credentials: Record<string, string>;
}
