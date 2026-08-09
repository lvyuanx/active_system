import { createApp } from "vue";
import { ConfigProvider } from "vant";
import "vant/lib/index.css";
import "./styles/index.css";
import App from "./App.vue";

createApp(App).use(ConfigProvider).mount("#app");
