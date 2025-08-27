import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tgdrive_api_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

export function setApiToken(token: string) {
  localStorage.setItem('tgdrive_api_token', token)
}

export function clearApiToken() {
  localStorage.removeItem('tgdrive_api_token')
}

