const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  
  const buildHeaders = () => {
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    } as Record<string, string>;

    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }
    return headers;
  };

  const response = await fetch(url, {
    cache: 'no-store',
    ...options,
    headers: buildHeaders(),
  });

  // On 401, attempt a token refresh and retry once
  if (response.status === 401 && typeof window !== 'undefined' && !endpoint.includes('/auth/refresh')) {
    // Deduplicate concurrent refresh attempts
    if (!isRefreshing) {
      isRefreshing = true;
      refreshPromise = tryRefreshToken().finally(() => {
        isRefreshing = false;
        refreshPromise = null;
      });
    }

    const refreshed = await (refreshPromise ?? tryRefreshToken());
    if (refreshed) {
      // Retry the original request with the new token
      const retryResponse = await fetch(url, {
        cache: 'no-store',
        ...options,
        headers: buildHeaders(),
      });

      if (!retryResponse.ok) {
        const errorData = await retryResponse.json().catch(() => ({}));
        let errorMessage = errorData.message || `API Error: ${retryResponse.status} ${retryResponse.statusText}`;
        if (errorData.detail) {
          errorMessage = Array.isArray(errorData.detail) 
            ? errorData.detail.map((e: { msg: string }) => e.msg).join(', ') 
            : errorData.detail;
        }
        throw new Error(errorMessage);
      }

      if (retryResponse.status === 204) {
        return {} as T;
      }

      return retryResponse.json() as Promise<T>;
    }

    // Refresh failed — clear tokens and redirect to login
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    let errorMessage = errorData.message || `API Error: ${response.status} ${response.statusText}`;
    if (errorData.detail) {
      errorMessage = Array.isArray(errorData.detail) 
        ? errorData.detail.map((e: { msg: string }) => e.msg).join(', ') 
        : errorData.detail;
    }
    throw new Error(errorMessage);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
