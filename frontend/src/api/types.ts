// API 类型定义

// 通用响应类型
export interface ApiResponse<T = any> {
  success?: boolean
  message?: string
  data?: T
}

export interface ErrorResponse {
  error: string
  code?: string
  details?: Record<string, any>
}

// 认证相关
export interface LoginRequest {
  phone: string
}

export interface VerifyCodeRequest {
  phone: string
  code: string
  phone_code_hash: string
  password?: string
}

export interface LoginResponse {
  session_encrypted: string
  user_id: string
  username?: string
}

export interface UserResponse {
  id: string
  username?: string
  created_at: string
  is_anonymous: boolean
}

// 文件相关
export interface FileInfo {
  id: string
  name: string
  size: number
  size_formatted: string
  mime_type?: string
  path: string
  created_at: string
  extension?: string
}

export interface DirectoryInfo {
  name: string
  path: string
}

export interface DirectoryListResponse {
  path: string
  directories: DirectoryInfo[]
  files: FileInfo[]
  total_files: number
  total_size: number
}

export interface UploadResponse {
  file_id: string
  message_id: number
  via: string
  name: string
  size: number
  path: string
}

export interface MoveRequest {
  new_name?: string
  new_dir_path?: string
}

export interface MoveResponse {
  id: string
  name: string
  path: string
}

export interface DeleteResponse {
  success: boolean
  message: string
}

// 频道相关
export interface ChannelInfo {
  id: number
  channel_id: number
  username?: string
  title?: string
  display_name: string
  identifier: string | number
  created_at: string
}

export interface ChannelListResponse {
  channels: ChannelInfo[]
}
