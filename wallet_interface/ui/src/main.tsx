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
    navigator.serviceWorker.register(serviceWorkerUrl, { scope: scopeUrl.pathname, type: "module" }).catch(() => {
      // The app remains usable without PWA support.
    });
  });
}
