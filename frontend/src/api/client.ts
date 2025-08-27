import axios, { AxiosError } from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 300 seconds timeout default
})

// 请求拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tgdrive_api_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // 处理网络错误
    if (!error.response) {
      console.error('Network error:', error.message)
      return Promise.reject(new Error('网络连接失败，请检查网络设置'))
    }

    // 处理 HTTP 错误
    const { status, data } = error.response

    switch (status) {
      case 401:
        console.warn('Unauthorized access, redirecting to login')
        // 可以在这里触发登录页面跳转
        break
      case 403:
        console.warn('Forbidden access')
        break
      case 404:
        console.warn('Resource not found')
        break
      case 500:
        console.error('Server error')
        break
    }

    return Promise.reject(error)
  }
)

export function setApiToken(token: string) {
  localStorage.setItem('tgdrive_api_token', token)
}

export function clearApiToken() {
  localStorage.removeItem('tgdrive_api_token')
}

export function getApiToken(): string | null {
  return localStorage.getItem('tgdrive_api_token')
}

// 会话管理
export function setSession(sessionData: {
  session_encrypted: string
  user_id: string
  username?: string
}) {
  localStorage.setItem('tgdrive_session', sessionData.session_encrypted)
  localStorage.setItem('tgdrive_user_id', sessionData.user_id)
  if (sessionData.username) {
    localStorage.setItem('tgdrive_username', sessionData.username)
  }
}

export function clearSession() {
  localStorage.removeItem('tgdrive_session')
  localStorage.removeItem('tgdrive_user_id')
  localStorage.removeItem('tgdrive_username')
}

export function getSession() {
  return {
    session: localStorage.getItem('tgdrive_session'),
    userId: localStorage.getItem('tgdrive_user_id'),
    username: localStorage.getItem('tgdrive_username')
  }
}

