export interface AuthUser { user_id: string; username: string; access_token: string }

export const getUser = (): AuthUser | null => {
  try { return JSON.parse(localStorage.getItem('ats_user') || 'null') } catch { return null }
}
export const setUser = (u: AuthUser) => {
  localStorage.setItem('ats_user', JSON.stringify(u))
  localStorage.setItem('ats_token', u.access_token)
}
export const clearUser = () => {
  localStorage.removeItem('ats_user')
  localStorage.removeItem('ats_token')
}
export const isAuthenticated = () => !!getUser()
