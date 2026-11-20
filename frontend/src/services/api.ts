import type { Member, MemberFormValues } from "../types/member";

interface ApiErrorBody {
  detail?: string;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const error = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function checkApiHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/health");
}

export function getMembers(): Promise<Member[]> {
  return request<Member[]>("/api/members");
}

export function getMember(id: number): Promise<Member> {
  return request<Member>(`/api/members/${id}`);
}

export function createMember(values: MemberFormValues): Promise<Member> {
  return request<Member>("/api/members", {
    method: "POST",
    body: JSON.stringify(values),
  });
}

export function updateMember(id: number, values: MemberFormValues): Promise<Member> {
  return request<Member>(`/api/members/${id}`, {
    method: "PUT",
    body: JSON.stringify(values),
  });
}

export function deleteMember(id: number): Promise<void> {
  return request<void>(`/api/members/${id}`, { method: "DELETE" });
}
