import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api'

export const LOW_STOCK = 20

// Stock badge from live inventory (Problem 8). Undefined when the API didn't send stock.
export function stockBadge(p: Product): { label: string; tone: 'low' | 'partial' | 'ok' | 'out' } | undefined {
  if (!p.inventory || p.total_stock === undefined) return undefined
  if (p.total_stock === 0) return { label: 'Sold out', tone: 'out' }
  if (p.total_stock <= LOW_STOCK) return { label: `Only ${p.total_stock} left`, tone: 'low' }
  if (p.inventory.some((s) => s.quantity === 0)) return { label: 'Some sizes sold out', tone: 'partial' }
  return { label: 'In stock', tone: 'ok' }
}

export default function ProductCard({ product }: { product: Product }) {
  const badge = stockBadge(product)
  const sizes = product.inventory?.filter((s) => s.quantity > 0).map((s) => s.size)

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {badge && <span className={`stock-badge ${badge.tone}`}>{badge.label}</span>}
      </div>
      <div className="product-body">
        <h3>{product.name}</h3>
        <p className="price">{formatPrice(product.price)}</p>
        <p className="desc">{product.description}</p>
        {sizes && (
          <p className="sizes-line">
            <span>Sizes:</span>
            {sizes.length ? sizes.map((s) => <b key={s}>{s}</b>) : <em>none in stock</em>}
          </p>
        )}
        <span className="view">View details →</span>
      </div>
    </Link>
  )
}
