/* ─── Service Worker — UPTCER ────────────────────────────────────────────── */

const CACHE_NAME = 'uptcer-v1';

// Archivos a cachear en la primera carga
const ESTATICOS = [
  '/static/css/global.css',
  '/static/css/toast.css',
  '/static/css/modal.css',
  '/static/css/componentes.css',
  '/static/css/f43.css',
  '/static/js/modal.js',
  '/static/js/toast.js',
  '/static/js/forms.js',
  '/static/js/scroll-top.js',
  '/static/js/zoom-documento.js',
  '/static/js/busqueda-ajax.js',
  '/static/js/impresion.js',
  '/static/js/f43.js',
  '/static/js/sw-registro.js',
];

// ─── Install: cachear estáticos ────────────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Cacheando estáticos...');
        return cache.addAll(ESTATICOS);
      })
      .then(() => {
        console.log('[SW] Instalado correctamente');
        return self.skipWaiting();
      })
  );
});

// ─── Activate: limpiar caches viejos ───────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activado');
  event.waitUntil(
    caches.keys().then((nombres) => {
      return Promise.all(
        nombres
          .filter((nombre) => nombre !== CACHE_NAME)
          .map((nombre) => {
            console.log('[SW] Eliminando cache viejo:', nombre);
            return caches.delete(nombre);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// ─── Fetch: Cache First para estáticos ─────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Solo cachear archivos estáticos
  if (url.includes('/static/')) {
    event.respondWith(
      caches.match(event.request)
        .then((respuestaCache) => {
          // Si está en cache, devolverlo inmediatamente
          if (respuestaCache) {
            return respuestaCache;
          }

          // Si no está en cache, buscarlo en red y guardarlo
          return fetch(event.request)
            .then((respuestaRed) => {
              // Solo cachear respuestas exitosas
              if (respuestaRed.ok) {
                const copia = respuestaRed.clone();
                caches.open(CACHE_NAME)
                  .then((cache) => cache.put(event.request, copia));
              }
              return respuestaRed;
            })
            .catch(() => {
              // Si falla la red y no hay cache, devolver error controlado
              console.warn('[SW] Sin conexión y sin cache para:', url);
              return new Response('Recurso no disponible sin conexión', {
                status: 503,
                headers: { 'Content-Type': 'text/plain' }
              });
            });
        })
    );
  }

  // Para peticiones normales (páginas Django), no cachear
  // Solo pasar la petición directamente a la red
});