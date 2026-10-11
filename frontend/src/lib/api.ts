/**
 * Cliente de la API de TechZone (FastAPI).
 *
 * Las llamadas se hacen desde el servidor de Astro, así que necesitan la URL
 * absoluta del backend. Se le reenvía la cookie del visitante para que
 * `/api/v1/me` sepa quién está conectado.
 */

const BASE = import.meta.env.PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export interface Product {
  id: number;
  name: string;
  brand: string;
  description: string;
  image_url: string;
  price: number;
  stock: number;
}

export interface Build {
  id: number;
  tier: string;
  name: string;
  tier_emoji: string;
  budget_label: string;
  cpu: string;
  gpu: string;
  ram: string;
  storage: string;
  performance_note: string;
  performance_pct: number;
  image_url: string;
  featured: boolean;
}

export interface Post {
  id: number;
  title: string;
  excerpt: string;
  author: string;
  created_at: string;
  views: number;
  comment_count: number;
  like_count: number;
}

export interface Comment {
  id: number;
  author: string;
  content: string;
  created_at: string;
}

export interface PostDetail extends Post {
  content: string;
  comments: Comment[];
}

export interface CommunityStats {
  users: number;
  posts: number;
  comments: number;
  requests: number;
}

export interface HomeData {
  products: Product[];
  builds: Build[];
  recent_posts: Post[];
  stats: { users: number; posts: number; comments: number };
}

export interface LegalPage {
  slug: string;
  title: string;
  body: string[];
}

export interface FlashMessage {
  category: string;
  message: string;
}

export interface SessionInfo {
  authenticated: boolean;
  name: string | null;
  role: string | null;
  is_admin: boolean;
  /** Avisos que dejó un redirect del backend. Se muestran una sola vez. */
  flashes: FlashMessage[];
}

const GUEST: SessionInfo = {
  authenticated: false,
  name: null,
  role: null,
  is_admin: false,
  flashes: [],
};

/**
 * Lo mínimo que necesitamos del objeto global `Astro`: la petición entrante y
 * las cabeceras de la respuesta que se va a devolver.
 */
export interface AstroContext {
  request: Request;
  response: { headers: Headers };
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
  ) {
    super(`La API respondió ${status} en ${path}`);
  }
}

function forwardedHeaders(request?: Request): HeadersInit {
  const cookie = request?.headers.get("cookie");
  return cookie ? { cookie } : {};
}

async function get<T>(path: string, request?: Request): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { headers: forwardedHeaders(request) });
  if (!response.ok) {
    throw new ApiError(response.status, path);
  }
  return (await response.json()) as T;
}

/** Igual que `get`, pero devuelve null en 404 para que la página haga su 404. */
async function getOrNull<T>(path: string, request?: Request): Promise<T | null> {
  try {
    return await get<T>(path, request);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export const api = {
  home: (request?: Request) => get<HomeData>("/api/v1/home", request),

  builds: (request?: Request) => get<Build[]>("/api/v1/catalog/builds", request),

  build: (id: number | string, request?: Request) =>
    getOrNull<Build>(`/api/v1/catalog/builds/${id}`, request),

  posts: (request?: Request) => get<Post[]>("/api/v1/community/posts", request),

  post: (id: number | string, request?: Request) =>
    getOrNull<PostDetail>(`/api/v1/community/posts/${id}`, request),

  communityStats: (request?: Request) =>
    get<CommunityStats>("/api/v1/community/stats", request),

  legal: (slug: string, request?: Request) =>
    getOrNull<LegalPage>(`/api/v1/legal/${slug}`, request),

  /** Nunca falla: si el backend no responde, el visitante se trata como anónimo. */
  async session(request?: Request): Promise<SessionInfo> {
    try {
      return await get<SessionInfo>("/api/v1/me", request);
    } catch {
      return GUEST;
    }
  },
};

/**
 * Lee la sesión y reenvía al navegador el Set-Cookie del backend.
 *
 * Hace falta porque leer los flashes los consume: si la cookie actualizada no
 * llega al navegador, el mismo aviso se mostraría una y otra vez.
 */
export async function loadSession(astro: AstroContext): Promise<SessionInfo> {
  try {
    const response = await fetch(`${BASE}/api/v1/me`, {
      headers: forwardedHeaders(astro.request),
    });
    if (!response.ok) {
      return GUEST;
    }
    forwardCookies(response, astro);
    return (await response.json()) as SessionInfo;
  } catch {
    return GUEST;
  }
}

/**
 * Token CSRF para los formularios que siguen procesándose en el backend.
 * Generarlo modifica la sesión, así que también hay que reenviar la cookie.
 */
export async function loadCsrf(astro: AstroContext): Promise<string | null> {
  try {
    const response = await fetch(`${BASE}/api/v1/csrf`, {
      headers: forwardedHeaders(astro.request),
    });
    if (!response.ok) {
      return null;
    }
    forwardCookies(response, astro);
    const body = (await response.json()) as { csrf_token: string };
    return body.csrf_token;
  } catch {
    return null;
  }
}

function forwardCookies(response: Response, astro: AstroContext): void {
  // getSetCookie() devuelve todas las cookies; en runtimes viejos cae al get().
  const cookies =
    typeof response.headers.getSetCookie === "function"
      ? response.headers.getSetCookie()
      : [response.headers.get("set-cookie")].filter((value): value is string => !!value);

  for (const cookie of cookies) {
    astro.response.headers.append("set-cookie", cookie);
  }
}

/** Respuesta 404 con la misma apariencia que la del backend. */
export function notFound(detail = "Página no encontrada."): Response {
  return new Response(
    `<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>404 · TechZone</title>
    <link rel="stylesheet" href="/static/css/style.css" />
  </head>
  <body style="display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center">
    <main style="padding:2rem">
      <h1>404 — Página no encontrada</h1>
      <p>${detail}</p>
      <p><a href="/">Volver al inicio</a></p>
    </main>
  </body>
</html>`,
    { status: 404, headers: { "content-type": "text/html; charset=utf-8" } },
  );
}

export function money(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function shortDate(value: string): string {
  return value.slice(0, 10);
}

export function initials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export function longDate(value: string): string {
  // "2026-10-11T14:05:00" → "2026-10-11 14:05", como el strftime de Jinja.
  return value.slice(0, 16).replace("T", " ");
}
