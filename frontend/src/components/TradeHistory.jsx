import { useState, useEffect, useCallback } from 'react'
import { getTradeHistory } from '../services/api.js'

export default function TradeHistory({ userId }) {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  const fetchTrades = useCallback(async () => {
    try {
      const data = await getTradeHistory(userId)
      setTrades(data.trades || [])
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }, [userId])

  useEffect(() => {
    fetchTrades()
    const interval = setInterval(fetchTrades, 15000)
    return () => clearInterval(interval)
  }, [fetchTrades])

  const filtered = trades.filter(t => {
    if (filter === 'demo') return t.is_demo
    if (filter === 'real') return !t.is_demo
    return true
  }).filter(t =>
    t.strike.toString().includes(searchTerm) ||
    t.date.includes(searchTerm) ||
    t.status.includes(searchTerm)
  )

  const closed = filtered.filter(t => t.pnl !== null)
  const totalPnl = closed.reduce((sum, t) => sum + (t.pnl || 0), 0)
  const winCount = closed.filter(t => t.pnl > 0).length
  const lossCount = closed.filter(t => t.pnl < 0).length
  const winRate = closed.length > 0 ? (winCount / closed.length * 100).toFixed(1) : '0'

  if (loading) {
    return <div className="flex justify-center items-center min-h-[300px]">
      <div className="text-center"><div className="animate-spin text-3xl mb-2">📊</div>
        <p className="text-gray-600">Loading trade history…</p></div>
    </div>
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <SummaryCard title="Total Trades" value={trades.length} color="text-gray-600" />
        <SummaryCard title="Total P&amp;L" value={`₹${totalPnl.toFixed(2)}`} color={totalPnl >= 0 ? 'text-green-600' : 'text-red-600'} />
        <SummaryCard title="Win Rate" value={`${winRate}%`} color="text-blue-600" />
        <SummaryCard title="W/L" value={`${winCount}W - ${lossCount}L`} color="text-gray-600" />
      </div>

      <div className="flex flex-col sm:flex-row gap-4 justify-between items-center">
        <div className="flex gap-2">
          <button onClick={() => setFilter('all')} className={`px-4 py-2 rounded-xl text-sm font-medium transition ${filter === 'all' ? 'bg-primary-600 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}>All</button>
          <button onClick={() => setFilter('demo')} className={`px-4 py-2 rounded-xl text-sm font-medium transition ${filter === 'demo' ? 'bg-blue-600 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}>Demo</button>
          <button onClick={() => setFilter('real')} className={`px-4 py-2 rounded-xl text-sm font-medium transition ${filter === 'real' ? 'bg-green-600 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}>Real</button>
        </div>
        <input type="text" placeholder="Search by strike or date..." value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10 pr-4 py-2 w-64 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-300 outline-none text-sm" />
      </div>

      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Date</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Strike</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Entry</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Exit</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">SL</th>
                <th className="px-4 py-3 text-right font-medium text-gray-700">P&amp;L</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Status</th>
                <th className="px-4 py-3 text-center font-medium text-gray-700">Mode</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan="8" className="text-center py-12 text-gray-400">📭 No trades found</td></tr>
              ) : (
                filtered.map((trade) => (
                  <tr key={trade.id} className="border-b border-gray-100 hover:bg-gray-50/50">
                    <td className="px-4 py-3 text-gray-700">{trade.date}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{trade.strike} {trade.option_type}</td>
                    <td className="px-4 py-3 text-gray-600">₹{trade.entry}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {trade.exit !== null && trade.exit !== undefined ? `₹${trade.exit}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">₹{trade.sl_price}</td>
                    <td className="px-4 py-3 font-bold text-right">
                      {trade.pnl !== null && trade.pnl !== undefined ? (
                        <span className={trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {trade.pnl >= 0 ? '▲' : '▼'} ₹{Math.abs(trade.pnl).toFixed(2)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={trade.status} /></td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs ${trade.is_demo ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
                        {trade.is_demo ? 'Demo' : 'Real'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function SummaryCard({ title, value, color }) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-4 text-center border border-gray-100">
      <p className="text-sm text-gray-500 mb-1">{title}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function StatusBadge({ status }) {
  const configs = {
    OPEN: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Open' },
    SL_HIT: { bg: 'bg-red-100', text: 'text-red-700', label: 'SL Hit' },
    TSL_EXIT: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'TSL Exit' },
    TIME_EXIT: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Time Exit' },
    MANUAL_EXIT: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Manual' },
  }
  const cfg = configs[status] || { bg: 'bg-gray-100', text: 'text-gray-700', label: status }
  return <span className={`px-3 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>{cfg.label}</span>
}