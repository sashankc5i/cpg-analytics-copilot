import { createContext, useContext, useEffect, useState } from 'react'
import { api, tok } from './api'
const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); const [ready, setReady] = useState(false)
  useEffect(() => { if (!tok.get()) { setReady(true); return } api('/auth/me').then(setUser).catch(() => tok.clear()).finally(() => setReady(true)) }, [])
  const login = async (username, password) => { const r = await api('/auth/login', { method: 'POST', body: { username, password } }); tok.set(r.token); setUser(r.user) }
  const logout = () => { tok.clear(); setUser(null) }
  return <Ctx.Provider value={{ user, ready, login, logout, can: f => !!user?.features.includes(f) }}>{children}</Ctx.Provider>
}
