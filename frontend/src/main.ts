import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './pages/Login.vue'
import Drive from './pages/Drive.vue'

const routes = [
  { path: '/', redirect: '/drive' },
  { path: '/login', component: Login },
  { path: '/drive', component: Drive },
]

const router = createRouter({ history: createWebHistory(), routes })

createApp(App).use(router).mount('#app')

