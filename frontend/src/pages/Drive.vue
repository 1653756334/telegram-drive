<template>
  <div class="container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <router-link to="/login" class="link">登录</router-link>
      <router-link to="/channels" class="link">频道管理</router-link>
      <span v-if="userInfo" class="user-info">
        用户: {{ userInfo.username || userInfo.id }}
      </span>
      <button @click="logout" class="link">登出</button>
      <span style="flex:1"></span>
      <input
        v-model="currentPath"
        placeholder="当前路径"
        style="min-width: 320px"
        :disabled="isLoading"
      />
      <input
        type="file"
        @change="onPickFile"
        :disabled="isLoading"
        title="选择文件上传"
      />
      <button @click="refresh" :disabled="isLoading">
        {{ isLoading ? '加载中...' : '刷新' }}
      </button>
    </div>

    <!-- 路径导航 -->
    <div class="card" style="margin-top: 12px;" v-if="currentPath !== '/'">
      <div class="toolbar">
        <button @click="go('/')" class="link">根目录</button>
        <span>/</span>
        <template v-for="(part, index) in currentPath.split('/').filter(p => p)" :key="index">
          <button
            @click="go('/' + currentPath.split('/').filter(p => p).slice(0, index + 1).join('/'))"
            class="link"
          >
            {{ part }}
          </button>
          <span v-if="index < currentPath.split('/').filter(p => p).length - 1">/</span>
        </template>
      </div>
    </div>

    <!-- 目录列表 -->
    <div class="card" style="margin-top: 12px;">
      <h3>📁 目录 ({{ dirs.length }})</h3>
      <div v-if="dirs.length === 0" class="muted">(无子目录)</div>
      <div v-else class="dir-grid">
        <div v-for="d in dirs" :key="d.path" class="dir-item">
          <button @click="go(d.path)" class="link dir-button">
            📁 {{ d.name }}
          </button>
        </div>
      </div>
    </div>

    <!-- 文件列表 -->
    <div class="card" style="margin-top: 12px;">
      <h3>📄 文件 ({{ files.length }})</h3>
      <div v-if="files.length === 0" class="muted">(无文件)</div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>大小</th>
            <th>类型</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in files" :key="f.id">
            <td>
              <span class="file-icon">{{ getFileIcon(f.extension) }}</span>
              {{ f.name }}
            </td>
            <td>{{ f.size_formatted || formatSize(f.size) }}</td>
            <td>{{ f.extension || '-' }}</td>
            <td>{{ new Date(f.created_at).toLocaleString() }}</td>
            <td>
              <button @click="download(f.id, f.name)" :disabled="isLoading" class="btn-sm">
                下载
              </button>
              <button @click="rename(f.id)" :disabled="isLoading" class="btn-sm">
                重命名
              </button>
              <button @click="move(f.id)" :disabled="isLoading" class="btn-sm">
                移动
              </button>
              <button @click="del(f.id)" :disabled="isLoading" class="btn-sm btn-danger">
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 操作日志 -->
    <div class="card" v-if="log" style="margin-top: 12px;">
      <h4>📋 操作日志</h4>
      <pre style="white-space: pre-wrap; word-break: break-word;">{{ log }}</pre>
      <button @click="log = ''" class="btn-sm">清除日志</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { clearSession } from '../api/client'
import { authService, fileService } from '../api/services'

const router = useRouter()
const currentPath = ref('/')
const dirs = ref<{name:string, path:string}[]>([])
const files = ref<{id:string, name:string, size:number, size_formatted:string, created_at:string, extension?:string}[]>([])
const log = ref('')
const pickedFile = ref<File | null>(null)
const isLoading = ref(false)
const userInfo = ref<{id:string, username?:string} | null>(null)

function formatSize(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024*1024) return `${(n/1024).toFixed(1)} KB`
  if (n < 1024*1024*1024) return `${(n/1024/1024).toFixed(1)} MB`
  return `${(n/1024/1024/1024).toFixed(1)} GB`
}

