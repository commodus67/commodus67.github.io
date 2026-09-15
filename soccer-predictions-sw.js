// Service worker for /soccer-predictions-demo (installable app + offline copy).
// The page is regenerated daily, so it is fetched network-first; the last good
// copy is kept only as an offline fallback. Bump VERSION when this file changes.
var VERSION = "scp-v1";
var PAGE = "/soccer-predictions-demo";
var ASSETS = [
  "/soccer-predictions-demo.webmanifest",
  "/demo-icon-192.png",
  "/demo-icon-512.png",
  "/demo-icon-maskable-512.png",
  "/apple-touch-icon.png",
  "/demo-favicon-48.png"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(VERSION).then(function (cache) {
      return cache.addAll(ASSETS).then(function () {
        return cache.add(new Request(PAGE, { cache: "no-store" })).catch(function () {});
      });
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k.indexOf("scp-") === 0 && k !== VERSION) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (req.mode === "navigate" && url.pathname.indexOf(PAGE) === 0) {
    event.respondWith(
      fetch(req).then(function (res) {
        if (res.ok) {
          var copy = res.clone();
          caches.open(VERSION).then(function (cache) { cache.put(PAGE, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match(PAGE).then(function (hit) {
          return hit || new Response(
            "<h1 style='font-family:sans-serif'>Offline</h1><p>Connect to the internet to load today's predictions.</p>",
            { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
          );
        });
      })
    );
    return;
  }

  if (ASSETS.indexOf(url.pathname) !== -1) {
    event.respondWith(
      caches.match(url.pathname).then(function (hit) { return hit || fetch(req); })
    );
  }
});
