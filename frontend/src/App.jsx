import { useState, useEffect, useCallback } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import LoginPage from './components/LoginPage.jsx'
import Dashboard from './components/Dashboard.jsx'
import TradeHistory from './components/TradeHistory.jsx'
import StrategyConfig from './components/StrategyConfig.jsx'
import AlertLog from './components/AlertLog.jsx'
import Header from './components/Header.jsx'
import { healthCheck, logout } from './services/api.js'

function App() {
  const navigate = useNavigate()
  const [userId, setUserId] = useState(() => localStorage.getItem('algox_user_id'))
  const [serverStatus, setServerStatus] = useState(null)

  // ── Check server health on mount ───────────────────────
  const checkHealth = useCallback(async () => {
    try {
      const data = await healthCheck()
      setServerStatus(data)
    } catch (e) {
      setServerStatus(null)
    }
  }, [])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [checkHealth])

  // ── Listen for auth:logout events ────────────────────────
  useEffect(() => {
    const handleLogout = () => {
      setUserId(null)
      navigate('/login')
    }
    window.addEventListener('auth:logout', handleLogout)
    return () => window.removeEventListener('auth:logout', handleLogout)
  }, [navigate])

  const handleLogin = (uid) => {
    setUserId(uid)
    navigate('/app/dashboard')
  }

  const handleLogout = () => {
    logout()
    setUserId(null)
    navigate('/login')
  }

  const requireAuth = (element) => {
    return userId ? element : <Navigate to="/login" replace />
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to={userId ? "/app/dashboard" : "/login"} replace />} />
      <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
      <Route
        path="/app/dashboard"
        element={requireAuth(
          <Layout userId={userId} onLogout={handleLogout} serverStatus={serverStatus}>
            <Dashboard userId={userId} />
          </Layout>
        )}
      />
      <Route
        path="/app/trades"
        element={requireAuth(
          <Layout userId={userId} onLogout={handleLogout} serverStatus={serverStatus}>
            <TradeHistory userId={userId} />
          </Layout>
        )}
      />
      <Route
        path="/app/strategy"
        element={requireAuth(
          <Layout userId={userId} onLogout={handleLogout} serverStatus={serverStatus}>
            <StrategyConfig userId={userId} />
          </Layout>
        )}
      />
      <Route
        path="/app/alerts"
        element={requireAuth(
          <Layout userId={userId} onLogout={handleLogout} serverStatus={serverStatus}>
            <AlertLog userId={userId} />
          </Layout>
        )}
      />
      <Route path="*" element={<Navigate to={userId ? "/app/dashboard" : "/login"} replace />} />
    </Routes>
  )
}

// Layout component (header + page)
function Layout({ userId, onLogout, serverStatus, children }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header userId={userId} onLogout={onLogout} serverStatus={serverStatus} />
      <main className="flex-1 container mx-auto px-4 py-6 pb-20 md:pb-6">
        <div className="animate-fade-in">
          {children}
        </div>
      </main>
      <footer className="text-center text-xs text-gray-400 pb-4">
        <span className="font-semibold text-primary-600">AlgoX</span> • NIFTY 9:45 Strategy •
        Multi-User Algo Trading Platform
      </footer>
    </div>
  )
}

export default App