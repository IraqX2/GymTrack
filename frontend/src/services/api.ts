import type { Member, MemberFormValues } from "../types/member";

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  role: "user" | "admin" | string;
  is_banned: boolean;
  created_at: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

interface ApiErrorBody {
  detail?: unknown;
}

let accessToken: string | null = null;

function saveAuth(response: AuthResponse): AuthUser {
  accessToken = response.access_token;
  return response.user;
}

function describeError(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === "object" && item !== null && "msg" in item) {
        return String((item as { msg: unknown }).msg);
      }
      return String(item);
    }).join(" ");
  }
  return fallback;
}

async function readError(response: Response): Promise<Error> {
  const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
  return new Error(describeError(body.detail, "Request failed (" + response.status + ")."));
}

async function performRefresh(): Promise<AuthResponse> {
  const response = await fetch("/api/auth/refresh", {
    method: "POST",
    credentials: "same-origin",
  });

  if (!response.ok) {
    accessToken = null;
    throw await readError(response);
  }

  const result = (await response.json()) as AuthResponse;
  saveAuth(result);
  return result;
}

async function request<T>(
  url: string,
  options: RequestInit = {},
  retryAfterRefresh = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", "Bearer " + accessToken);
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "same-origin",
  });

  const isLoginOrSignup = url === "/api/auth/login" || url === "/api/auth/register";
  const isRefreshRequest = url === "/api/auth/refresh";

  if (
    response.status === 401 &&
    accessToken &&
    retryAfterRefresh &&
    !isLoginOrSignup &&
    !isRefreshRequest
  ) {
    try {
      await performRefresh();
      return request<T>(url, options, false);
    } catch {
      accessToken = null;
    }
  }

  if (!response.ok) {
    throw await readError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function register(
  fullName: string,
  email: string,
  password: string,
): Promise<AuthUser> {
  const result = await request<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ full_name: fullName, email, password }),
  });
  return saveAuth(result);
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const result = await request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return saveAuth(result);
}

export async function restoreSession(): Promise<AuthUser | null> {
  try {
    const result = await performRefresh();
    return result.user;
  } catch {
    accessToken = null;
    return null;
  }
}

export async function logout(): Promise<void> {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
      headers: accessToken ? { Authorization: "Bearer " + accessToken } : undefined,
    });
  } finally {
    accessToken = null;
  }
}

export function checkApiHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/health");
}

export function getMembers(): Promise<Member[]> {
  return request<Member[]>("/api/members");
}

export function getMember(id: number): Promise<Member> {
  return request<Member>("/api/members/" + id);
}

export function createMember(values: MemberFormValues): Promise<Member> {
  return request<Member>("/api/members", {
    method: "POST",
    body: JSON.stringify(values),
  });
}

export function updateMember(id: number, values: MemberFormValues): Promise<Member> {
  return request<Member>("/api/members/" + id, {
    method: "PUT",
    body: JSON.stringify(values),
  });
}

export function deleteMember(id: number): Promise<void> {
  return request<void>("/api/members/" + id, { method: "DELETE" });
}
