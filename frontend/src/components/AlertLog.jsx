import { useState, useEffect, useCallback } from 'react'
import { getAlerts, getAllUsers } from '../services/api.js'

export default function AlertLog({ userId }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [users, setUsers] = useState([])

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await getAlerts()
      setAlerts(data.alerts || [])
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }, [])

  const fetchUsers = useCallback(async () => {
    try {
      const data = await getAllUsers()
      setUsers(data.users || [])
    } catch (err) { console.error(err) }
  }, [])

  useEffect(() => {
    fetchAlerts()
    fetchUsers()
    const interval = setInterval(fetchAlerts, 30000)
    return () => clearInterval(interval)
  }, [fetchAlerts, fetchUsers])

  const filtered = filter === 'all'
    ? alerts
    : alerts.filter(a => a.level.toLowerCase() === filter)

  const levelConfig = {
    INFO: { bg: 'bg-blue-50', text: 'text-blue-700', icon: 'ℹ️' },
    WARNING: { bg: 'bg-amber-50', text: 'text-amber-700', icon: '⚠️' },
    ERROR: { bg: 'bg-red-50', text: 'text-red-700', icon: '❌' },
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">System Alerts</h1>
        <div className="flex gap-2">
          <button onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
              filter === 'all' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}>All</button>
          <button onClick={() => setFilter('error')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
              filter === 'error' ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}>Errors</button>
          <button onClick={() => setFilter('warning')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
              filter === 'warning' ? 'bg-amber-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}>Warnings</button>
        </div>
      </div>

      {/* Registered Users */}
      <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
        <p className="text-sm text-blue-800 font-medium mb-2">
          Registered Users: <span className="font-bold">{users.length}</span>
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {users.map(u => (
            <div key={u.user_id} className="bg-white rounded-lg p-3 border border-gray-200">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-mono text-xs text-gray-600">ID: {u.client_id}</p>
                  <p className="text-sm text-gray-800 mt-1">{u.user_id.slice(0, 20)}…</p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  u.is_demo ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                }`}>
                  {u.is_demo ? 'Demo' : 'Real'}
                </span>
              </div>
              <div className="mt-2 flex gap-4 text-xs text-gray-500">
                <span>Algo: {u.algo_active ? '🔴 ON' : '⚪ OFF'}</span>
                <span>Capital: ₹{u.is_demo ? u.demo_capital : u.capital}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Alerts List */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Level</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Message</th>
                <th className="px-4 py-3 text-left font-medium text-gray-700">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="3" className="text-center py-8 text-gray-400">⏳ Loading alerts…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="3" className="text-center py-8 text-gray-400">📭 No alerts</td></tr>
              ) : (
                filtered.map((alert, i) => {
                  const cfg = levelConfig[alert.level] || levelConfig.INFO
                  return (
                    <tr key={i} className={`border-b border-gray-100 ${cfg.bg}`}>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${cfg.text}`}>
                          {cfg.icon} {alert.level}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-700">{alert.message}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {new Date(alert.timestamp).toLocaleString('en-IN')}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
