# AlgoX – Multi-User Algo Trading Web App (NIFTY 9:45 Strategy)

> A production-ready, multi-user algo trading platform that automatically buys
> ATM NIFTY CE options at **9:45 AM IST** and exits at **3:30 PM** or on SL/TSL.

## 🚀 Features

| Feature | Description |
|---------|-------------|
| **Multi-User** | Up to 100 traders login with their own Dhan Client ID & Token |
| **NIFTY 9:45 Strategy** | Auto-buy ATM NIFTY CE @ 9:45 AM, auto-exit @ 3:30 PM |
| **Demo Mode** | Paper trading with virtual ₹10,000 capital |
| **ON/OFF Switch** | Toggle algo activation per user |
| **Stop Loss** | Fixed SL = Entry − 20 points |
| **Trailing SL** | TSL Level 1: +20 → SL = Entry+10 · TSL Level 2: +40 → SL = Entry+30 |
| **Trade Log** | Per-user trade history with P&L (date \| strike \| entry \| exit \| P&L) |
| **Real-time** | Live LTP via Dhan MarketFeed API |
| **Mobile-First** | React + Tailwind, fully responsive |

## 📋 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Tailwind CSS (Vite) |
| Backend | Python Flask |
| Database | MongoDB (pymongo) |
| Broker API | DhanHQ v2 REST API |
| Scheduler | APScheduler (IST timezone) |

## 📦 Project Structure

```
AlgoX/
├── app.py                 # Flask backend – all API routes
├── config.py              # Strategy + app configuration
├── dhan_client.py         # DhanHQ v2 REST API wrapper
├── trading_engine.py      # Core strategy engine (entry, SL, TSL, exit)
├── models.py              # MongoDB models & helpers
├── requirements.txt       # Python dependencies
├── wsgi.py                # Production WSGI entry point
├── .env.example           # Environment variables template
├── templates/
│   └── index.html         # Fallback landing page
└── frontend/              # React SPA
    ├── index.html         # Vite root HTML
    ├── vite.config.js     # Vite + proxy config
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        ├── services/api.js
        └── components/
            ├── LoginPage.jsx
            ├── Header.jsx
            ├── Dashboard.jsx
            ├── TradeHistory.jsx
            ├── StrategyConfig.jsx
            └── AlertLog.jsx
```

## 🔧 Setup

### 1. Install Backend Dependencies

```bash
cd AlgoX
pip install -r requirements.txt
```

### 2. Install MongoDB (required)

```bash
# macOS
brew install mongodb-community

# Ubuntu
sudo apt install mongodb

# Start MongoDB
mongod
```

### 3. Start Backend Server (port 3000)

```bash
python app.py
```

### 4. Setup & Run Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### 5. Build for Production (Flask serves React)

```bash
cd frontend
npm run build    # outputs to frontend/build/
cd ..
python app.py     # Flask serves React at http://localhost:3000/app
```

## 🔑 Getting Dhan API Credentials

1. Sign up at [Dhan.co](https://dhan.co)
2. Go to **Dhan Connect** → **API** → **My Apps**
3. Create a new app and get your **Client ID**
4. Generate an **Access Token** from the Dhan web/mobile app

## 🎮 Usage

1. Go to `http://localhost:3000/app` or `http://localhost:5173`
2. Enter your **Dhan Client ID** and **Access Token**
3. Toggle **Demo Mode** ON for paper trading (₹10,000 virtual capital)
4. Switch **Algo** to **ON**
5. At 9:45 AM IST the algo will automatically buy ATM NIFTY CE
6. Monitor via **Dashboard** → **Trade Log** → **Alerts**

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Server health check |
| `POST` | `/api/login` | Login with Dhan credentials |
| `GET`  | `/api/dashboard/:user_id` | Dashboard data (capital, P&L, current trade) |
| `GET`  | `/api/refresh/:user_id` | Force-refresh capital & holdings |
| `GET`  | `/api/holdings/:user_id` | User holdings |
| `GET`  | `/api/positions/:user_id` | Open positions |
| `GET`  | `/api/optionchain/:user_id` | NIFTY option chain |
| `GET`  | `/api/optionchain/nearest-ce/:user_id` | Nearest ATM CE (price 100-140) |
| `POST` | `/api/orders/place` | Place manual order |
| `GET`  | `/api/orders/:user_id` | Order list |
| `POST` | `/api/strategy/toggle` | Toggle algo ON/OFF |
| `POST` | `/api/demo/toggle` | Toggle demo/paper mode |
| `POST` | `/api/strategy/entry` | Manual entry trigger |
| `POST` | `/api/strategy/exit` | Manual exit |
| `GET`  | `/api/position/:user_id` | Current open position |
| `GET`  | `/api/trade-history/:user_id` | Trade history |
| `GET`  | `/api/users` | All users (admin) |
| `GET`  | `/api/users/count` | User count |
| `GET`  | `/api/alerts` | System alerts |
| `GET`  | `/api/strategy/config` | Strategy config |
| `POST` | `/api/strategy/config` | Update strategy config |

## 🧪 Testing Without Dhan Credentials

The login form supports **Demo Mode** by default. Use placeholder credentials:
- Client ID: `demo`
- Token: `demo-token`
- Toggle Demo Mode ON

Market data endpoints will show mock data when real credentials aren't available.