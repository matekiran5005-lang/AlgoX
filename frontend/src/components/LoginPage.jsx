import { useState } from 'react'
import { login } from '../services/api.js'

export default function LoginPage({ onLogin }) {
  const [clientId, setClientId] = useState('')
  const [accessToken, setAccessToken] = useState('')
  const [isDemo, setIsDemo] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const data = await login({
        client_id: clientId,
        access_token: accessToken,
        is_demo: isDemo,
      })

      if (data.status === 'success') {
        onLogin(data.user_id)
      } else {
        setError(data.message || 'Login failed')
      }
    } catch (err) {
      const msg = err.response?.data?.message || err.message || 'Connection error'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // ── Demo quick-login (uses placeholder tokens for UI demo) ──
  const handleDemoLogin = () => {
    setClientId('demo')
    setAccessToken('demo-token')
    setIsDemo(true)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-900 via-dhan-purple to-dhan-amber flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-extrabold text-white mb-3">
            Algo<span className="text-yellow-400">X</span>
          </h1>
          <p className="text-blue-100 text-lg">NIFTY 9:45 CE Strategy</p>
          <p className="text-blue-200/60 text-sm mt-1">Multi-User Algo Trading Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Error message */}
          {error && (
            <div className="bg-red-500/20 border border-red-400/50 text-red-200 px-4 py-3 rounded-xl text-sm">
              ⚠️ {error}
            </div>
          )}

          {/* Client ID */}
          <div>
            <label className="block text-sm font-medium text-blue-100 mb-2">
              Dhan Client ID
            </label>
            <input
              type="text"
              placeholder="e.g. 1000000001"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-blue-300/50 focus:outline-none focus:ring-2 focus:ring-yellow-400/50"
              required
            />
          </div>

          {/* Access Token */}
          <div>
            <label className="block text-sm font-medium text-blue-100 mb-2">
              Access Token
            </label>
            <input
              type="password"
              placeholder="JWT token from Dhan app"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-blue-300/50 focus:outline-none focus:ring-2 focus:ring-yellow-400/50"
              required
            />
          </div>

          {/* Demo Mode Toggle */}
          <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/10">
            <div>
              <label className="text-sm font-medium text-blue-100">Demo / Paper Trading</label>
              <p className="text-xs text-blue-300/60 mt-1">
                {isDemo
                  ? 'Virtual ₹10,000 capital • Simulated orders'
                  : 'Real Dhan account • Live orders'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsDemo(!isDemo)}
              className={`relative inline-flex h-6 w-12 items-center rounded-full transition-colors ${
                isDemo ? 'bg-green-500' : 'bg-gray-600'
              }`}
            >
              <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                isDemo ? 'translate-x-6' : 'translate-x-1'
              }`} />
            </button>
          </div>

          {/* OAuth Button */}
          <button
            type="button"
            onClick={() => {
              // Dhan OAuth flow
              const redirectUri = encodeURIComponent(window.location.origin + '/login')
              window.location.href = `https://api.dhan.co/auth/authorize?client_id=${encodeURIComponent(clientId)}&redirect_uri=${redirectUri}`
            }}
            className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600/20 border border-blue-400/50 text-blue-100 rounded-xl hover:bg-blue-600/30 transition"
          >
            <span>🔐</span>
            <span>Dhan OAuth Login</span>
          </button>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-yellow-400 to-yellow-300 text-gray-900 font-bold rounded-xl hover:from-yellow-300 hover:to-yellow-200 transition transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin">⚡</span> Loading...
              </span>
            ) : 'Login & Launch'}
          </button>
        </form>

        {/* Quick demo login */}
        <div className="mt-6 text-center">
          <button
            onClick={handleDemoLogin}
            className="text-sm text-blue-200 hover:text-white hover:underline transition"
          >
            Skip login – Try demo mode with placeholder credentials
          </button>
        </div>
      </div>
    </div>
  )
}