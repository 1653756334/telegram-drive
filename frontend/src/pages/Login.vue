<template>
  <div class="container">
    <h1>登录</h1>
    <div class="card" style="max-width: 480px;">
      <div class="toolbar">
        <input v-model="apiToken" placeholder="后端API Token(可选)" />
        <button @click="saveToken">保存</button>
      </div>
      <div class="toolbar">
        <input v-model="phone" placeholder="手机号(含国家码)" />
        <button @click="sendCode">发送验证码</button>
      </div>
      <div class="toolbar">
        <input v-model="code" placeholder="验证码" />
        <input v-model="password" placeholder="二步密码(如有)" />
        <button @click="verify">验证并登录</button>
      </div>
      <div class="card" v-if="log">
        <pre>{{ log }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api, setApiToken } from '../api/client'

const phone = ref('')
const code = ref('')
const password = ref('')
const phone_code_hash = ref('')
const apiToken = ref(localStorage.getItem('tgdrive_api_token') || '')
const log = ref('')

async function saveToken() {
  setApiToken(apiToken.value)
}

async function sendCode() {
  const { data } = await api.post('/auth/telegram/send_code', { phone: phone.value })
  phone_code_hash.value = data.phone_code_hash
  log.value = JSON.stringify(data, null, 2)
}

async function verify() {
  const { data } = await api.post('/auth/telegram/verify', {
    phone: phone.value,
    code: code.value,
    phone_code_hash: phone_code_hash.value,
    password: password.value || null,
  })
  log.value = JSON.stringify(data, null, 2)
}
</script>

