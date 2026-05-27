import { createContext, useCallback, useContext, useEffect, useState } from "react"
import type { ReactNode } from "react"
import type { UserInfo } from "@/lib/types"
import { getMe } from "@/lib/api"

type AuthContextType = {
  user: UserInfo | null
  isLoading: boolean
  setAuth: (token: string, user: UserInfo) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  setAuth: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (!token) {
      setIsLoading(false)
      return
    }
    getMe()
      .then((me) => setUser(me))
      .catch(() => {
        localStorage.removeItem("access_token")
        localStorage.removeItem("user_info")
      })
      .finally(() => setIsLoading(false))
  }, [])

  const setAuth = useCallback((token: string, userInfo: UserInfo) => {
    localStorage.setItem("access_token", token)
    localStorage.setItem("user_info", JSON.stringify(userInfo))
    setUser(userInfo)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("user_info")
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
