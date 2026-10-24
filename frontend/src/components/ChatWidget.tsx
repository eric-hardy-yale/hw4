import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'
import Markdown from 'react-markdown'
import { clearChatHistory, fetchChatHistory, formatPrice, sendChat, type ChatTurn, type PageContext, type Product } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import { OPEN_CHAT } from '../chatBus'

interface Message extends ChatTurn {
  products?: Product[]
}

const greeting = (name?: string | null): Message => ({
  role: 'assistant',
  text: `Hi${name ? ` ${name}` : ''}! I'm the Campus Customs assistant. Ask me about sizes, prices, or what's in stock.`,
})

export default function ChatWidget() {
  const { user } = useAuth()
  const results = useChatResults()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [opened, setOpened] = useState(false) // pulse the button until the shopper opens chat once
  const endRef = useRef<HTMLDivElement>(null)

  const { pathname } = useLocation()
  // Tell the agent what's on screen, so "do you have this in pink?" means the product being viewed.
  const productMatch = pathname.match(/^\/products\/([^/]+)$/)
  const page: PageContext = { path: pathname, product_id: productMatch ? decodeURIComponent(productMatch[1]) : null }

  // Logged in: reload saved chat from the database. Guest (or logout): start fresh.
  useEffect(() => {
    let cancelled = false
    setMessages([greeting(user?.first_name)])
    if (user) {
      fetchChatHistory()
        .then((saved) => {
          if (!cancelled && saved.length > 0)
            setMessages([greeting(user.first_name), ...saved.map(({ role, text, products }) => ({ role, text, products }))])
        })
        .catch(() => undefined)
    }
    return () => {
      cancelled = true
    }
  }, [user])

  async function newChat() {
    if (user) await clearChatHistory().catch(() => undefined)
    setMessages([greeting(user?.first_name)])
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, busy])

  // One-tap suggestions (Problem 8). On a product page they're about that item.
  const started = messages.some((m) => m.role === 'user')
  const suggestions = page.product_id
    ? ['Is this in stock in M?', 'What colors does this come in?', 'Show me similar items']
    : ['What hoodies do you have?', 'Anything with Handsome Dan?', 'Gifts under $40', 'Show me Berkeley College gear']
  const showChips = !busy && (!started || page.product_id !== null)

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || busy) return
    // Guests send their history (greeting excluded); for logged-in shoppers the server reads it from the DB.
    const history: ChatTurn[] = messages.slice(1).map(({ role, text }) => ({ role, text }))
    setInput('')
    setMessages((m) => [...m, { role: 'user', text }])
    setBusy(true)
    try {
      const res = await sendChat(text, user ? [] : history, page)
      setMessages((m) => [...m, { role: 'assistant', text: res.reply, products: res.products }])
      // Put the matches on the page itself as full product cards.
      if (res.products.length > 0) results.show(res.results_title || 'From your chat', res.products)
    } catch {
      setMessages((m) => [...m, { role: 'assistant', text: "Sorry, I can't reach the shop right now. Please try again." }])
    } finally {
      setBusy(false)
    }
  }

  // Buttons elsewhere ("Ask the assistant about this") open the panel and can send a question.
  const sendRef = useRef(send)
  sendRef.current = send
  useEffect(() => {
    function onOpen(e: Event) {
      setOpen(true)
      setOpened(true)
      const q = (e as CustomEvent<string | undefined>).detail
      if (q) setTimeout(() => sendRef.current(q), 150)
    }
    window.addEventListener(OPEN_CHAT, onOpen)
    return () => window.removeEventListener(OPEN_CHAT, onOpen)
  }, [])

  return (
    <div className="chat">
      {open && (
        <div className="chat-panel" role="dialog" aria-label="Chat with Campus Customs">
          <div className="chat-head">
            <div className="who">
              <span className="avatar">Y</span>
              <div>
                <strong>Campus Customs Assistant</strong>
                <small className="chat-sub">
                  <span className="online" />
                  {user ? `Signed in as ${user.first_name || user.name} · chat is saved` : 'Guest · log in to save this chat'}
                </small>
              </div>
            </div>
            <div className="chat-head-actions">
              {messages.length > 1 && (
                <button className="chat-new" onClick={newChat} title="Start a new chat">New chat</button>
              )}
              <button onClick={() => setOpen(false)} aria-label="Close chat">×</button>
            </div>
          </div>
          <div className="chat-body">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === 'assistant' && <span className="avatar" aria-hidden>Y</span>}
                <div className={`bubble ${m.role}`}>
                  {m.role === 'assistant' ? <Markdown>{m.text}</Markdown> : m.text}
                </div>
                {m.products && m.products.length > 0 && (
                  <div className="chat-cards">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-card">
                        <img src={p.image_url} alt="" />
                        <span className="chat-card-name">{p.name}</span>
                        <span className="chat-card-price">{formatPrice(p.price)}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && (
              <div className="msg assistant">
                <span className="avatar" aria-hidden>Y</span>
                <div className="bubble assistant" aria-label="Assistant is checking the shelves">
                  <span className="typing-dots"><i /><i /><i /></span>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
          {showChips && (
            <div className="chat-chips" aria-label="Suggested questions">
              {suggestions.map((q) => (
                <button key={q} type="button" className="chat-chip" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}
          {page.product_id && <div className="chat-context">The assistant can see the item on this page</div>}
          <form className="chat-input" onSubmit={onSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a hoodie, size, or price…"
              aria-label="Message"
              maxLength={2000}
            />
            <button type="submit" disabled={busy || !input.trim()}>Send</button>
          </form>
        </div>
      )}
      <button
        className={`chat-fab ${!opened && !open ? 'nudge' : ''}`}
        onClick={() => {
          setOpen((o) => !o)
          setOpened(true)
        }}
        aria-expanded={open}
      >
        <span className="avatar" aria-hidden>Y</span>
        {open ? 'Close' : 'Chat with us'}
      </button>
    </div>
  )
}
