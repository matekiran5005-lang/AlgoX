import { useState, useEffect, useCallback } from 'react'
import { getStrategyConfig, updateStrategyConfig } from '../services/api.js'

export default function StrategyConfig({ userId }) {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})

  const fetchConfig = useCallback(async () => {
    try {
      const data = await getStrategyConfig()
      setConfig(data.config)
    } catch (err) { console.error(err) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchConfig() }, [fetchConfig])

  const handleEdit = () => {
    setEditing(true)
    setForm({
      lot_qty: config.lot_qty,
      budget: config.budget,
      entry_price_min: config.entry_price_min,
      entry_price_max: config.entry_price_max,
      sl_points: config.sl_points,
      market_open: config.market_open,
      market_close: config.market_close,
      tsl_levels: config.tsl_levels ? [...config.tsl_levels] : [],
    })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateStrategyConfig(form)
      await fetchConfig()
      setEditing(false)
    } catch (err) { console.error(err) }
    finally { setSaving(false) }
  }

  if (loading) return <div className="text-center py-12 text-gray-500">⏳ Loading…</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">Strategy Configuration</h1>
        {editing ? (
          <div className="flex gap-2">
            <button onClick={() => setEditing(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-xl">Cancel</button>
            <button onClick={handleSave} disabled={saving} className="px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700">
              {saving ? '💾 Saving…' : '💾 Save'}
            </button>
          </div>
        ) : (
          <button onClick={handleEdit} className="px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700">✏️ Edit</button>
        )}
      </div>

      {!config && <p className="text-gray-500">No strategy configured.</p>}

      {config && (
        <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 space-y-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            {config.name || 'NIFTY 9:45 CE Strategy'}
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {!editing ? (
              Object.entries({
                'Lot Quantity': config.lot_qty,
                'Budget': `₹${config.budget?.toLocaleString()}`,
                'Entry Min': `₹${config.entry_price_min}`,
                'Entry Max': `₹${config.entry_price_max}`,
                'SL Points': `${config.sl_points} pts`,
                'Open': config.market_open,
                'Close': config.market_close,
                'TSL Levels': config.tsl_levels?.map(l => `+${l.trigger}→+${l.sl_offset}`).join(', '),
              }).map(([label, value]) => (
                <div key={label} className="bg-gray-50 rounded-xl p-4">
                  <p className="text-sm text-gray-500">{label}</p>
                  <p className="text-lg font-bold text-gray-800 mt-1">{value}</p>
                </div>
              ))
            ) : (
              <>
                <InputField label="Lot Quantity" type="number"
                  value={form.lot_qty} onChange={e => setForm({...form, lot_qty: parseInt(e.target.value)})} />
                <InputField label="Budget (₹)" type="number"
                  value={form.budget} onChange={e => setForm({...form, budget: parseInt(e.target.value)})} />
                <InputField label="Entry Price Min" type="number"
                  value={form.entry_price_min} onChange={e => setForm({...form, entry_price_min: parseInt(e.target.value)})} />
                <InputField label="Entry Price Max" type="number"
                  value={form.entry_price_max} onChange={e => setForm({...form, entry_price_max: parseInt(e.target.value)})} />
                <InputField label="SL Points" type="number"
                  value={form.sl_points} onChange={e => setForm({...form, sl_points: parseInt(e.target.value)})} />
                <InputField label="Market Open" type="time"
                  value={form.market_open} onChange={e => setForm({...form, market_open: e.target.value})} />
                <InputField label="Market Close" type="time"
                  value={form.market_close} onChange={e => setForm({...form, market_close: e.target.value})} />

                <div className="md:col-span-3">
                  <p className="text-sm text-gray-500 mb-2">TSL Levels</p>
                  {form.tsl_levels?.map((level, i) => (
                    <div key={i} className="flex items-center gap-4 mb-2">
                      <span className="text-sm text-gray-600">Level {i + 1}:</span>
                      <input type="number" value={level.trigger}
                        onChange={e => {
                          const nl = [...form.tsl_levels]
                          nl[i].trigger = parseInt(e.target.value)
                          setForm({...form, tsl_levels: nl})
                        }}
                        className="w-24 px-3 py-2 border border-gray-200 rounded-lg" placeholder="+pts" />
                      <span className="text-sm">→ SL = Entry +</span>
                      <input type="number" value={level.sl_offset}
                        onChange={e => {
                          const nl = [...form.tsl_levels]
                          nl[i].sl_offset = parseInt(e.target.value)
                          setForm({...form, tsl_levels: nl})
                        }}
                        className="w-24 px-3 py-2 border border-gray-200 rounded-lg" placeholder="offset" />
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function InputField({ label, type, value, onChange }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <label className="block text-sm text-gray-500 mb-1">{label}</label>
      <input type={type} value={value || ''} onChange={onChange}
        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-300 outline-none" />
    </div>
  )
}