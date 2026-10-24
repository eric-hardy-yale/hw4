import { createContext, useContext, useState, type ReactNode } from 'react'
import type { Product } from './api'

// Product matches the chat agent returned, shared so any page can render them as cards.
interface ChatResultsState {
  title: string
  products: Product[]
  version: number // bumps on every new set, so the page can scroll to them
  show: (title: string, products: Product[]) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [title, setTitle] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [version, setVersion] = useState(0)

  const show = (t: string, p: Product[]) => {
    setTitle(t)
    setProducts(p)
    setVersion((v) => v + 1)
  }
  const clear = () => {
    setTitle('')
    setProducts([])
  }

  return (
    <ChatResultsContext.Provider value={{ title, products, version, show, clear }}>
      {children}
    </ChatResultsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
