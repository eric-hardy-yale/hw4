import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function onLogout() {
    close()
    await logout()
    navigate('/')
  }

  return (
    <header className="site-header">
      <div className="announce">Officially licensed Yale gear · 57 Broadway, New Haven</div>
      <nav className="nav" aria-label="Main">
        <Link to="/" className="brand" onClick={close}>
          <span className="brand-mark">Y</span>
          <span className="brand-text">
            Campus Customs
            <small>Yale Bulldog Blue</small>
          </span>
        </Link>

        <button
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="nav-links"
          onClick={() => setOpen((o) => !o)}
        >
          Menu
        </button>

        <div id="nav-links" className={`nav-links ${open ? 'open' : ''}`}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          <span className="nav-spacer" />
          {user ? (
            <>
              <span className="nav-user">Hi, {user.first_name || user.name}</span>
              <button className="nav-button" onClick={onLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>
                Log in
              </NavLink>
              <NavLink to="/signup" className="nav-cta" onClick={close}>
                Create account
              </NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
