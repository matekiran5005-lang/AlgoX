import { useState, useEffect, useCallback } from 'react'
import {
  getDashboard, refreshData, toggleAlgo, toggleDemoMode,
  manualEntry, manualExit, getStrategyConfig
} from '../services/api.js'

export default function Dashboard({ userId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [strategy, setStrategy] = useState(null)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    if (!userId) return
    try {
      const [dashboard, config] = await Promise.all([
        getDashboard(userId),
        getStrategyConfig(),
      ])
      setData(dashboard)
      setStrategy(config?.config)
    } catch (err) {
      setError(err.response?.data?.message || err.message)
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await refreshData(userId)
      await fetchData()
    } catch (err) { console.error(err) }
    finally { setRefreshing(false) }
  }

  const handleToggleAlgo = async () => {
    const next = !data.algo_active
    const msg = next
      ? 'Algo ON karaycha? Auto trade 9:45 CE gheil (SL -20, TSL +10/+30).'
      : 'Algo OFF karaycha? Trading thambel, navin trade ghetla janar nahi.'
    if (!window.confirm(msg)) return
    try {
      await toggleAlgo(userId, next)
      setData((prev) => ({ ...prev, algo_active: next }))
    } catch (err) { console.error(err) }
  }

  const handleToggleDemo = async () => {
    try {
      await toggleDemoMode(userId, !data.is_demo)
      setData((prev) => ({
        ...prev, is_demo: !prev.is_demo,
        capital: !prev.is_demo ? 10000 : prev.capital,
      }))
    } catch (err) { console.error(err) }
  }

  const handleManualEntry = async () => {
    try { await manualEntry(userId); await fetchData() }
    catch (err) { console.error(err) }
  }

  const handleManualExit = async () => {
    try { await manualExit(userId); await fetchData() }
    catch (err) { console.error(err) }
  }

  if (loading || !data) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">⚡</div>
          <p className="text-gray-600">Data Load hotay...</p>
        </div>
      </div>
    )
  }

  const { is_demo, algo_active, capital, today_pnl, current_trade, holdings } = data
  const safePnl = Number.isFinite(today_pnl) ? today_pnl : 0
  const safeCapital = Number.isFinite(capital) ? capital : 0

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-500/10 border border-red-400/30 text-red-700 px-4 py-3 rounded-xl text-sm">{error}</div>
      )}

      {/* User Header */}
      <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
        <h1 className="text-2xl font-bold text-gray-800">Namaste, {userId}</h1>
        <p className="text-sm text-gray-500 mt-1">Client ID: {userId}</p>
      </div>

      {/* Mode Banner */}
      <div className="flex gap-3">
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          is_demo ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
        }`}>
          {is_demo ? '📊 DEMO (Paper Trading)' : '💰 REAL Trading'}
        </span>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
          algo_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {algo_active ? '🟢 Algo ON' : '🔴 Algo OFF'}
        </span>
      </div>

      {/* Top Row: Available / Total / Trades / Profit */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card text="center">
          <CardTitle>Available Balance</CardTitle>
          <CardValue value={safeCapital} prefix="₹" />
        </Card>

        <Card text="center">
          <CardTitle>Total Balance</CardTitle>
          <CardValue value={data?.sodLimit || safeCapital} prefix="₹" />
        </Card>

        <Card text="center">
          <CardTitle>Trades</CardTitle>
          <div className="text-3xl font-bold text-primary-700">{holdings?.length || 0}</div>
        </Card>

        <Card text="center">
          <CardTitle>Profit</CardTitle>
          <div className={`text-3xl font-bold ${safePnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            ₹{Math.abs(safePnl).toLocaleString()}
          </div>
        </Card>
      </div>

      {/* Strategy Controls */}
      <Card>
        <CardTitle>Strategy Controls</CardTitle>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="col-span-2">
            <button onClick={handleToggleAlgo}
              className={`w-full py-3 rounded-xl font-bold text-lg transition ${
                algo_active ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-gray-400 hover:bg-gray-500 text-gray-900'
              }`}>
              {algo_active ? '🟢 STOP ALGO' : '⚡ START ALGO'}
            </button>
          </div>
          <div>
            <button onClick={handleToggleDemo}
              className={`w-full py-3 rounded-xl font-bold transition ${
                is_demo ? 'bg-blue-500 hover:bg-blue-600 text-white'
                : 'bg-gray-400 hover:bg-gray-500 text-gray-900'
              }`}>
              {is_demo ? '📊 DEMO' : '💰 REAL'}
            </button>
          </div>
          <div>
            <button onClick={handleRefresh} disabled={refreshing}
              className="w-full py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-medium">
              🔄 Refresh
            </button>
          </div>
        </div>
        {algo_active && (
          <p className="text-sm text-gray-500 mt-4 text-center">
            Auto-trading active: 9:45 CE (100–140), SL -20, TSL +10/+30
          </p>
        )}
      </Card>

      {/* Current Trade */}
      <Card>
        <CardTitle>Current Trade</CardTitle>
        {current_trade ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <Stat label="Strike" value={`${current_trade.strike} CE`} />
            <Stat label="Entry" value={current_trade.entry} prefix="₹" />
            <Stat label="SL" value={current_trade.sl} prefix="₹" color="text-red-600" />
            <Stat label="TSL" value={current_trade.tsl} prefix="₹" color="text-blue-600" />
            <Stat label="LTP" value={current_trade.ltp || '--'} prefix="₹" />
            <Stat label="Qty" value={current_trade.qty} />
            <Stat label="Unreal P&amp;L" value={current_trade.unrealized_pnl} prefix="₹"
              color={current_trade.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'} />
            <Stat label="Demo" value={current_trade.is_demo ? 'Yes' : 'No'} />
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p className="text-2xl mb-2">—</p>
            <p className="text-sm">No open position</p>
          </div>
        )}
      </Card>

      {/* Strategy Info */}
      {strategy && (
        <Card>
          <CardTitle>{strategy.name}</CardTitle>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-gray-500">Entry Band:</span> ₹{strategy.entry_price_min}–₹{strategy.entry_price_max}</div>
            <div><span className="text-gray-500">Lot Qty:</span> {strategy.lot_qty}</div>
            <div><span className="text-gray-500">Budget:</span> ₹{strategy.budget.toLocaleString()}</div>
            <div><span className="text-gray-500">SL:</span> Entry - {strategy.sl_points} pts</div>
            <div><span className="text-gray-500">TSL 1:</span> +{strategy.tsl_levels[0]?.trigger}→Entry+{strategy.tsl_levels[0]?.sl_offset}</div>
            <div><span className="text-gray-500">TSL 2:</span> +{strategy.tsl_levels[1]?.trigger}→Entry+{strategy.tsl_levels[1]?.sl_offset}</div>
            <div><span className="text-gray-500">Open:</span> {strategy.market_open}</div>
            <div><span className="text-gray-500">Close:</span> {strategy.market_close}</div>
          </div>
        </Card>
      )}
    </div>
  )
}

// ── Helper Components ─────────────────────────────────────
function Card({ children, text = '' }) {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
      <div className={text}>{children}</div>
    </div>
  )
}

function CardTitle({ children }) {
  return <h2 className="text-xl font-semibold text-gray-800 mb-4">{children}</h2>
}

function CardValue({ value, prefix = '', suffix = '' }) {
  const formatted = Number(value || 0).toLocaleString('en-IN')
  return <div className="text-3xl font-bold text-primary-700">{prefix}{formatted}{suffix}</div>
}

function Stat({ label, value, prefix = '', suffix = '', color = 'text-gray-700' }) {
  const display = value !== null && value !== undefined ? value : '--'
  return (
    <div className="bg-gray-50 rounded-xl p-3 text-center">
      <p className="text-xs text-gray-500 uppercase">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{prefix}{display}{suffix}</p>
    </div>
  )
}