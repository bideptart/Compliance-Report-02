import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { RmdHistoryProvider } from './context/RmdHistoryContext.jsx'
import { FccHistoryProvider } from './context/FccHistoryContext.jsx'
import { ThemeProvider } from './context/ThemeContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <RmdHistoryProvider>
          <FccHistoryProvider>
            <App />
          </FccHistoryProvider>
        </RmdHistoryProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
