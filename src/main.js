// import { createApp } from "vue";
// import { registerPlugins } from "@/plugins";
// import App from "./App.vue";
// import vuetify from "./plugins/vuetify";
// import router from "./router"; // Router qo'shildi

// const app = createApp(App); // Faqat bitta app yaratiladi

// registerPlugins(app); // Plaginlarni ro‘yxatdan o‘tkazish
// app.use(router).use(vuetify); // Vuetify va Router ulanishi

import { createApp } from 'vue';
import { registerPlugins } from './plugins';  // Plaginlar ro'yxatdan o'tkaziladi
import App from './App.vue';
import VueApexCharts from 'vue3-apexcharts';

// Avval app yaratiladi
const app = createApp(App);

// Keyin plaginlar ulanadi
app.use(VueApexCharts);

// Plaginlar ro'yxatdan o'tkaziladi
registerPlugins(app);

// Nihoyat app mount qilinadi
app.mount('#app');
