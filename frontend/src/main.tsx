import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import '@fontsource-variable/inter'
import '@fontsource/libre-baskerville/400.css'
import '@fontsource/libre-baskerville/700.css'
import '@fontsource/graduate'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth'
import { ChatResultsProvider } from './chatResults'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatResultsProvider>
          <App />
        </ChatResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
