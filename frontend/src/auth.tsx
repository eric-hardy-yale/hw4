import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { fetchMe, logout as apiLogout, type User } from './api'

interface AuthState {
  user: User | null
  ready: boolean
  setUser: (u: User | null) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true))
  }, [])

  async function logout() {
    await apiLogout().catch(() => undefined)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, ready, setUser, logout }}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
