"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { apiRequest, clearTokens, getAccessToken, setTokens } from "@/lib/api-client";
import type { MeResponse } from "@/lib/types";

interface RegisterInput {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
  industry?: string;
  country?: string;
}

interface AuthContextValue {
  me: MeResponse | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
  refetchMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!getAccessToken()) {
      setMe(null);
      setIsLoading(false);
      return;
    }
    try {
      const response = await apiRequest<MeResponse>("/api/me");
      setMe(response);
    } catch {
      setMe(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Fetching the current session on mount is the documented "Effects:
    // fetching data" use case (react.dev) — there's no props/state this
    // could be derived from synchronously instead.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadMe();
  }, [loadMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiRequest<TokenResponse>("/api/auth/login", {
        method: "POST",
        body: { email, password },
        auth: false,
      });
      setTokens(tokens.access_token, tokens.refresh_token);
      await loadMe();
    },
    [loadMe]
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const tokens = await apiRequest<TokenResponse>("/api/auth/register", {
        method: "POST",
        body: input,
        auth: false,
      });
      setTokens(tokens.access_token, tokens.refresh_token);
      await loadMe();
    },
    [loadMe]
  );

  const logout = useCallback(() => {
    clearTokens();
    setMe(null);
  }, []);

  return (
    <AuthContext.Provider value={{ me, isLoading, login, register, logout, refetchMe: loadMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
