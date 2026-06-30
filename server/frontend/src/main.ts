import { createApp } from "vue";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import ConfirmationService from "primevue/confirmationservice";
import Pixeo from "./theme/pixeo-preset";
import App from "./app/App.vue";
import { router } from "./router";
import { getStoredTheme, applyTheme } from "./app/auth";
import { appServicesKey, createAppServices } from "./app/services";
import "primeicons/primeicons.css";
import "./app/styles.css";

async function bootstrap() {
  applyTheme(getStoredTheme());

  const app = createApp(App);
  const services = createAppServices();

  await services.restoreSession();

  app.use(router);
  app.use(PrimeVue, {
    theme: {
      preset: Pixeo,
      options: {
        darkModeSelector: ".dark",
        prefix: "p",
      },
    },
  });
  app.use(ToastService);
  app.use(ConfirmationService);
  app.provide(appServicesKey, services);
  app.mount("#app");
}

void bootstrap();
