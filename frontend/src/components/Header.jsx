import { Link, useLocation } from 'react-router-dom'

export default function Header({ userId, onLogout, serverStatus }) {
  const location = useLocation()

  const navItems = [
    { path: '/app/dashboard', label: '📊 Dashboard' },
    { path: '/app/trades', label: '📋 Trade Log' },
    { path: '/app/strategy', label: '⚙️ Strategy' },
    { path: '/app/alerts', label: '🔔 Alerts' },
  ]

  const isActive = (path) => location.pathname === path

  return (
    <header className="bg-white shadow-md border-b border-gray-200 sticky top-0 z-10">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">

          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-primary-700 to-dhan-purple rounded-lg flex items-center justify-center text-white font-bold text-lg">
              AX
            </div>
            <div className="hidden sm:block">
              <h1 className="font-bold text-gray-800 text-lg">AlgoX</h1>
              <p className="text-xs text-gray-500">NIFTY 9:45 Strategy</p>
            </div>
          </div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                  isActive(item.path)
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-3">

            {/* Server status */}
            {serverStatus && (
              <span className={`hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                serverStatus.status === 'ok'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-red-100 text-red-700'
              }`}>
                <span className={`w-2 h-2 rounded-full ${
                  serverStatus.status === 'ok' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}></span>
                Server: {serverStatus.status === 'ok' ? 'Online' : 'Offline'}
              </span>
            )}

            {/* User ID badge */}
            <span className="hidden sm:inline-block px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-mono">
              {userId || 'guest'}
            </span>

            {/* Mobile menu button */}
            <details className="md:hidden">
              <summary className="cursor-pointer p-2 text-gray-600 hover:bg-gray-100 rounded-xl">
                ☰
              </summary>
              <div className="absolute top-16 right-4 bg-white shadow-lg rounded-xl py-2 min-w-[180px] border">
                {navItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`block px-4 py-2 text-sm hover:bg-gray-100 ${
                      isActive(item.path) ? 'text-primary-700 bg-primary-50' : 'text-gray-700'
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
                <button
                  onClick={onLogout}
                  className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  🚪 Logout
                </button>
              </div>
            </details>

            {/* Desktop logout */}
            <button
              onClick={onLogout}
              className="hidden md:flex items-center gap-1 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition"
              title="Logout"
            >
              🚪
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}