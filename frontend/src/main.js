import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)

app.mount('#app')

console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL);
