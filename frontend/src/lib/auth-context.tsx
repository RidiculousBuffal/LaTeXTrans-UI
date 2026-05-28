import { createContext, useCallback, useContext, useEffect, useState } from "react"
import type { ReactNode } from "react"
import type { UserInfo } from "@/lib/types"
import { getAuthConfig, getMe, logout as apiLogout } from "@/lib/api"

type AuthContextType = {
  user: UserInfo | null
  isLoading: boolean
  registrationEnabled: boolean
  setAuth: (user: UserInfo) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  registrationEnabled: false,
  setAuth: () => {},
  logout: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [registrationEnabled, setRegistrationEnabled] = useState(false)

  useEffect(() => {
    Promise.allSettled([getAuthConfig(), getMe()])
      .then(([configResult, meResult]) => {
        if (configResult.status === "fulfilled") {
          setRegistrationEnabled(configResult.value.registration_enabled)
        }
        if (meResult.status === "fulfilled") {
          setUser(() => meResult.value)
        } else {
          // Avoid letting an older unauthenticated /auth/me probe clear a
          // newer user state that was just established by a successful login.
          setUser((currentUser) => currentUser)
        }
      })
      .finally(() => setIsLoading(false))
  }, [])

  const setAuth = useCallback((userInfo: UserInfo) => {
    setUser(userInfo)
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } catch {
      // We still clear local state if the session is already gone server-side.
    }
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, registrationEnabled, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
