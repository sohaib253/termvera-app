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
import type { DesktopStatus, MeResponse } from "@/lib/types";

interface RegisterInput {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
  industry?: string;
  country?: string;
}

export interface DesktopSetupInput {
  full_name: string;
  organization_name: string;
  email?: string;
  industry?: string;
  country?: string;
}

interface AuthContextValue {
  me: MeResponse | null;
  isLoading: boolean;
  /** True in the installed desktop app: no login, automatic sign-in. */
  isDesktop: boolean;
  /** Desktop app not yet set up (first launch). */
  desktopSetupRequired: boolean;
  /** False during free early access: no trial to mention. */
  billingEnabled: boolean;
  setupDesktop: (input: DesktopSetupInput) => Promise<void>;
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
  const [isDesktop, setIsDesktop] = useState(false);
  const [desktopSetupRequired, setDesktopSetupRequired] = useState(false);
  const [billingEnabled, setBillingEnabled] = useState(true);

  const loadMe = useCallback(async () => {
    // The desktop app has one local user and no password: sign in
    // automatically, or report that first-run setup is needed.
    try {
      const desktop = await apiRequest<DesktopStatus>("/api/desktop/status", { auth: false });
      setIsDesktop(desktop.desktop);
      setDesktopSetupRequired(desktop.setup_required);
      setBillingEnabled(desktop.billing_enabled ?? true);
      if (desktop.desktop && desktop.setup_required) {
        clearTokens();
        setMe(null);
        setIsLoading(false);
        return;
      }
      if (desktop.desktop && !getAccessToken()) {
        const tokens = await apiRequest<TokenResponse>("/api/desktop/session", {
          method: "POST",
          auth: false,
        });
        setTokens(tokens.access_token, tokens.refresh_token);
      }
    } catch {
      // A server without the desktop routes, or unreachable: carry on with
      // the normal token check, which reports its own error.
    }
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

  const setupDesktop = useCallback(
    async (input: DesktopSetupInput) => {
      const tokens = await apiRequest<TokenResponse>("/api/desktop/setup", {
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
    <AuthContext.Provider
      value={{
        me,
        isLoading,
        isDesktop,
        desktopSetupRequired,
        billingEnabled,
        setupDesktop,
        login,
        register,
        logout,
        refetchMe: loadMe,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
