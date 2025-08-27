<template>
  <div class="container">
    <div class="toolbar">
      <router-link to="/login" class="link">登录</router-link>
      <span style="flex:1"></span>
      <input v-model="currentPath" style="min-width: 320px" />
      <input type="file" @change="onPickFile" />
      <button @click="refresh">刷新</button>
    </div>

    <div class="card" style="margin-top: 12px;">
      <h3>目录</h3>
      <div v-if="dirs.length === 0" class="muted">(空)</div>
      <ul>
        <li v-for="d in dirs" :key="d.path">
          <a href="#" class="link" @click.prevent="go(d.path)">{{ d.name }}</a>
        </li>
      </ul>
    </div>

    <div class="card" style="margin-top: 12px;">
      <h3>文件</h3>
      <table class="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>大小</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in files" :key="f.id">
            <td>{{ f.name }}</td>
            <td>{{ formatSize(f.size) }}</td>
            <td>{{ f.created_at }}</td>
            <td>
              <button @click="download(f.id, f.name)">下载</button>
              <button @click="rename(f.id)">重命名</button>
              <button @click="move(f.id)">移动</button>
              <button @click="del(f.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" v-if="log" style="margin-top: 12px;">
      <pre>{{ log }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const currentPath = ref('/')
const dirs = ref<{name:string, path:string}[]>([])
const files = ref<{id:string, name:string, size:number, created_at:string}[]>([])
const log = ref('')
const pickedFile = ref<File | null>(null)

function formatSize(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024*1024) return `${(n/1024).toFixed(1)} KB`
  if (n < 1024*1024*1024) return `${(n/1024/1024).toFixed(1)} MB`
  return `${(n/1024/1024/1024).toFixed(1)} GB`
}

function go(path: string) {
  currentPath.value = path
  refresh()
}

async function refresh() {
  const { data } = await api.get('/files', { params: { path: currentPath.value } })
  dirs.value = data.directories
  files.value = data.files
}

function onPickFile(e: Event) {
  const input = e.target as HTMLInputElement
  pickedFile.value = input.files?.[0] || null
  if (pickedFile.value) upload()
}

async function upload() {
  if (!pickedFile.value) return
  const form = new FormData()
  form.append('upload', pickedFile.value)
  try {
    const { data } = await api.post('/files', form, { params: { path: currentPath.value } })
    log.value = JSON.stringify(data, null, 2)
  } catch (e: any) {
    if (e?.response?.status === 409) {
      const detail = e.response.data?.detail
      if (typeof detail === 'object' && detail?.code === 'FILE_ALREADY_EXISTS') {
        log.value = `已存在同名文件：${detail.path}`
      } else {
        log.value = '已存在同名文件'
      }
    } else {
      log.value = `上传失败: ${e?.response?.status || ''}`
    }
  }
  await refresh()
}

function parseFilenameFromCD(cd?: string | null): string | null {
  if (!cd) return null
  // Try filename*=UTF-8''...
  const star = /filename\*=UTF-8''([^;\n]+)/i.exec(cd)
  if (star && star[1]) {
    try { return decodeURIComponent(star[1]) } catch { /* ignore */ }
  }
  const plain = /filename="?([^";\n]+)"?/i.exec(cd)
  if (plain && plain[1]) return plain[1]
  return null
}

async function download(id: string, fallbackName?: string) {
  try {
    const res = await api.get(`/files/id/${id}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    const cd = res.headers['content-disposition'] as string | undefined
    const name = parseFilenameFromCD(cd || null) || fallbackName || `download-${id}`
    a.href = url; a.download = name; a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    log.value = `下载失败: ${e?.response?.status || ''} ${e?.response?.data ? await e.response.data.text?.() : ''}`
  }
}

async function rename(id: string) {
  const newName = prompt('输入新名称') || undefined
  if (!newName) return
  const { data } = await api.post(`/files/id/${id}/move`, { new_name: newName })
  log.value = JSON.stringify(data, null, 2)
  await refresh()
}

async function move(id: string) {
  const newPath = prompt('输入新目录路径，如 /docs') || undefined
  if (!newPath) return
  const { data } = await api.post(`/files/id/${id}/move`, { new_dir_path: newPath })
  log.value = JSON.stringify(data, null, 2)
  await refresh()
}

async function del(id: string) {
  if (!confirm('确认删除？')) return
  const { data } = await api.delete(`/files/id/${id}`)
  log.value = JSON.stringify(data, null, 2)
  await refresh()
}

onMounted(refresh)
</script>

