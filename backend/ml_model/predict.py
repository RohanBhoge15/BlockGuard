"""
BlockGuard - Prediction Module
Loads trained models and predicts fraud on new transactions.
"""

import numpy as np
import pandas as pd
import pickle
import os


class FraudPredictor:
    """Loads trained models and provides fraud prediction."""

    def __init__(self, model_dir=None):
        if model_dir is None:
            model_dir = os.path.dirname(os.path.abspath(__file__))

        self.model_dir = model_dir
        self.rf_model = self._load("rf_model.pkl")
        self.iso_model = self._load("iso_model.pkl")
        self.type_model = self._load("type_model.pkl")
        self.scaler = self._load("scaler.pkl")
        self.label_encoder = self._load("label_encoder.pkl")
        self.feature_columns = self._load("feature_columns.pkl")

    def _load(self, filename):
        path = os.path.join(self.model_dir, filename)
        with open(path, "rb") as f:
            return pickle.load(f)

    def engineer_single_features(self, tx):
        """Engineer features for a single transaction dict."""
        ts = pd.to_datetime(tx.get('timestamp', '2024-06-15T12:00:00'))

        features = {
            'value_eth': tx.get('value_eth', 0),
            'gas_price_gwei': tx.get('gas_price_gwei', 30),
            'gas_used': tx.get('gas_used', 21000),
            'tx_fee_eth': tx.get('tx_fee_eth', 0.001),
            'hour': ts.hour,
            'day_of_week': ts.weekday(),
            'is_weekend': 1 if ts.weekday() >= 5 else 0,
            'log_value': np.log1p(tx.get('value_eth', 0)),
            'value_to_gas_ratio': tx.get('value_eth', 0) / (tx.get('gas_price_gwei', 30) + 1),
            'tx_fee_ratio': tx.get('tx_fee_eth', 0.001) / (tx.get('value_eth', 0) + 1e-10),
            'gas_efficiency': tx.get('gas_used', 21000) / (tx.get('gas_price_gwei', 30) + 1),
            'high_gas_flag': 1 if tx.get('gas_price_gwei', 30) > 60 else 0,
            'sender_frequency': tx.get('sender_frequency', 1),
            'receiver_frequency': tx.get('receiver_frequency', 1),
            'address_freq_ratio': tx.get('sender_frequency', 1) / (tx.get('receiver_frequency', 1) + 1),
            'is_contract_int': 1 if tx.get('is_contract_interaction', False) else 0,
            'has_input_data': 1 if tx.get('input_data_length', 0) > 0 else 0,
            'input_complexity': tx.get('input_data_length', 0) / 68,
            'low_nonce_flag': 1 if tx.get('nonce', 0) < 5 else 0,
            'log_nonce': np.log1p(tx.get('nonce', 0)),
            'is_dust': 1 if tx.get('value_eth', 0) < 0.01 else 0,
            'is_large': 1 if tx.get('value_eth', 0) > 10 else 0,
            'is_very_large': 1 if tx.get('value_eth', 0) > 50 else 0,
            'rapid_tx_flag': tx.get('rapid_tx_flag', 0),
            'nonce': tx.get('nonce', 0),
            'input_data_length': tx.get('input_data_length', 0),
        }

        return features

    def predict(self, transaction):
        """
        Predict fraud for a single transaction.
        Returns dict with prediction details.
        """
        features = self.engineer_single_features(transaction)

        # Create DataFrame with correct column order
        X = pd.DataFrame([features])[self.feature_columns].fillna(0)
        X_scaled = self.scaler.transform(X)

        # Random Forest prediction
        rf_pred = self.rf_model.predict(X_scaled)[0]
        rf_proba = self.rf_model.predict_proba(X_scaled)[0]

        # Isolation Forest anomaly score
        iso_score = self.iso_model.decision_function(X_scaled)[0]
        iso_pred = self.iso_model.predict(X_scaled)[0]
        is_anomaly = iso_pred == -1

        # Combined risk score (weighted average of Random Forest + Isolation Forest)
        fraud_probability = rf_proba[1]
        anomaly_normalized = max(0, min(1, 0.5 - iso_score))
        combined_risk = 0.7 * fraud_probability + 0.3 * anomaly_normalized

        # Risk level classification
        if combined_risk > 0.8:
            risk_level = "CRITICAL"
        elif combined_risk > 0.6:
            risk_level = "HIGH"
        elif combined_risk > 0.4:
            risk_level = "MEDIUM"
        elif combined_risk > 0.2:
            risk_level = "LOW"
        else:
            risk_level = "SAFE"

        return {
            "is_fraud": bool(rf_pred == 1),
            "fraud_probability": round(float(fraud_probability), 4),
            "anomaly_score": round(float(iso_score), 4),
            "is_anomaly": bool(is_anomaly),
            "combined_risk_score": round(float(combined_risk), 4),
            "risk_level": risk_level,
            "features_used": features,
            "feature_importances": dict(zip(
                self.feature_columns,
                self.rf_model.feature_importances_.tolist()
            ))
        }

    def predict_batch(self, transactions):
        """Predict fraud for a list of transactions."""
        return [self.predict(tx) for tx in transactions]
