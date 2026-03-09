"""
BlockGuard - Flask Backend API
REST API connecting ML model, MongoDB, blockchain, and alert system.
"""

import os
import sys
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import pandas as pd

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml_model.predict import FraudPredictor
from alerts.alert_system import AlertSystem

app = Flask(__name__)
CORS(app)

# Initialize components
predictor = None
alert_system = None
blockchain_client = None


def init_components():
    """Initialize all system components."""
    global predictor, alert_system, blockchain_client

    print("[*] Initializing BlockGuard components...")

    # ML Model
    try:
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_model")
        predictor = FraudPredictor(model_dir)
        print("[+] ML Model loaded")
    except Exception as e:
        print(f"[!] ML Model failed to load: {e}")

    # Alert System (MongoDB)
    try:
        alert_system = AlertSystem()
        print("[+] Alert system connected")
    except Exception as e:
        print(f"[!] Alert system failed: {e}")

    # Blockchain Client
    try:
        from blockchain.deploy_contract import FraudRegistryClient
        blockchain_client = FraudRegistryClient()
        print("[+] Blockchain client connected")
    except Exception as e:
        print(f"[!] Blockchain client failed (Ganache may not be running): {e}")
        blockchain_client = None


# =================== API Routes ===================

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "components": {
            "ml_model": predictor is not None,
            "alert_system": alert_system is not None,
            "blockchain": blockchain_client is not None,
        },
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/api/predict", methods=["POST"])
def predict_fraud():
    """Predict fraud for a single transaction."""
    if not predictor:
        return jsonify({"error": "ML model not loaded"}), 503

    try:
        tx_data = request.json
        prediction = predictor.predict(tx_data)

        # Store transaction and create alert
        if alert_system:
            alert_system.store_transaction(tx_data)

            # Log to blockchain if fraud detected and blockchain is available
            blockchain_result = None
            if prediction["is_fraud"] and blockchain_client:
                try:
                    print(f"[*] Attempting to log fraud to blockchain: {tx_data.get('tx_hash')}")
                    blockchain_result = blockchain_client.report_fraud(
                        tx_data.get("tx_hash", "unknown"),
                        "FRAUD_DETECTED",
                        prediction["combined_risk_score"],
                        json.dumps({"risk_level": prediction["risk_level"]})
                    )
                    print(f"[+] Successfully logged to blockchain: {blockchain_result}")
                    prediction["blockchain_logged"] = True
                    prediction["blockchain_tx"] = blockchain_result
                except Exception as e:
                    print(f"[!] Blockchain logging failed: {str(e)}")
                    traceback.print_exc()
                    prediction["blockchain_logged"] = False
                    prediction["blockchain_error"] = str(e)

            alert = alert_system.create_alert(
                tx_data.get("tx_hash", "unknown"),
                prediction,
                tx_data,
                blockchain_result
            )
            prediction["alert_id"] = alert.get("_id")

        return jsonify(prediction)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/predict/batch", methods=["POST"])
def predict_batch():
    """Predict fraud for multiple transactions."""
    if not predictor:
        return jsonify({"error": "ML model not loaded"}), 503

    try:
        transactions = request.json.get("transactions", [])
        results = []

        for tx in transactions:
            prediction = predictor.predict(tx)
            if alert_system:
                alert_system.store_transaction(tx)
                alert_system.create_alert(
                    tx.get("tx_hash", "unknown"),
                    prediction,
                    tx
                )
            results.append({
                "tx_hash": tx.get("tx_hash"),
                "prediction": prediction
            })

        fraud_count = sum(1 for r in results if r["prediction"]["is_fraud"])

        return jsonify({
            "total": len(results),
            "fraud_detected": fraud_count,
            "results": results
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Get fraud alerts."""
    if not alert_system:
        return jsonify({"error": "Alert system not connected"}), 503

    limit = request.args.get("limit", 50, type=int)
    severity = request.args.get("severity")
    status = request.args.get("status")

    alerts = alert_system.get_alerts(limit, severity, status)
    return jsonify({"alerts": alerts, "count": len(alerts)})


@app.route("/api/alerts/stats", methods=["GET"])
def get_alert_stats():
    """Get alert statistics."""
    if not alert_system:
        return jsonify({"error": "Alert system not connected"}), 503

    stats = alert_system.get_alert_stats()
    return jsonify(stats)


@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """Get stored transactions."""
    if not alert_system:
        return jsonify({"error": "Alert system not connected"}), 503

    limit = request.args.get("limit", 100, type=int)
    fraud_only = request.args.get("fraud_only", "false").lower() == "true"

    txs = alert_system.get_transactions(limit, fraud_only)
    return jsonify({"transactions": txs, "count": len(txs)})


@app.route("/api/blockchain/status", methods=["GET"])
def blockchain_status():
    """Get blockchain connection status."""
    if not blockchain_client:
        return jsonify({
            "connected": False,
            "message": "Blockchain not connected. Ensure Ganache is running."
        })

    try:
        report_count = blockchain_client.get_report_count()
        return jsonify({
            "connected": True,
            "contract_address": blockchain_client.contract.address,
            "total_reports": report_count,
            "network": "Ganache Local",
            "chain_id": blockchain_client.w3.eth.chain_id,
        })
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)})


@app.route("/api/blockchain/report/<int:report_id>", methods=["GET"])
def get_blockchain_report(report_id):
    """Get a specific blockchain fraud report."""
    if not blockchain_client:
        return jsonify({"error": "Blockchain not connected"}), 503

    try:
        report = blockchain_client.get_report(report_id)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/ingest", methods=["POST"])
def ingest_dataset():
    """Ingest the synthetic dataset into MongoDB."""
    if not alert_system:
        return jsonify({"error": "Alert system not connected"}), 503

    try:
        data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "dataset.json"
        )

        with open(data_path, "r") as f:
            transactions = json.load(f)

        alert_system.bulk_store_transactions(transactions)

        return jsonify({
            "status": "success",
            "transactions_ingested": len(transactions)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan", methods=["POST"])
def scan_all():
    """Scan all stored transactions with ML model and generate alerts."""
    if not predictor or not alert_system:
        return jsonify({"error": "Components not ready"}), 503

    try:
        limit = request.json.get("limit", 100) if request.json else 100
        transactions = alert_system.get_transactions(limit=limit)

        results = {"total": 0, "fraud": 0, "alerts_created": 0}

        for tx in transactions:
            prediction = predictor.predict(tx)
            results["total"] += 1

            if prediction["is_fraud"]:
                results["fraud"] += 1

            alert = alert_system.create_alert(
                tx.get("tx_hash", "unknown"),
                prediction,
                tx
            )
            results["alerts_created"] += 1

        return jsonify(results)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_components()
    print("\n[+] BlockGuard API starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
