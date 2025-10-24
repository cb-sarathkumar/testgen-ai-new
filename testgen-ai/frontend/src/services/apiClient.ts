import axios, { AxiosInstance, AxiosResponse } from 'axios';
import toast from 'react-hot-toast';
import {
  User,
  Project,
  ContextSource,
  TestGeneration,
  Integration,
  AuthResponse,
  CreateProjectRequest,
  CreateContextSourceRequest,
  CreateTestGenerationRequest,
  CreateIntegrationRequest,
} from '../types/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: 'http://localhost:9000/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          window.location.href = '/auth';
        } else if (error.response?.status >= 500) {
          toast.error('Server error. Please try again later.');
        } else if (error.response?.data?.detail) {
          toast.error(error.response.data.detail);
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth endpoints
  async register(email: string, password: string, fullName: string): Promise<User> {
    const response: AxiosResponse<User> = await this.client.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.client.post('/auth/login', {
      email,
      password,
    });
    
    // Store token
    localStorage.setItem('access_token', response.data.access_token);
    
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await this.client.get('/auth/me');
    return response.data;
  }

  // Project endpoints
  async getProjects(): Promise<Project[]> {
    const response: AxiosResponse<Project[]> = await this.client.get('/projects');
    return response.data;
  }

  async getProject(projectId: number): Promise<Project> {
    const response: AxiosResponse<Project> = await this.client.get(`/projects/${projectId}`);
    return response.data;
  }

  async createProject(projectData: CreateProjectRequest): Promise<Project> {
    const response: AxiosResponse<Project> = await this.client.post('/projects', projectData);
    return response.data;
  }

  async updateProject(projectId: number, projectData: Partial<CreateProjectRequest>): Promise<Project> {
    const response: AxiosResponse<Project> = await this.client.put(`/projects/${projectId}`, projectData);
    return response.data;
  }

  async deleteProject(projectId: number): Promise<void> {
    await this.client.delete(`/projects/${projectId}`);
  }

  // Context source endpoints
  async getContextSources(projectId: number): Promise<ContextSource[]> {
    const response: AxiosResponse<ContextSource[]> = await this.client.get(`/projects/${projectId}/contexts`);
    return response.data;
  }

  async createContextSource(projectId: number, sourceData: CreateContextSourceRequest): Promise<ContextSource> {
    const response: AxiosResponse<ContextSource> = await this.client.post(`/projects/${projectId}/contexts`, sourceData);
    return response.data;
  }

  async deleteContextSource(projectId: number, sourceId: number): Promise<void> {
    await this.client.delete(`/projects/${projectId}/contexts/${sourceId}`);
  }

  // Test generation endpoints
  async getTestGenerations(projectId: number): Promise<TestGeneration[]> {
    const response: AxiosResponse<TestGeneration[]> = await this.client.get(`/projects/${projectId}/generations`);
    return response.data;
  }

  async createTestGeneration(projectId: number, generationData: CreateTestGenerationRequest): Promise<TestGeneration> {
    const response: AxiosResponse<TestGeneration> = await this.client.post(`/projects/${projectId}/generations`, generationData);
    return response.data;
  }

  async downloadGenerationFiles(generationId: number): Promise<Blob> {
    const response = await this.client.get(`/generations/${generationId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // Integration endpoints
  async getIntegrations(): Promise<Integration[]> {
    const response: AxiosResponse<Integration[]> = await this.client.get('/integrations');
    return response.data;
  }

  async createIntegration(integrationData: CreateIntegrationRequest): Promise<Integration> {
    const response: AxiosResponse<Integration> = await this.client.post('/integrations', integrationData);
    return response.data;
  }

  async updateIntegration(integrationId: number, integrationData: Partial<CreateIntegrationRequest>): Promise<Integration> {
    const response: AxiosResponse<Integration> = await this.client.put(`/integrations/${integrationId}`, integrationData);
    return response.data;
  }

  async deleteIntegration(integrationId: number): Promise<void> {
    await this.client.delete(`/integrations/${integrationId}`);
  }

  // Utility methods
  logout(): void {
    localStorage.removeItem('access_token');
    window.location.href = '/auth';
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}

export const apiClient = new ApiClient();
