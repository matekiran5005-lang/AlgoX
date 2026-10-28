/**
 * AlgoX API Service
 * Axios instance with automatic user_id handling.
 *
 * Usage:
 *   api.login({ client_id, access_token, is_demo })
 *   api.getDashboard(userId)
 *   api.toggleAlgo(userId, true)
 *   ...
 */
import axios from 'axios'

// The backend URL (Flask on port 3000 in production; Vite proxy in dev)
const API_BASE = import.meta.env?.VITE_API_URL || ''
const API_PREFIX = '/api'

const api = axios.create({
  baseURL: API_BASE ? `${API_BASE}${API_PREFIX}` : API_PREFIX,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request interceptor: attach user_id ────────────────────
api.interceptors.request.use(
  (config) => {
    const userId = localStorage.getItem('algox_user_id')
    if (userId && !config.url.includes('/login') && !config.url.includes('/health')) {
      if (config.method === 'post' && !config.data?.user_id) {
        config.data = { ...config.data, user_id: userId }
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response interceptor: auto-handle errors ───────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('algox_user_id')
      window.dispatchEvent(new Event('auth:logout'))
    }
    return Promise.reject(error)
  }
)


// ════════════════════════════════════════════════════════════
// AUTH
// ════════════════════════════════════════════════════════════

/** POST /api/login — Login with Dhan Client ID + Access Token */
export const login = async ({ client_id, access_token, is_demo }) => {
  const resp = await api.post('/login', { client_id, access_token, is_demo })
  const data = resp.data
  if (data.status === 'success') {
    localStorage.setItem('algox_user_id', data.user_id)
  }
  return data
}

/** GET /api/health — Health check */
export const healthCheck = async () => {
  const resp = await api.get('/health')
  return resp.data
}

/** GET /api/users/count — User count */
export const getUserCount = async () => {
  const resp = await api.get('/users/count')
  return resp.data
}

/** POST /api/logout — Clear local session (no server-side logout needed) */
export const logout = () => {
  localStorage.removeItem('algox_user_id')
  window.dispatchEvent(new Event('auth:logout'))
}


// ════════════════════════════════════════════════════════════
// DASHBOARD & PORTFOLIO
// ════════════════════════════════════════════════════════════

/** GET /api/dashboard/:user_id */
export const getDashboard = async (userId) => {
  const resp = await api.get(`/dashboard/${userId}`)
  return resp.data
}

/** GET /api/refresh/:user_id */
export const refreshData = async (userId) => {
  const resp = await api.get(`/refresh/${userId}`)
  return resp.data
}

/** GET /api/holdings/:user_id */
export const getHoldings = async (userId) => {
  const resp = await api.get(`/holdings/${userId}`)
  return resp.data
}

/** GET /api/positions/:user_id */
export const getPositions = async (userId) => {
  const resp = await api.get(`/positions/${userId}`)
  return resp.data
}


// ════════════════════════════════════════════════════════════
// OPTION CHAIN
// ════════════════════════════════════════════════════════════

/** GET /api/optionchain/:user_id */
export const getOptionChain = async (userId) => {
  const resp = await api.get(`/optionchain/${userId}`)
  return resp.data
}

/** GET /api/optionchain/nearest-ce/:user_id */
export const getNearestCE = async (userId) => {
  const resp = await api.get(`/optionchain/nearest-ce/${userId}`)
  return resp.data
}


// ════════════════════════════════════════════════════════════
// ORDERS
// ════════════════════════════════════════════════════════════

/** POST /api/orders/place */
export const placeOrder = async (orderData) => {
  const resp = await api.post('/orders/place', orderData)
  return resp.data
}

/** GET /api/orders/:user_id */
export const getOrders = async (userId) => {
  const resp = await api.get(`/orders/${userId}`)
  return resp.data
}


// ════════════════════════════════════════════════════════════
// STRATEGY CONTROL
// ════════════════════════════════════════════════════════════

/** POST /api/strategy/toggle */
export const toggleAlgo = async (userId, active) => {
  const resp = await api.post('/strategy/toggle', { user_id: userId, active })
  return resp.data
}

/** POST /api/demo/toggle */
export const toggleDemoMode = async (userId, isDemo) => {
  const resp = await api.post('/demo/toggle', { user_id: userId, is_demo: isDemo })
  return resp.data
}

/** POST /api/strategy/entry */
export const manualEntry = async (userId) => {
  const resp = await api.post('/strategy/entry', { user_id: userId })
  return resp.data
}

/** POST /api/strategy/exit */
export const manualExit = async (userId) => {
  const resp = await api.post('/strategy/exit', { user_id: userId })
  return resp.data
}

/** GET /api/position/:user_id */
export const getPosition = async (userId) => {
  const resp = await api.get(`/position/${userId}`)
  return resp.data
}

/** GET /api/strategy/config */
export const getStrategyConfig = async () => {
  const resp = await api.get('/strategy/config')
  return resp.data
}

/** POST /api/strategy/config */
export const updateStrategyConfig = async (config) => {
  const resp = await api.post('/strategy/config', config)
  return resp.data
}


// ════════════════════════════════════════════════════════════
// TRADE HISTORY & ALERTS
// ════════════════════════════════════════════════════════════

/** GET /api/trade-history/:user_id */
export const getTradeHistory = async (userId) => {
  const resp = await api.get(`/trade-history/${userId}`)
  return resp.data
}

/** GET /api/alerts */
export const getAlerts = async () => {
  const resp = await api.get('/alerts')
  return resp.data
}

/** GET /api/users */
export const getAllUsers = async () => {
  const resp = await api.get('/users')
  return resp.data
}


export default api