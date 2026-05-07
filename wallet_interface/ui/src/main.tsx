import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

registerPortalServiceWorker();

function registerPortalServiceWorker(): void {
  if (!("serviceWorker" in navigator)) return;
  if (!import.meta.env.PROD && import.meta.env.VITE_ENABLE_PWA_IN_DEV !== "true") return;

  window.addEventListener("load", () => {
    const serviceWorkerUrl = new URL("serviceWorker.js", window.location.href);
    const serviceWorkerScope = new URL("./", serviceWorkerUrl).pathname;
    navigator.serviceWorker
      .register(serviceWorkerUrl, { scope: serviceWorkerScope, type: "module" })
      .catch(() => undefined);
  });
}
