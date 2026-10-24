import { useEffect, useRef } from 'react'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

// The on-page card section the chat agent fills in. Each card links to the single-item page.
export default function ChatResults() {
  const { title, products, version, clear } = useChatResults()
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    if (version > 0) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [version])

  if (products.length === 0) return null

  return (
    <section ref={ref} className="section chat-results" aria-live="polite" key={version}>
      <div className="chat-results-head">
        <div>
          <p className="eyebrow">From your chat</p>
          <h2>{title}</h2>
          <p className="muted small">
            {products.length} {products.length === 1 ? 'item' : 'items'} our assistant found. Prices and stock are live.
          </p>
        </div>
        <button className="chip" onClick={clear}>Clear</button>
      </div>
      <div className="product-grid">
        {products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}
