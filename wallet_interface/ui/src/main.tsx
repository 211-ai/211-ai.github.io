import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    const serviceWorkerBaseUrl = new URL(import.meta.env.BASE_URL || "./", window.location.href);
    const serviceWorkerUrl = new URL("service-worker.js", serviceWorkerBaseUrl);
    void navigator.serviceWorker
      .register(serviceWorkerUrl, {
        scope: serviceWorkerBaseUrl.href,
        type: "module"
      })
      .catch((error) => {
        console.warn("Abby offline shell registration failed", error);
      });
  });
}
