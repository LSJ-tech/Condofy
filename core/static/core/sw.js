const CACHE_NAME = "condofy-v1";
const OFFLINE_URL = "/offline/";

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.add(OFFLINE_URL))
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
        ))
    );
    self.clients.claim();
});

// Red primero, con una página de respaldo si no hay conexión -- el contenido
// (alertas, gastos comunes) cambia seguido, así que nunca conviene mostrar
// una versión vieja desde el cache en vez de intentar la red.
self.addEventListener("fetch", (event) => {
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(OFFLINE_URL))
        );
    }
});
