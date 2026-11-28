const CACHE_NAME = "systan-srs-shell-v2";
const SHELL_ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  let url;
  try {
    url = new URL(req.url);
  } catch (_) {
    return;
  }

  // Never intercept or cache cross-origin calls (GAS, Google Drive, external APIs)
  if (url.origin !== self.location.origin) return;

  const isNav = req.mode === "navigate";
  const isShell = isNav || /\/($|index\.html$|manifest\.json$|icon\.svg$)/.test(url.pathname);
  if (!isShell) return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.ok && res.type === "basic") {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone)).catch(() => {});
        }
        return res;
      })
      .catch(async () => {
        const cached = await caches.match(req);
        if (cached) return cached;
        if (isNav) {
          return (await caches.match("./index.html")) || (await caches.match("./"));
        }
        return new Response("Offline", { status: 503, statusText: "Offline" });
      })
  );
});
