export type GymUser = {
  id: number;
  full_name: string;
  email: string;
  role: "admin" | "user" | "trainer";
  is_banned: boolean;
  member_id?: number | null;
};

export type GymRow = Record<string, any> & { id: number };
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

const TOKEN_KEY = "gymtrack_access_token";
let accessToken: string | null = sessionStorage.getItem(TOKEN_KEY);

function saveToken(value: string | null) {
  accessToken = value;
  if (value) sessionStorage.setItem(TOKEN_KEY, value);
  else sessionStorage.removeItem(TOKEN_KEY);
}

async function raw<T>(path: string, method: HttpMethod = "GET", data?: unknown, authenticated = true): Promise<Response> {
  const headers = new Headers();
  if (data !== undefined) headers.set("Content-Type", "application/json");
  if (authenticated && accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(path, {
    method,
    headers,
    body: data === undefined ? undefined : JSON.stringify(data),
    credentials: "include",
  });
}

async function parseError(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({})) as { detail?: unknown };
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map((item: any) => item.msg).join(", ");
  return `Request failed (${response.status})`;
}

export async function api<T>(path: string, method: HttpMethod = "GET", data?: unknown): Promise<T> {
  let response = await raw(path, method, data);
  if (response.status === 401 && !path.startsWith("/api/auth/")) {
    try {
      const renewed = await raw<{ access_token: string }>("/api/auth/refresh", "POST", undefined, false);
      if (renewed.ok) {
        const auth = await renewed.json() as { access_token: string };
        saveToken(auth.access_token);
        response = await raw(path, method, data);
      } else {
        saveToken(null);
        window.dispatchEvent(new Event("gymtrack:logout"));
      }
    } catch {
      saveToken(null);
      window.dispatchEvent(new Event("gymtrack:logout"));
    }
  }
  if (!response.ok) throw new Error(await parseError(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<GymUser> {
  const result = await api<{ user: GymUser; access_token: string }>("/api/auth/login", "POST", { email, password });
  saveToken(result.access_token);
  return result.user;
}

export async function signup(full_name: string, email: string, password: string): Promise<GymUser> {
  const result = await api<{ user: GymUser; access_token: string }>("/api/auth/signup", "POST", { full_name, email, password });
  saveToken(result.access_token);
  return result.user;
}

export async function restoreSession(): Promise<GymUser | null> {
  try {
    if (!accessToken) {
      const response = await raw("/api/auth/refresh", "POST", undefined, false);
      if (!response.ok) return null;
      const result = await response.json() as { access_token: string; user?: GymUser };
      saveToken(result.access_token);
      // Refresh already returns the public user profile. Reuse it rather than
      // opening a second database request immediately after a cold start.
      if (result.user) return result.user;
    }
    return await api<GymUser>("/api/me");
  } catch {
    saveToken(null);
    return null;
  }
}

export async function logout(): Promise<void> {
  try { await api<void>("/api/auth/logout", "POST"); }
  finally { saveToken(null); }
}

export async function exportCsv(path: string, filename: string): Promise<void> {
  let response = await raw(path);
  if (response.status === 401) {
    const renewed = await raw("/api/auth/refresh", "POST", undefined, false);
    if (renewed.ok) {
      const auth = await renewed.json() as { access_token: string };
      saveToken(auth.access_token);
      response = await raw(path);
    }
  }
  if (!response.ok) throw new Error(await parseError(response));
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function clearAccessToken() {
  saveToken(null);
}
