# BlockGuard - Decentralized Fraud Detection System

A decentralized fraud detection system for blockchain transactions using Machine Learning and smart contracts. Processes transactions through a binary fraud classifier, logs confirmed fraud to an immutable on-chain registry, and visualizes results across a React dashboard and Streamlit test suite.

---

## How It Works

```
[Synthetic Dataset Generator]
         │
         ▼
[MongoDB] ◄──────────────────── Data Storage (transactions + alerts)
         │
         ▼
[ML Engine]
  ├── Random Forest       ──► Binary fraud classification (fraud / not fraud)
  └── Isolation Forest    ──► Anomaly scoring
         │
         ├──► [FraudRegistry Smart Contract on Ganache] ── Immutable audit trail
         ├──► [Alert System] ── Severity-based alerts (CRITICAL / HIGH / MEDIUM / LOW / SAFE)
         └──► [React Dashboard] ── Live visualization
              [Streamlit Test Suite] ── Interactive demo + API testing
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | Python, Flask, Flask-CORS |
| ML Engine | scikit-learn (Random Forest + Isolation Forest) |
| Database | MongoDB 7.0 (Docker) |
| Blockchain | Solidity 0.8.19, Web3.py, Ganache (Docker) |
| Frontend | React 18, Recharts, Lucide, Axios |
| Test Suite | Streamlit, Plotly |
| Orchestration | Docker Compose |

---

## ML Model Performance

| Metric | Score |
|--------|-------|
| Accuracy | 100% |
| Precision | 100% |
| Recall | 100% |
| F1 Score | 100% |
| AUC-ROC | 1.00 |

**Training dataset:** 4,200 transactions (3,000 normal + 1,200 fraud), 28.6% fraud rate

**Why perfect scores?** The synthetic dataset uses **intentionally separated fraud patterns** (see [Fraud Patterns](#fraud-patterns) section):
- Wash Trading: 80–200 ETH, high frequency, 85+ Gwei
- Phishing: 0.0001–0.005 ETH dust, nonce 1–5, 110+ Gwei
- Rug Pull: 200–1000 ETH drain, nonce 500+ sender → nonce 1 receiver
- Normal: 0.1–50 ETH, established accounts, 25–40 Gwei

These non-overlapping patterns enable perfect classification. **Real-world fraud detection typically achieves 85-95% accuracy** due to overlapping transaction characteristics.

**Top features driving detection:**

| Feature | Importance |
|---------|------------|
| tx_fee_eth | 0.1657 |
| gas_price_gwei | 0.1267 |
| high_gas_flag | 0.1079 |
| log_value | 0.0844 |
| value_eth | 0.0757 |

---

## Fraud Patterns

The model is trained with distinct patterns per fraud class to ensure clear ML separation:

| Type | Key Signal | Value Range | Gas |
|------|-----------|-------------|-----|
| **Wash Trading** | High value + extreme frequency | 80–200 ETH | 85+ Gwei |
| **Phishing** | Dust amount + brand-new wallet | 0.0001–0.005 ETH | 110+ Gwei, nonce 1–5 |
| **Rug Pull** | Massive drain from established wallet | 200–1000 ETH | nonce 500+ sender, nonce 1 receiver |
| **Normal** | Moderate value, established accounts | 0.1–50 ETH | 25–40 Gwei |

Detection is **binary** (fraud / not fraud) — no fraud type label is returned in the prediction.

---

## Prerequisites

- **Docker Desktop** — for MongoDB and Ganache containers
- **Python 3.9+**
- **Node.js 16+ and npm**

---

## Setup (One-Time)

```bash
# 1. Start Docker containers (MongoDB + Ganache)
docker-compose up -d

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Generate synthetic dataset
python backend/data/generate_dataset.py

# 4. Train ML models
python backend/ml_model/train_model.py

# 5. Deploy smart contract to Ganache
python backend/blockchain/deploy_contract.py

# 6. Install React dependencies
cd frontend && npm install && cd ..
```

Or run the automated script:
```bash
setup.bat
```

---

## Running the Project

Open 3 terminals:

```bash
# Terminal 1 — Flask Backend
python backend/app.py

# Terminal 2 — React Dashboard
cd frontend && npm start

