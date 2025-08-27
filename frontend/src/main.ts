import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './pages/Login.vue'
import Drive from './pages/Drive.vue'
import Channels from './pages/Channels.vue'

// 导入样式
import './styles/main.css'

const routes = [
  { path: '/', redirect: '/drive' },
  { path: '/login', component: Login },
  { path: '/drive', component: Drive },
  { path: '/channels', component: Channels },
]

const router = createRouter({ history: createWebHistory(), routes })

createApp(App).use(router).mount('#app')

