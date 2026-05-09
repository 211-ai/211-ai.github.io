import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

const enablePwaInAutomation = import.meta.env.VITE_ENABLE_PWA_IN_AUTOMATION === "true";
const shouldRegisterServiceWorker =
  "serviceWorker" in navigator &&
  import.meta.env.PROD &&
  (!navigator.webdriver || enablePwaInAutomation);

if (shouldRegisterServiceWorker) {
  const serviceWorkerUrl = new URL("serviceWorker.js", window.location.href);
  const scopeUrl = new URL("./", serviceWorkerUrl);

  window.addEventListener("load", () => {
    registerServiceWorker(serviceWorkerUrl, scopeUrl).catch(() => {
      // The app remains usable without PWA support.
    });
  });
}

async function registerServiceWorker(serviceWorkerUrl: URL, scopeUrl: URL): Promise<void> {
  let refreshing = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (refreshing) return;
    refreshing = true;
    window.location.reload();
  });

  const registration = await navigator.serviceWorker.register(serviceWorkerUrl, {
    scope: scopeUrl.pathname,
    type: "module",
  });
  await registration.update().catch(() => undefined);
  const waitingWorker = registration.waiting || registration.installing;
  waitingWorker?.postMessage({ type: "SKIP_WAITING" });
}
