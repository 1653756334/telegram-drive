// API 服务层
import { api } from './client'
import type {
  LoginRequest,
  VerifyCodeRequest,
  LoginResponse,
  UserResponse,
  DirectoryListResponse,
  UploadResponse,
  MoveRequest,
  MoveResponse,
  DeleteResponse,
  ChannelListResponse,
  ApiResponse
} from './types'

// 认证服务
export const authService = {
  async sendCode(request: LoginRequest): Promise<ApiResponse> {
    const { data } = await api.post('/api/v1/auth/send-code', request)
    return data
  },

  async verifyCode(request: VerifyCodeRequest): Promise<LoginResponse> {
    const { data } = await api.post('/api/v1/auth/verify-code', request)
    return data
  },

  async getCurrentUser(): Promise<UserResponse> {
    const { data } = await api.get('/api/v1/auth/me')
    return data
  },

  async logout(): Promise<ApiResponse> {
    const { data } = await api.post('/api/v1/auth/logout')
    return data
  }
}

// 文件服务
export const fileService = {
  async listDirectory(path: string = '/'): Promise<DirectoryListResponse> {
    const { data } = await api.get('/api/v1/files/', { params: { path } })
    return data
  },

  async uploadFile(path: string, file: File): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    
    const { data } = await api.post('/api/v1/files/upload', formData, {
      params: { path },
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  async downloadFile(fileId: string): Promise<Blob> {
    const response = await api.get(`/api/v1/files/id/${fileId}/download`, {
      responseType: 'blob'
    })
    return response.data
  },

  async moveFile(fileId: string, request: MoveRequest): Promise<MoveResponse> {
    const { data } = await api.post(`/api/v1/files/id/${fileId}/move`, request)
    return data
  },

  async deleteFile(fileId: string): Promise<DeleteResponse> {
    const { data } = await api.delete(`/api/v1/files/id/${fileId}`)
    return data
  }
}

// 频道服务
export const channelService = {
  async ensureStorageChannel(): Promise<ApiResponse> {
    const { data } = await api.post('/api/v1/channels/ensure')
    return data
  },

  async listChannels(): Promise<ChannelListResponse> {
    const { data } = await api.get('/api/v1/channels/')
    return data
  },

  async addChannel(identifier: string, title?: string): Promise<ApiResponse> {
    const { data } = await api.post('/api/v1/channels/add', null, {
      params: { identifier, title }
    })
    return data
  },

  async removeChannel(channelId: number): Promise<ApiResponse> {
    const { data } = await api.delete(`/api/v1/channels/${channelId}`)
    return data
  }
}

// 健康检查
export const healthService = {
  async check(): Promise<{ status: string; version: string; timestamp: string }> {
    const { data } = await api.get('/health')
    return data
  }
}
