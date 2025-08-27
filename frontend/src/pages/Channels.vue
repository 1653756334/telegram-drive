<template>
  <div class="container">
    <h1>📺 频道管理</h1>
    
    <!-- 工具栏 -->
    <div class="toolbar">
      <router-link to="/drive" class="link">返回文件管理</router-link>
      <span style="flex:1"></span>
      <button @click="ensureChannel" :disabled="isLoading">
        {{ isLoading ? '检查中...' : '确保存储频道' }}
      </button>
      <button @click="refreshChannels" :disabled="isLoading">
        {{ isLoading ? '加载中...' : '刷新列表' }}
      </button>
    </div>

    <!-- 添加频道 -->
    <div class="card">
      <h3>➕ 添加新频道</h3>
      <div class="toolbar">
        <input 
          v-model="newChannelId" 
          placeholder="频道ID (如: -100xxxxxxxxx) 或用户名 (如: @channelname)"
          style="flex: 1"
          :disabled="isLoading"
        />
        <input 
          v-model="newChannelTitle" 
          placeholder="频道标题 (可选)"
          :disabled="isLoading"
        />
        <button @click="addChannel" :disabled="isLoading || !newChannelId.trim()">
          添加频道
        </button>
      </div>
    </div>

    <!-- 频道列表 -->
    <div class="card">
      <h3>📋 频道列表 ({{ channels.length }})</h3>
      <div v-if="channels.length === 0" class="muted">
        (暂无频道)
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>频道ID</th>
            <th>用户名</th>
            <th>标题</th>
            <th>标识符</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="channel in channels" :key="channel.id">
            <td>{{ channel.id }}</td>
            <td>{{ channel.channel_id }}</td>
            <td>{{ channel.username || '-' }}</td>
            <td>{{ channel.title || '-' }}</td>
            <td>{{ channel.identifier }}</td>
            <td>{{ new Date(channel.created_at).toLocaleString() }}</td>
            <td>
              <button 
                @click="removeChannel(channel.id)" 
                :disabled="isLoading"
                class="btn-sm btn-danger"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 操作日志 -->
    <div class="card" v-if="log">
      <h4>📋 操作日志</h4>
      <pre style="white-space: pre-wrap; word-break: break-word;">{{ log }}</pre>
      <button @click="log = ''" class="btn-sm">清除日志</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { channelService } from '../api/services'
import type { ChannelInfo } from '../api/types'

const router = useRouter()
const channels = ref<ChannelInfo[]>([])
const newChannelId = ref('')
const newChannelTitle = ref('')
const log = ref('')
const isLoading = ref(false)

async function ensureChannel() {
  isLoading.value = true
  try {
    const response = await channelService.ensureStorageChannel()
    log.value = `存储频道确保成功:\n${JSON.stringify(response.data, null, 2)}`
    await refreshChannels()
  } catch (error: any) {
    log.value = `确保存储频道失败: ${error.response?.data?.detail || error.message}`
    if (error.response?.status === 401) {
      router.push('/login')
    }
  } finally {
    isLoading.value = false
  }
}

async function refreshChannels() {
  isLoading.value = true
  try {
    const response = await channelService.listChannels()
    channels.value = response.channels || []
    log.value = `频道列表刷新成功: ${channels.value.length} 个频道`
  } catch (error: any) {
    log.value = `刷新频道列表失败: ${error.response?.data?.detail || error.message}`
    if (error.response?.status === 401) {
      router.push('/login')
    }
  } finally {
    isLoading.value = false
  }
}

async function addChannel() {
  if (!newChannelId.value.trim()) {
    log.value = '请输入频道ID或用户名'
    return
  }

  isLoading.value = true
  try {
    const response = await channelService.addChannel(
      newChannelId.value.trim(),
      newChannelTitle.value.trim() || undefined
    )
    
    log.value = `频道添加成功:\n${JSON.stringify(response.data, null, 2)}`
    
    // 清空输入框
    newChannelId.value = ''
    newChannelTitle.value = ''
    
    // 刷新列表
    await refreshChannels()
    
  } catch (error: any) {
    if (error.response?.status === 409) {
      log.value = `频道已存在: ${error.response.data?.detail || '重复添加'}`
    } else if (error.response?.status === 400) {
      log.value = `添加失败: ${error.response.data?.detail || '请求参数错误'}`
    } else {
      log.value = `添加频道失败: ${error.response?.data?.detail || error.message}`
    }
    
    if (error.response?.status === 401) {
      router.push('/login')
    }
  } finally {
    isLoading.value = false
  }
}

async function removeChannel(channelId: number) {
  if (!confirm(`确认删除频道 ID: ${channelId}？`)) return

  isLoading.value = true
  try {
    const response = await channelService.removeChannel(channelId)
    log.value = `频道删除成功: ${response.message}`
    await refreshChannels()
  } catch (error: any) {
    log.value = `删除频道失败: ${error.response?.data?.detail || error.message}`
    if (error.response?.status === 401) {
      router.push('/login')
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  refreshChannels()
})
</script>
