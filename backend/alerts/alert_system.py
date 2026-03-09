"""
BlockGuard - Alert System
Manages fraud alerts, stores in MongoDB, and provides alert querying.
"""

import json
from datetime import datetime
from pymongo import MongoClient


class AlertSystem:
    """Manages fraud detection alerts."""

    SEVERITY_LEVELS = {
        "CRITICAL": {"min_risk": 0.8, "color": "#FF0000", "priority": 1},
        "HIGH":     {"min_risk": 0.6, "color": "#FF6600", "priority": 2},
        "MEDIUM":   {"min_risk": 0.4, "color": "#FFAA00", "priority": 3},
        "LOW":      {"min_risk": 0.2, "color": "#FFFF00", "priority": 4},
        "SAFE":     {"min_risk": 0.0, "color": "#00FF00", "priority": 5},
    }

    def __init__(self, mongo_uri="mongodb://localhost:27017", db_name="blockguard"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.alerts_collection = self.db["alerts"]
        self.transactions_collection = self.db["transactions"]

        # Create indexes
        self.alerts_collection.create_index("tx_hash")
        self.alerts_collection.create_index("severity")
        self.alerts_collection.create_index("created_at")
        self.transactions_collection.create_index("tx_hash")
        print("[+] Alert system initialized")

    def create_alert(self, tx_hash, prediction_result, transaction_data=None, blockchain_result=None):
        """Create a new fraud alert from ML prediction results."""
        severity = prediction_result.get("risk_level", "SAFE")

        alert = {
            "tx_hash": tx_hash,
            "severity": severity,
            "risk_score": prediction_result.get("combined_risk_score", 0),
            "fraud_probability": prediction_result.get("fraud_probability", 0),
            "anomaly_score": prediction_result.get("anomaly_score", 0),
            "fraud_type": prediction_result.get("fraud_type", "unknown"),
            "type_confidences": prediction_result.get("type_confidences", {}),
            "is_fraud": prediction_result.get("is_fraud", False),
            "is_anomaly": prediction_result.get("is_anomaly", False),
            "blockchain_logged": blockchain_result is not None,
            "blockchain_tx_hash": blockchain_result.get("blockchain_tx_hash") if blockchain_result else None,
            "blockchain_report_id": blockchain_result.get("report_id") if blockchain_result else None,
            "transaction_data": transaction_data,
            "created_at": datetime.utcnow().isoformat(),
            "status": "new",  # new, acknowledged, investigating, resolved
        }

        result = self.alerts_collection.insert_one(alert)
        alert["_id"] = str(result.inserted_id)

        return alert

    def store_transaction(self, transaction):
        """Store a transaction in MongoDB."""
        tx = transaction.copy()
        self.transactions_collection.update_one(
            {"tx_hash": tx.get("tx_hash")},
            {"$set": tx},
            upsert=True
        )

    def get_alerts(self, limit=50, severity=None, status=None):
        """Get recent alerts with optional filtering."""
        query = {}
        if severity:
            query["severity"] = severity
        if status:
            query["status"] = status

        alerts = list(
            self.alerts_collection.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

        for alert in alerts:
            alert["_id"] = str(alert["_id"])

        return alerts

    def get_alert_stats(self):
        """Get alert statistics."""
        pipeline = [
            {"$group": {
                "_id": "$severity",
                "count": {"$sum": 1},
                "avg_risk": {"$avg": "$risk_score"},
            }},
            {"$sort": {"count": -1}}
        ]
        severity_stats = list(self.alerts_collection.aggregate(pipeline))

        type_pipeline = [
            {"$group": {
                "_id": "$fraud_type",
                "count": {"$sum": 1},
                "avg_risk": {"$avg": "$risk_score"},
            }},
            {"$sort": {"count": -1}}
        ]
        type_stats = list(self.alerts_collection.aggregate(type_pipeline))

        total = self.alerts_collection.count_documents({})
        fraud_count = self.alerts_collection.count_documents({"is_fraud": True})

        return {
            "total_alerts": total,
            "fraud_detected": fraud_count,
            "fraud_rate": round(fraud_count / max(total, 1) * 100, 2),
            "by_severity": {s["_id"]: s for s in severity_stats},
            "by_type": {t["_id"]: t for t in type_stats},
        }

    def get_transactions(self, limit=100, fraud_only=False):
        """Get stored transactions."""
        query = {}
        if fraud_only:
            query["is_fraud"] = 1

        txs = list(
            self.transactions_collection.find(query)
            .sort("timestamp", -1)
            .limit(limit)
        )

        for tx in txs:
            tx["_id"] = str(tx["_id"])

        return txs

    def update_alert_status(self, tx_hash, status):
        """Update alert status."""
        self.alerts_collection.update_one(
            {"tx_hash": tx_hash},
            {"$set": {"status": status, "updated_at": datetime.utcnow().isoformat()}}
        )

    def bulk_store_transactions(self, transactions):
        """Bulk store transactions."""
        if not transactions:
            return
        from pymongo import UpdateOne
        operations = [
            UpdateOne(
                {"tx_hash": tx.get("tx_hash")},
                {"$set": tx},
                upsert=True
            )
            for tx in transactions
        ]
        self.transactions_collection.bulk_write(operations)
        print(f"[+] Stored {len(transactions)} transactions in MongoDB")
