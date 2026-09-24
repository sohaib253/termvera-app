const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const ACCESS_TOKEN_KEY = "tenderguard_access_token";
const REFRESH_TOKEN_KEY = "tenderguard_refresh_token";

export class ApiError extends Error {
  status: number;
  requestId?: string;

  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string) {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
}

function buildHeaders(auth: boolean, isFormData: boolean): Record<string, string> {
  const headers: Record<string, string> = {};
  if (!isFormData) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function parseErrorMessage(response: Response): Promise<{ message: string; requestId?: string }> {
  try {
    const data = await response.json();
    if (data?.error?.message) {
      return { message: data.error.message as string, requestId: data.error.request_id };
    }
  } catch {
    // response body wasn't JSON — fall through to a generic message
  }
  return { message: `Request failed with status ${response.status}` };
}

let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) return false;
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const isFormData = body instanceof FormData;

  const doFetch = async (): Promise<Response> => {
    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: buildHeaders(auth, isFormData),
      body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let response = await doFetch();

  if (response.status === 401 && auth) {
    const refreshed = await tryRefreshAccessToken();
    if (refreshed) {
      response = await doFetch();
    }
  }

  if (!response.ok) {
    const { message, requestId } = await parseErrorMessage(response);
    if (response.status === 401) {
      clearTokens();
    }
    throw new ApiError(message, response.status, requestId);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function openDocumentFile(path: string, page?: number): Promise<void> {
  const headers = buildHeaders(true, false);
  delete headers["Content-Type"];
  const response = await fetch(`${API_BASE_URL}${path}`, { headers });

  if (!response.ok) {
    const { message, requestId } = await parseErrorMessage(response);
    throw new ApiError(message, response.status, requestId);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  window.open(page ? `${url}#page=${page}` : url, "_blank", "noopener,noreferrer");
}

export async function downloadFile(path: string, filenameFallback: string): Promise<void> {
  const headers = buildHeaders(true, false);
  delete headers["Content-Type"];
  const response = await fetch(`${API_BASE_URL}${path}`, { headers });

  if (!response.ok) {
    const { message, requestId } = await parseErrorMessage(response);
    throw new ApiError(message, response.status, requestId);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? filenameFallback;

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
