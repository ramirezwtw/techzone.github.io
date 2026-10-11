import node from "@astrojs/node";
import { defineConfig } from "astro/config";

// El backend FastAPI. En desarrollo corre en otro puerto; en producción el
// frontend y la API se sirven desde el mismo dominio.
const BACKEND = process.env.PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

// Rutas que siguen siendo del backend (formularios con sesión y CSRF, panel
// admin, estáticos y la API). El proxy del servidor de desarrollo las manda a
// FastAPI, así que en el navegador todo vive en el mismo origen y la cookie de
// sesión funciona igual que en producción.
const BACKEND_PATHS = [
  "/api",
  "/static",
  "/docs",
  "/openapi.json",
  "/login",
  "/logout",
  "/registro",
  "/olvide-contrasena",
  "/restablecer-contrasena",
  "/verify-email",
  "/reenviar-verificacion",
  "/perfil",
  "/admin",
  "/comunidad/nueva",
  // Los POST de comentar y dar like: Astro solo sirve las vistas de lectura.
  "^/comunidad/[0-9]+/(like|comentar)$",
];

export default defineConfig({
  output: "server",
  // El sitio usa <img> con URLs externas, no el componente <Image> de Astro:
  // sin esto el build exigiría instalar sharp para nada.
  image: { service: { entrypoint: "astro/assets/services/noop" } },
  adapter: node({ mode: "standalone" }),
  server: { port: 4321 },
  vite: {
    server: {
      proxy: Object.fromEntries(
        BACKEND_PATHS.map((path) => [path, { target: BACKEND, changeOrigin: true }]),
      ),
    },
  },
});
