// Thin client for the FastAPI backend. Vite proxies /api and /media to port 8000.

export interface SizeStock {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
  inventory?: SizeStock[]
  total_stock?: number
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  text: string
}

export interface ChatReply {
  reply: string
  products: Product[]
  results_title: string
  tools_used: string[]
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchProducts = (q?: string) =>
  getJson<Product[]>(`/api/products${q ? `?q=${encodeURIComponent(q)}` : ''}`)

export const fetchProduct = (id: string) => getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

export interface PageContext {
  path: string
  product_id: string | null
}

export interface SavedMessage extends ChatTurn {
  products: Product[]
  created_at: string
}

// history is only used for guests; the backend reads logged-in shoppers' history from the database.
export const sendChat = (message: string, history: ChatTurn[], page: PageContext) =>
  getJson<ChatReply>('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({ message, history: history.slice(-12), page }),
  })

export const fetchChatHistory = () => getJson<SavedMessage[]>('/api/chat/history', { credentials: 'same-origin' })

export const clearChatHistory = () =>
  getJson<{ ok: boolean }>('/api/chat/history', { method: 'DELETE', credentials: 'same-origin' })

export const formatPrice = (n: number) => `$${n.toFixed(2)}`

// ---- accounts (session lives in an HttpOnly cookie set by the backend)

export interface User {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
}

async function postAuth<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data?.detail
    // FastAPI validation errors come back as a list.
    const msg = Array.isArray(d) ? d.map((e: { msg: string }) => e.msg).join(' ') : d
    throw new Error(msg || 'Something went wrong. Please try again.')
  }
  return data as T
}

export const fetchMe = () => getJson<User | null>('/api/auth/me', { credentials: 'same-origin' })
export const login = (email: string, password: string) => postAuth<User>('/api/auth/login', { email, password })
export const signup = (body: { first_name: string; last_name: string; email: string; password: string }) =>
  postAuth<User>('/api/auth/signup', body)
export const logout = () => postAuth<{ ok: boolean }>('/api/auth/logout')

export const fetchSimilar = (id: string) => getJson<Product[]>(`/api/products/${encodeURIComponent(id)}/similar?limit=4`)
