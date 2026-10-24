import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, fetchSimilar, formatPrice, type Product } from '../api'
import { openChat } from '../chatBus'
import { swatch } from '../colors'
import ProductCard, { stockBadge } from '../components/ProductCard'

export default function ProductDetail() {
  const { id = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [similar, setSimilar] = useState<Product[]>([])
  const [size, setSize] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setProduct(null)
    setSimilar([])
    setSize(null)
    setError('')
    fetchProduct(id)
      .then(setProduct)
      .catch(() => setError('We could not find that product.'))
    fetchSimilar(id).then(setSimilar).catch(() => setSimilar([]))
  }, [id])

  if (error)
    return (
      <section className="section narrow">
        <p>{error}</p>
        <Link to="/products">← Back to all products</Link>
      </section>
    )
  if (!product) return <section className="section"><p className="muted">Loading…</p></section>

  const badge = stockBadge(product)
  const chosen = product.inventory?.find((s) => s.size === size)

  // Zoom follows the cursor.
  function onMove(e: MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.setProperty('--zx', `${((e.clientX - r.left) / r.width) * 100}%`)
    e.currentTarget.style.setProperty('--zy', `${((e.clientY - r.top) / r.height) * 100}%`)
  }

  return (
    <>
      <section className="section">
        <nav className="crumbs" aria-label="Breadcrumb">
          <Link to="/">Home</Link><span>/</span><Link to="/products">Products</Link><span>/</span>
          {product.name}
        </nav>
        <div className="detail">
          <div className="detail-img" onMouseMove={onMove}>
            <img src={product.image_url} alt={product.name} />
          </div>
          <div className="detail-info">
            <p className="eyebrow">{product.garment_type}</p>
            <h1>{product.name}</h1>
            <p className="detail-price">
              {formatPrice(product.price)}{' '}
              {badge && <span className={`stock-badge inline ${badge.tone}`}>{badge.label}</span>}
            </p>
            <p>{product.description}</p>

            <h3>Colors</h3>
            <div className="swatches">
              {product.colors.map((c) => (
                <span className="swatch" key={c}>
                  <i style={{ background: swatch(c) }} />
                  {c}
                </span>
              ))}
            </div>

            <h3>Pick a size</h3>
            <div className="size-picker" role="group" aria-label="Sizes">
              {product.inventory?.map((s) => (
                <button
                  key={s.size}
                  className={size === s.size ? 'on' : ''}
                  disabled={s.quantity === 0}
                  onClick={() => setSize(s.size)}
                  aria-pressed={size === s.size}
                  title={s.quantity === 0 ? `${s.size} is sold out` : `${s.quantity} in stock`}
                >
                  <strong>{s.size}</strong>
                  <small>{s.quantity === 0 ? 'Sold out' : `${s.quantity} left`}</small>
                </button>
              ))}
            </div>
            {chosen ? (
              <p className={`size-status ${chosen.quantity <= 5 ? 'low' : 'good'}`}>
                {chosen.quantity <= 5 ? `Hurry, only ${chosen.quantity} left in ${chosen.size}.` : `${chosen.size} is in stock (${chosen.quantity} on the shelf).`}
              </p>
            ) : (
              <p className="muted small">{product.total_stock} in stock across all sizes. Crossed-out sizes are sold out.</p>
            )}

            <div className="detail-actions">
              <button className="btn btn-ask" onClick={() => openChat(size ? `Is this in stock in ${size}?` : 'What colors does this come in?')}>
                Ask the assistant about this
              </button>
              <Link to="/products" className="btn btn-ghost">Keep shopping</Link>
            </div>
            <p className="store-note">See it in person at Yale Bulldog Blue, 57 Broadway, New Haven. Stock shown here is live from our inventory.</p>
          </div>
        </div>
      </section>

      {similar.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>You might also like</h2>
          </div>
          <div className="product-grid">
            {similar.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}
    </>
  )
}
