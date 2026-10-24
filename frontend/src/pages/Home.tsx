import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, formatPrice, type Product } from '../api'
import { openChat } from '../chatBus'
import ProductCard from '../components/ProductCard'

const HERO_IDS = [
  'district-vit-hoodie-vintage-bulldog',
  '2025-yale-vs-harvard-t-shirt',
  'berkeley-1-4-zip',
  'brooks-brothers-bomber-jacket-yale',
]
const PICK_IDS = ['basic-hoodie-big-yale', 'baseball-left-chest-crewneck', 'big-yale-tri-blend-t-shirt', 'benjamin-franklin-fleece-jacket']

const categories = [
  { title: 'Hoodies', match: 'hood', image: 'basic-hoodie-big-yale', blurb: 'Heavyweight pullovers for long walks across Old Campus.' },
  { title: 'Crewnecks', match: 'crewneck', image: 'baseball-left-chest-crewneck', blurb: 'Residential colleges, varsity sports, and classic wordmarks.' },
  { title: 'Tees', match: 't-shirt', image: 'big-yale-tri-blend-t-shirt', blurb: 'Easy everyday shirts, from vintage bulldogs to The Game.' },
  { title: 'Quarter-zips & fleece', match: 'zip', image: 'berkeley-1-4-zip', blurb: 'Layers that handle a New Haven October.' },
]

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]))
  }, [])
  const byId = useMemo(() => new Map(products.map((p) => [p.product_id, p])), [products])
  const lowest = (match: string) => {
    const prices = products.filter((p) => p.garment_type.toLowerCase().includes(match)).map((p) => p.price)
    return prices.length ? Math.min(...prices) : undefined
  }
  const hero = HERO_IDS.map((id) => byId.get(id)).filter(Boolean) as Product[]
  const picks = PICK_IDS.map((id) => byId.get(id)).filter(Boolean) as Product[]

  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <div>
            <p className="eyebrow">Officially licensed · New Haven, CT</p>
            <h1>Wear your Bulldog pride every day.</h1>
            <p className="lead">
              Sweatshirts, tees, and jackets for students, alumni, and the families cheering them on.
              Can't find your size? Ask our chat assistant. It checks real stock before it answers.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-light">Shop the collection</Link>
              <button className="btn btn-outline" onClick={() => openChat()}>Ask the assistant</button>
            </div>
            <div className="trust">
              <span>Officially licensed</span>
              <span>Live stock, size by size</span>
              <span>57 Broadway, New Haven</span>
            </div>
          </div>
          <div className="hero-collage" aria-label="Featured products">
            {hero.map((p) => (
              <Link key={p.product_id} to={`/products/${p.product_id}`}>
                <img src={p.image_url} alt={p.name} />
                <span><em>{p.name.replace(/^District Vit /, '')}</em><b>{formatPrice(p.price)}</b></span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>Find your fit</h2>
          <Link to="/products">See all {products.length || ''} items →</Link>
        </div>
        <div className="cat-grid">
          {categories.map((c) => {
            const from = lowest(c.match)
            const img = byId.get(c.image)?.image_url
            return (
              <Link to="/products" key={c.title} className="cat-tile">
                {img ? <img src={img} alt="" /> : <div style={{ aspectRatio: '4 / 3' }} />}
                <div>
                  <h3>{c.title}</h3>
                  <p>{c.blurb}</p>
                  {from !== undefined && <span className="from">From {formatPrice(from)}</span>}
                </div>
              </Link>
            )
          })}
        </div>
      </section>

      <section className="section">
        <div className="assist-band">
          <span className="avatar">Y</span>
          <div>
            <h2>Not sure what fits? Just ask.</h2>
            <p>
              Our assistant searches the whole shop, checks stock in your size, and puts what it finds right
              on the page. Try "anything with Handsome Dan?"
            </p>
          </div>
          <button className="btn btn-ask" onClick={() => openChat('Anything with Handsome Dan?')}>
            Try it
          </button>
        </div>
      </section>

      {picks.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>New Haven staples</h2>
            <Link to="/products">Shop all →</Link>
          </div>
          <div className="product-grid">
            {picks.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}

      <section className="section split">
        <div>
          <h2>Gear for everyone in the family</h2>
          <p>
            Whether you live in Berkeley or Branford, row on the crew team, or are just the proudest
            Yale parent on the block, there's a design with your name on it. We stock residential
            colleges, varsity sports, graduate schools, and plenty of Handsome Dan.
          </p>
        </div>
        <div className="callout">
          <h3>Stop by the shop</h3>
          <p>57 Broadway, New Haven, CT 06511</p>
          <Link to="/about">More about us →</Link>
        </div>
      </section>
    </>
  )
}
