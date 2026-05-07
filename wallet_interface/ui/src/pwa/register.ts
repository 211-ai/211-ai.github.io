export async function registerPortalServiceWorker(): Promise<ServiceWorkerRegistration | undefined> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !import.meta.env.PROD) {
    return undefined;
  }

  const baseUrl = new URL(import.meta.env.BASE_URL || "/", window.location.origin);
  const serviceWorkerUrl = new URL("serviceWorker.js", baseUrl);

  try {
    return await navigator.serviceWorker.register(serviceWorkerUrl, {
      scope: baseUrl.pathname,
      type: "module",
    });
  } catch {
    return undefined;
  }
}
