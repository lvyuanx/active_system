import { createApp } from "vue";
import { ConfigProvider } from "vant";
import "vant/lib/index.css";
import "./styles/index.css";
import App from "./App.vue";
import router from "./router";

createApp(App).use(ConfigProvider).use(router).mount("#app");
