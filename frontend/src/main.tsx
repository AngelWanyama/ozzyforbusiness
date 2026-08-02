import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Apply the saved Dark Mode preference immediately, before React even renders — previously this
// only ran inside Settings.tsx's own effect, so the whole app stayed light until the Settings
// page happened to mount, and reverted to light again on any fresh load elsewhere.
if (localStorage.getItem('ozzy_dark') === '1') {
  document.documentElement.classList.add('dark');
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)