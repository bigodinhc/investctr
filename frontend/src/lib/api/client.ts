/**
 * API Client for InvestCTR Backend
 */

import { createClient } from "@/lib/supabase/client";

// Singleton para manter consistência de sessão
let supabaseInstance: ReturnType<typeof createClient> | null = null;
function getSupabase() {
  if (!supabaseInstance) {
    supabaseInstance = createClient();
  }
  return supabaseInstance;
}

// Token cache para evitar race conditions
let cachedToken: string | null = null;
let authListenerInitialized = false;

function initAuthListener() {
  if (authListenerInitialized || typeof window === "undefined") return;
  authListenerInitialized = true;

  const supabase = getSupabase();

  // Listener para mudanças de estado de autenticação
  supabase.auth.onAuthStateChange((event, session) => {
    cachedToken = session?.access_token || null;
    console.log("[API] Auth state changed:", event, cachedToken ? "has token" : "no token");
  });

  // Inicializar com sessão atual
  supabase.auth.getSession().then(({ data }) => {
    cachedToken = data.session?.access_token || null;
    console.log("[API] Initial session:", cachedToken ? "has token" : "no token");
  });
}

// Inicializar listener no carregamento
if (typeof window !== "undefined") {
  initAuthListener();
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiError {
  error: string;
  details?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const supabase = getSupabase();

    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    // Primeiro tentar usar token em cache
    if (cachedToken) {
      headers["Authorization"] = `Bearer ${cachedToken}`;
      return headers;
    }

    // Fallback para getSession com retry
    for (let attempt = 1; attempt <= 3; attempt++) {
      const { data: { session }, error } = await supabase.auth.getSession();

      if (error) {
        console.error(`[API] Attempt ${attempt}: Error getting session:`, error);
      }

      if (session?.access_token) {
        cachedToken = session.access_token;
        headers["Authorization"] = `Bearer ${session.access_token}`;
        return headers;
      }

      if (attempt < 3) {
        await new Promise((resolve) => setTimeout(resolve, 100 * attempt));
      }
    }

    console.warn("[API] No access token after retries - request will be unauthenticated");
    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: "An unexpected error occurred",
      }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }

    const response = await fetch(url.toString(), {
      method: "GET",
      headers: await this.getAuthHeaders(),
      credentials: "include",
    });

    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "POST",
      headers: await this.getAuthHeaders(),
      credentials: "include",
      body: data ? JSON.stringify(data) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "PUT",
      headers: await this.getAuthHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });

    return this.handleResponse<T>(response);
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "DELETE",
      headers: await this.getAuthHeaders(),
      credentials: "include",
    });

    return this.handleResponse<T>(response);
  }

  async uploadFile<T>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, string>
  ): Promise<T> {
    const supabase = getSupabase();

    // Tentar obter sessão com retry para lidar com race conditions
    let accessToken: string | null = null;

    // Primeiro, tentar usar o token em cache
    if (cachedToken) {
      accessToken = cachedToken;
      console.log("[API] Using cached token for upload");
    }

    // Se não tiver cache, tentar obter da sessão com retry
    if (!accessToken) {
      for (let attempt = 1; attempt <= 3; attempt++) {
        const { data, error } = await supabase.auth.getSession();

        if (error) {
          console.error(`[API] Attempt ${attempt}: Error getting session:`, error);
        }

        if (data.session?.access_token) {
          accessToken = data.session.access_token;
          cachedToken = accessToken; // Atualizar cache
          console.log(`[API] Got session on attempt ${attempt}`);
          break;
        }

        // Aguardar antes de tentar novamente
        if (attempt < 3) {
          console.log(`[API] No session on attempt ${attempt}, retrying...`);
          await new Promise((resolve) => setTimeout(resolve, 100 * attempt));
        }
      }
    }

    if (!accessToken) {
      console.error("[API] No session after retries - user needs to login");
      // Redirecionar para login
      if (typeof window !== "undefined") {
        window.location.href = "/auth/login";
      }
      throw new Error("Sessão expirada. Faça login novamente.");
    }

    console.log("[API] Uploading with token:", accessToken.substring(0, 20) + "...");

    const formData = new FormData();
    formData.append("file", file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${accessToken}`,
      },
      credentials: "include",
      body: formData,
    });

    return this.handleResponse<T>(response);
  }
}

// Default API client instance
export const api = new ApiClient();