# Terminal 3 — Streamlit Test Suite
streamlit run test_suite.py
```

Or run:
```bash
run.bat
```

---

## Access

| Service | URL |
|---------|-----|
| Flask Backend API | http://localhost:5000 |
| React Dashboard | http://localhost:3000 |
| Streamlit Test Suite | http://localhost:8501 |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health status of all components |
| POST | `/api/predict` | Predict fraud for a single transaction |
| POST | `/api/predict/batch` | Batch prediction for multiple transactions |
| GET | `/api/alerts` | Retrieve fraud alerts (filter by severity/status) |
| GET | `/api/alerts/stats` | Aggregated alert statistics |
| GET | `/api/transactions` | Retrieve stored transactions |
| POST | `/api/ingest` | Ingest dataset CSV into MongoDB |
| POST | `/api/scan` | Scan all stored transactions with ML |
| GET | `/api/blockchain/status` | Smart contract + Ganache connection status |
| GET | `/api/blockchain/report/<id>` | Query a specific on-chain fraud report |

### Sample Prediction Request

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tx_hash": "0xabc123",
    "value_eth": 500.0,
    "gas_price_gwei": 60,
    "gas_used": 120000,
    "tx_fee_eth": 1.0,
    "nonce": 2000,
    "sender_frequency": 30,
    "receiver_frequency": 2,
    "is_contract_interaction": true,
    "input_data_length": 68,
    "rapid_tx_flag": 0
  }'
```

### Sample Prediction Response

```json
{
  "tx_hash": "0xabc123",
  "is_fraud": true,
  "fraud_probability": 0.98,
  "anomaly_score": -0.42,
  "combined_risk_score": 0.94,
  "risk_level": "CRITICAL",
  "alert_created": true,
  "blockchain_logged": true
}
```

---

## Smart Contract

**File:** `contracts/FraudRegistry.sol` (Solidity 0.8.19)
**Network:** Ganache local testnet (localhost:8545)

Every transaction classified as fraud is logged to the `FraudRegistry` contract with:
- Transaction hash
- Risk score
- Block timestamp
- Status: `FRAUD_DETECTED`

Events emitted:
- `FraudReported` — on every logged fraud
- `AlertTriggered` — when risk score exceeds 80

---

## Streamlit Test Suite

The test suite at http://localhost:8501 includes:

| Page | Description |
|------|-------------|
| **Dashboard** | Pre-built test cases (Normal, Fraud Case 1/2/3) with deterministic features |
| **API Testing** | Test all 9 endpoints with live responses |
| **ML Model** | Confusion matrix, ROC curve (AUC=1.0), feature importance chart |
| **Dataset Explorer** | Dataset composition, fraud characteristics, feature ranges |
| **Blockchain** | Live contract status, query on-chain fraud reports |
| **System Status** | Health check for ML, MongoDB, Blockchain, overall status |

---

## Project Structure

```
BlockGuard/
├── docker-compose.yml              # MongoDB + Ganache containers
├── requirements.txt                # Python dependencies
├── setup.bat                       # One-time setup script
├── run.bat                         # Start all services
├── test_suite.py                   # Streamlit interactive test suite
├── backend/
│   ├── app.py                      # Flask REST API + routing
│   ├── data/
│   │   ├── generate_dataset.py     # Synthetic transaction generator
│   │   ├── dataset.csv             # Generated dataset (4,200 rows)
│   │   └── dataset.json            # JSON format for MongoDB
│   ├── ml_model/
│   │   ├── train_model.py          # Model training pipeline
│   │   ├── predict.py              # Prediction module (binary fraud detection)
│   │   ├── rf_model.pkl            # Trained Random Forest
│   │   ├── iso_model.pkl           # Trained Isolation Forest
│   │   └── scaler.pkl              # Feature scaler
│   ├── blockchain/
│   │   ├── deploy_contract.py      # Contract deployment + Web3 client
│   │   ├── contract_abi.json       # Contract ABI
│   │   └── contract_config.json    # Deployed contract address
│   └── alerts/
│       └── alert_system.py         # Alert creation + MongoDB storage
├── contracts/
│   └── FraudRegistry.sol           # Solidity smart contract
└── frontend/
    ├── package.json
    └── src/
        ├── App.js                  # Main React dashboard
        ├── index.js
        └── index.css
```

---

## Alert Severity Levels

| Severity | Risk Score Threshold | Description |
|----------|----------------------|-------------|
| CRITICAL | > 90% | Immediate action required |
| HIGH | 70–90% | High confidence fraud |
| MEDIUM | 50–70% | Suspicious activity |
| LOW | 30–50% | Minor anomaly |
| SAFE | < 30% | Legitimate transaction |

---

## Key Design Decisions

- **Binary classification only** — Fraud type labels (wash trading, phishing, rug pull) are used only during training for distinct pattern learning. The live system returns `is_fraud: true/false` and a risk score, avoiding unreliable multi-class predictions.
- **Zero cost** — All tools are free and open-source. Runs entirely on local machine with no cloud services or gas fees.
- **Immutable audit trail** — Every detected fraud is permanently logged to a Ganache smart contract, demonstrating blockchain's value for tamper-proof records.
- **Deterministic test cases** — The Streamlit test suite uses fixed (non-random) transaction features that reliably trigger the correct fraud/safe classification every time.
