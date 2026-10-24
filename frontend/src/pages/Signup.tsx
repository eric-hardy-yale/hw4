import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { signup } from '../api'
import { useAuth } from '../auth'

const empty = { firstName: '', lastName: '', email: '', password: '', confirm: '' }

export default function Signup() {
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { setUser } = useAuth()
  const navigate = useNavigate()
  const set = (k: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value })

  const mismatch = form.confirm.length > 0 && form.confirm !== form.password

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    if (form.password !== form.confirm) return setError('Passwords do not match.')
    setBusy(true)
    try {
      const user = await signup({
        first_name: form.firstName,
        last_name: form.lastName,
        email: form.email,
        password: form.password,
      })
      setUser(user)
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section auth">
      <form className="auth-card" onSubmit={onSubmit}>
        <h1>Create account</h1>
        <p className="muted">Save your chats and get help finding your size.</p>
        <div className="row">
          <label>
            First name
            <input name="firstName" value={form.firstName} onChange={set('firstName')} required autoComplete="given-name" />
          </label>
          <label>
            Last name
            <input name="lastName" value={form.lastName} onChange={set('lastName')} required autoComplete="family-name" />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" value={form.email} onChange={set('email')} required autoComplete="email" />
        </label>
        <label>
          Password
          <input type="password" name="password" value={form.password} onChange={set('password')} required minLength={8} autoComplete="new-password" />
          <span className="hint">At least 8 characters.</span>
        </label>
        <label>
          Confirm password
          <input type="password" name="confirm" value={form.confirm} onChange={set('confirm')} required autoComplete="new-password" aria-invalid={mismatch} />
          {mismatch && <span className="hint bad">Passwords do not match.</span>}
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted small">
          Already have one? <Link to="/login">Log in</Link>
        </p>
      </form>
    </section>
  )
}
