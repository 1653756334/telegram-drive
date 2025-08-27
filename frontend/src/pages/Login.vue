<template>
  <div class="container">
    <h1>Telegram Drive - 登录</h1>
    <div class="card" style="max-width: 480px;">
      <!-- API Token 配置 -->
      <div class="toolbar">
        <input
          v-model="apiToken"
          placeholder="后端API Token(可选)"
          type="password"
        />
        <button @click="saveToken" :disabled="isLoading">保存Token</button>
      </div>

      <!-- 手机号验证 -->
      <div class="toolbar">
        <input
          v-model="phone"
          placeholder="手机号(含国家码，如+8613800138000)"
          :disabled="isLoading"
        />
        <button @click="sendCode" :disabled="isLoading || !phone.trim()">
          {{ isLoading ? '发送中...' : '发送验证码' }}
        </button>
      </div>

      <!-- 验证码输入 -->
      <div class="toolbar">
        <input
          v-model="code"
          placeholder="验证码"
          :disabled="isLoading"
        />
        <input
          v-model="password"
          placeholder="二步验证密码(如有)"
          type="password"
          :disabled="isLoading"
        />
        <button @click="verify" :disabled="isLoading || !code.trim() || !phone_code_hash">
          {{ isLoading ? '验证中...' : '验证并登录' }}
        </button>
      </div>

      <!-- 用户信息查询 -->
      <div class="toolbar">
        <button @click="checkCurrentUser" :disabled="isLoading">
          查看当前用户
        </button>
        <router-link to="/drive" class="link">
          进入文件管理
        </router-link>
      </div>

      <!-- 日志输出 -->
      <div class="card" v-if="log" style="margin-top: 12px;">
        <h4>操作日志</h4>
        <pre style="white-space: pre-wrap; word-break: break-word;">{{ log }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { setApiToken, setSession } from '../api/client'
import { authService } from '../api/services'

const router = useRouter()
const phone = ref('')
const code = ref('')
const password = ref('')
const phone_code_hash = ref('')
const apiToken = ref(localStorage.getItem('tgdrive_api_token') || '')
const log = ref('')
const isLoading = ref(false)

async function saveToken() {
  setApiToken(apiToken.value)
  log.value = 'API Token 已保存'
}

async function sendCode() {
  if (!phone.value.trim()) {
    log.value = '请输入手机号'
    return
  }

  isLoading.value = true
  try {
    const response = await authService.sendCode({ phone: phone.value.trim() })

    if (response.data && response.data.phone_code_hash) {
      phone_code_hash.value = response.data.phone_code_hash
      log.value = `验证码已发送到 ${response.data.phone}\n请查收短信并输入验证码`
    } else {
      log.value = JSON.stringify(response, null, 2)
    }
  } catch (error: any) {
    log.value = `发送验证码失败: ${error.response?.data?.detail || error.message}`
  } finally {
    isLoading.value = false
  }
}

async function verify() {
  if (!code.value.trim()) {
    log.value = '请输入验证码'
    return
  }

  if (!phone_code_hash.value) {
    log.value = '请先发送验证码'
    return
  }

  isLoading.value = true
  try {
    const response = await authService.verifyCode({
      phone: phone.value.trim(),
      code: code.value.trim(),
      phone_code_hash: phone_code_hash.value,
      password: password.value.trim() || undefined,
    })

    // 保存会话信息
    setSession(response)

    log.value = `登录成功！\n用户ID: ${response.user_id}\n用户名: ${response.username || '未设置'}`

    // 跳转到主页
    setTimeout(() => {
      router.push('/drive')
    }, 1500)

  } catch (error: any) {
    if (error.response?.status === 401 && error.response?.data?.detail?.includes('password')) {
      log.value = '需要输入两步验证密码'
    } else {
      log.value = `登录失败: ${error.response?.data?.detail || error.message}`
    }
  } finally {
    isLoading.value = false
  }
}

async function checkCurrentUser() {
  try {
    const user = await authService.getCurrentUser()
    log.value = `当前用户信息:\n${JSON.stringify(user, null, 2)}`
  } catch (error: any) {
    log.value = `获取用户信息失败: ${error.response?.data?.detail || error.message}`
  }
}
</script>

