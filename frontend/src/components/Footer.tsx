import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div>
        <strong>Campus Customs</strong>
        <p>57 Broadway, New Haven, CT 06511</p>
      </div>
      <div className="footer-links">
        <Link to="/products">Shop</Link>
        <Link to="/about">About Us</Link>
        <Link to="/signup">Create account</Link>
      </div>
      <p className="fine">© {new Date().getFullYear()} Campus Customs. Class project site, not the official store.</p>
    </footer>
  )
}
