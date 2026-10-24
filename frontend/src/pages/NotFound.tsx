import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="section narrow">
      <h1>Page not found</h1>
      <p>
        That page wandered off. <Link to="/">Head back home</Link>.
      </p>
    </section>
  )
}