function getFileIcon(extension?: string): string {
  if (!extension) return '📄'
  const ext = extension.toLowerCase()

  // 图片
  if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)) return '🖼️'
  // 视频
  if (['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'].includes(ext)) return '🎬'
  // 音频
  if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'].includes(ext)) return '🎵'
  // 文档
  if (['pdf'].includes(ext)) return '📕'
  if (['doc', 'docx'].includes(ext)) return '📘'
  if (['xls', 'xlsx'].includes(ext)) return '📗'
  if (['ppt', 'pptx'].includes(ext)) return '📙'
  if (['txt', 'md'].includes(ext)) return '📝'
  // 压缩包
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return '📦'
  // 代码
  if (['js', 'ts', 'py', 'java', 'cpp', 'c', 'html', 'css'].includes(ext)) return '💻'

  return '📄'
}

function go(path: string) {
  currentPath.value = path
  refresh()
}

async function refresh() {
  isLoading.value = true
  try {
    const data = await fileService.listDirectory(currentPath.value)
    dirs.value = data.directories || []
    files.value = data.files || []
    log.value = `刷新成功: ${data.total_files} 个文件, 总大小 ${formatSize(data.total_size || 0)}`
  } catch (error: any) {
    log.value = `刷新失败: ${error.response?.data?.detail || error.message}`
    if (error.response?.status === 401) {
      router.push('/login')
    }
  } finally {
    isLoading.value = false
  }
}

async function checkUser() {
  try {
    const data = await authService.getCurrentUser()
    userInfo.value = data
    log.value = `当前用户: ${data.username || data.id}`
  } catch (error: any) {
    log.value = `获取用户信息失败: ${error.response?.data?.detail || error.message}`
    if (error.response?.status === 401) {
      router.push('/login')
    }
  }
}

async function logout() {
  try {
    await authService.logout()
    clearSession()
    router.push('/login')
  } catch (error: any) {
    log.value = `登出失败: ${error.response?.data?.detail || error.message}`
  }
}

function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  pickedFile.value = input.files?.[0] || null
  if (pickedFile.value) upload()
}

async function upload() {
  if (!pickedFile.value) return

  isLoading.value = true

  try {
    const data = await fileService.uploadFile(currentPath.value, pickedFile.value)

    log.value = `上传成功: ${data.name}\n文件ID: ${data.file_id}\n上传方式: ${data.via}\n大小: ${formatSize(data.size)}`

  } catch (e: any) {
    if (e?.response?.status === 409) {
      log.value = `文件已存在: ${e.response.data?.detail || '同名文件冲突'}`
    } else if (e?.response?.status === 400) {
      log.value = `上传失败: ${e.response.data?.detail || '请求参数错误'}`
    } else if (e?.response?.status === 500) {
      log.value = `上传失败: ${e.response.data?.detail || '服务器内部错误'}`
    } else {
      log.value = `上传失败: ${e?.response?.data?.detail || e.message}`
    }
  } finally {
    isLoading.value = false
    await refresh()
  }
}



async function download(id: string, fallbackName?: string) {
  isLoading.value = true
  try {
    const blob = await fileService.downloadFile(id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const name = fallbackName || `download-${id}`
    a.href = url; a.download = name; a.click()
    URL.revokeObjectURL(url)
    log.value = `下载成功: ${name}`
  } catch (e: any) {
    log.value = `下载失败: ${e?.response?.data?.detail || e.message}`
  } finally {
    isLoading.value = false
  }
}

async function rename(id: string) {
  const newName = prompt('输入新名称') || undefined
  if (!newName) return

  isLoading.value = true
  try {
    const data = await fileService.moveFile(id, { new_name: newName })
    log.value = `重命名成功: ${data.name}`
    await refresh()
  } catch (e: any) {
    log.value = `重命名失败: ${e?.response?.data?.detail || e.message}`
  } finally {
    isLoading.value = false
  }
}

async function move(id: string) {
  const newPath = prompt('输入新目录路径，如 /docs') || undefined
  if (!newPath) return

  isLoading.value = true
  try {
    const data = await fileService.moveFile(id, { new_dir_path: newPath })
    log.value = `移动成功: ${data.path}`
    await refresh()
  } catch (e: any) {
    log.value = `移动失败: ${e?.response?.data?.detail || e.message}`
  } finally {
    isLoading.value = false
  }
}

async function del(id: string) {
  if (!confirm('确认删除？')) return

  isLoading.value = true
  try {
    const data = await fileService.deleteFile(id)
    log.value = data.success ? '删除成功' : '删除失败'
    await refresh()
  } catch (e: any) {
    log.value = `删除失败: ${e?.response?.data?.detail || e.message}`
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  checkUser()
  refresh()
})
</script>

