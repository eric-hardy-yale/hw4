import { useEffect, useMemo, useState } from 'react'
import { fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'

const filters = [
  { label: 'All', match: '' },
  { label: 'Hoodies', match: 'hood' },
  { label: 'Crewnecks', match: 'crew' },
  { label: 'Tees', match: 't-shirt' },
  { label: 'Quarter-zips', match: 'quarter-zip' },
  { label: 'Jackets', match: 'jacket' },
]

const sorts = {
  featured: { label: 'Featured', fn: () => 0 },
  'price-asc': { label: 'Price: low to high', fn: (a: Product, b: Product) => a.price - b.price },
  'price-desc': { label: 'Price: high to low', fn: (a: Product, b: Product) => b.price - a.price },
  name: { label: 'Name: A–Z', fn: (a: Product, b: Product) => a.name.localeCompare(b.name) },
}
type SortKey = keyof typeof sorts

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortKey>('featured')
  const [inStockOnly, setInStockOnly] = useState('')

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('We could not load the catalogue. Is the backend running on port 8000?'))
      .finally(() => setLoading(false))
  }, [])

  const shown = useMemo(() => {
    const s = search.trim().toLowerCase()
    const list = products.filter((p) => {
      const type = p.garment_type.toLowerCase()
      if (filter && !type.includes(filter)) return false
      if (inStockOnly && !p.inventory?.some((x) => x.size === inStockOnly && x.quantity > 0)) return false
      if (!s) return true
      return [p.name, p.description, p.garment_type, ...p.colors, ...p.search_tags]
        .join(' ')
        .toLowerCase()
        .includes(s)
    })
    // Stable sort keeps the default order for ties.
    return [...list].sort(sorts[sort].fn)
  }, [products, filter, search, sort, inStockOnly])

  return (
    <section className="section">
      <p className="eyebrow">Products</p>
      <h1>Shop the collection</h1>

      <div className="toolbar">
        <div className="chips" role="group" aria-label="Filter by type">
          {filters.map((f) => (
            <button
              key={f.label}
              className={`chip ${filter === f.match ? 'active' : ''}`}
              onClick={() => setFilter(f.match)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="toolbar-right">
        <label className="select">
          In stock in
          <select value={inStockOnly} onChange={(e) => setInStockOnly(e.target.value)} aria-label="Only show items in stock in this size">
            <option value="">any size</option>
            {['XS', 'S', 'M', 'L', 'XL', 'XXL'].map((z) => (
              <option key={z} value={z}>{z}</option>
            ))}
          </select>
        </label>
        <label className="select">
          Sort
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} aria-label="Sort products">
            {Object.entries(sorts).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
        </label>
        <input
          className="search"
          type="search"
          placeholder="Search bulldog, Berkeley, navy…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search products"
        />
        </div>
      </div>

      {loading && <p className="muted">Loading products…</p>}
      {error && <div className="empty-state">{error}</div>}
      {!loading && !error && (
        <>
          <p className="muted small">{shown.length} of {products.length} items</p>
          <div className="product-grid">
            {shown.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
          {shown.length === 0 && <div className="empty-state">No items match that search.</div>}
        </>
      )}
    </section>
  )
}
