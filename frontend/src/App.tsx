import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import Home from './pages/Home'
import Products from './pages/Products'
import About from './pages/About'
import Login from './pages/Login'
import Signup from './pages/Signup'
import NotFound from './pages/NotFound'
import ProductDetail from './pages/ProductDetail'
import ChatWidget from './components/ChatWidget'
import ChatResults from './components/ChatResults'

export default function App() {
  const { pathname } = useLocation()
  // Start each page at the top. Chat cards stay in memory while you open a product and come back.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  const onDetailPage = pathname.startsWith('/products/')

  return (
    <div className="app">
      <NavBar />
      <main className="page">
        {!onDetailPage && <ChatResults />}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
    </div>
  )
}
