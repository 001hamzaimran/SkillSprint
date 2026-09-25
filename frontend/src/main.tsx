import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { Toaster } from 'sonner'
import App from './App'
import './index.css'

const basename = window.location.pathname.startsWith('/app') ? '/app' : undefined

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <App />
      <Toaster position="top-right" richColors />
    </BrowserRouter>
  </StrictMode>,
)
