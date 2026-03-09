"""
BlockGuard - ML Fraud Detection Engine
Trains Random Forest + Isolation Forest models on transaction features.
"""

import numpy as np
import pandas as pd
import pickle
import os
import sys
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def engineer_features(df):
    """
    Extract meaningful features from raw transaction data.
    These features capture behavioral patterns indicative of fraud.
    """
    df = df.copy()

    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    # Value features
    df['log_value'] = np.log1p(df['value_eth'])
    df['value_to_gas_ratio'] = df['value_eth'] / (df['gas_price_gwei'] + 1)
    df['tx_fee_ratio'] = df['tx_fee_eth'] / (df['value_eth'] + 1e-10)

    # Gas features
    df['gas_efficiency'] = df['gas_used'] / (df['gas_price_gwei'] + 1)
    df['high_gas_flag'] = (df['gas_price_gwei'] > 60).astype(int)

    # Address frequency features (how often each address appears as sender/receiver)
    sender_counts = df['from_address'].value_counts().to_dict()
    receiver_counts = df['to_address'].value_counts().to_dict()
    df['sender_frequency'] = df['from_address'].map(sender_counts)
    df['receiver_frequency'] = df['to_address'].map(receiver_counts)
    df['address_freq_ratio'] = df['sender_frequency'] / (df['receiver_frequency'] + 1)

    # Contract interaction features
    df['is_contract_int'] = df['is_contract_interaction'].astype(int)
    df['has_input_data'] = (df['input_data_length'] > 0).astype(int)
    df['input_complexity'] = df['input_data_length'] / 68  # 68 bytes = 1 function sig + 1 param

    # Nonce features (low nonce = new wallet, suspicious)
    df['low_nonce_flag'] = (df['nonce'] < 5).astype(int)
    df['log_nonce'] = np.log1p(df['nonce'])

    # Value magnitude classification
    df['is_dust'] = (df['value_eth'] < 0.01).astype(int)
    df['is_large'] = (df['value_eth'] > 10).astype(int)
    df['is_very_large'] = (df['value_eth'] > 50).astype(int)

    # Time-based clustering (transactions happening in bursts)
    df = df.sort_values('timestamp')
    df['time_diff_seconds'] = df['timestamp'].diff().dt.total_seconds().fillna(9999)
    df['rapid_tx_flag'] = (df['time_diff_seconds'] < 120).astype(int)

    return df


def get_feature_columns():
    """Return the list of feature columns used for training."""
    return [
        'value_eth', 'gas_price_gwei', 'gas_used', 'tx_fee_eth',
        'hour', 'day_of_week', 'is_weekend',
        'log_value', 'value_to_gas_ratio', 'tx_fee_ratio',
        'gas_efficiency', 'high_gas_flag',
        'sender_frequency', 'receiver_frequency', 'address_freq_ratio',
        'is_contract_int', 'has_input_data', 'input_complexity',
        'low_nonce_flag', 'log_nonce',
        'is_dust', 'is_large', 'is_very_large',
        'rapid_tx_flag', 'nonce', 'input_data_length'
    ]


def train_models(data_path=None):
    """Train both Random Forest (classification) and Isolation Forest (anomaly detection)."""
    if data_path is None:
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "data", "dataset.csv")

    print("[*] Loading dataset...")
    df = pd.read_csv(data_path)
    print(f"    Total records: {len(df)}")
    print(f"    Fraud records: {df['is_fraud'].sum()}")

    print("\n[*] Engineering features...")
    df = engineer_features(df)

    feature_cols = get_feature_columns()
    X = df[feature_cols].fillna(0)
    y = df['is_fraud']

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    # === Random Forest Classifier ===
    print("\n[*] Training Random Forest Classifier...")
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)

    y_pred_rf = rf_model.predict(X_test)
    y_proba_rf = rf_model.predict_proba(X_test)[:, 1]

    print("\n=== Random Forest Results ===")
    print(classification_report(y_test, y_pred_rf, target_names=['Normal', 'Fraud']))
    print(f"ROC AUC Score: {roc_auc_score(y_test, y_proba_rf):.4f}")
    print(f"Confusion Matrix:\n{confusion_matrix(y_test, y_pred_rf)}")

    # Feature importance
    importances = pd.Series(rf_model.feature_importances_, index=feature_cols)
    importances = importances.sort_values(ascending=False)
    print("\n=== Top 10 Feature Importances ===")
    for feat, imp in importances.head(10).items():
        print(f"  {feat:30s}: {imp:.4f}")

    # === Isolation Forest (Anomaly Detection) ===
    print("\n[*] Training Isolation Forest...")
    iso_model = IsolationForest(
        n_estimators=200,
        contamination=0.15,
        max_features=0.8,
        random_state=42,
        n_jobs=-1
    )
    iso_model.fit(X_scaled)

    anomaly_scores = iso_model.decision_function(X_test)
    anomaly_preds = iso_model.predict(X_test)
    anomaly_preds = (anomaly_preds == -1).astype(int)  # -1 = anomaly

    print("\n=== Isolation Forest Results ===")
    print(classification_report(y_test, anomaly_preds, target_names=['Normal', 'Anomaly']))

    # === Fraud Type Classifier (Multi-class) ===
    print("\n[*] Training Fraud Type Classifier...")
    le = LabelEncoder()
    df['fraud_label'] = le.fit_transform(df['fraud_type'])

    X_full = df[feature_cols].fillna(0)
    X_full_scaled = scaler.transform(X_full)
    y_type = df['fraud_label']

    X_train_t, X_test_t, y_train_t, y_test_t = train_test_split(
        X_full_scaled, y_type, test_size=0.2, random_state=42, stratify=y_type
    )

    type_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    type_model.fit(X_train_t, y_train_t)

    y_pred_type = type_model.predict(X_test_t)
    print("\n=== Fraud Type Classification Results ===")
    print(classification_report(y_test_t, y_pred_type, target_names=le.classes_))

    # === Save models ===
    model_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(model_dir, "rf_model.pkl"), "wb") as f:
        pickle.dump(rf_model, f)

    with open(os.path.join(model_dir, "iso_model.pkl"), "wb") as f:
        pickle.dump(iso_model, f)

    with open(os.path.join(model_dir, "type_model.pkl"), "wb") as f:
        pickle.dump(type_model, f)

    with open(os.path.join(model_dir, "scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    with open(os.path.join(model_dir, "label_encoder.pkl"), "wb") as f:
        pickle.dump(le, f)

    with open(os.path.join(model_dir, "feature_columns.pkl"), "wb") as f:
        pickle.dump(feature_cols, f)

    print(f"\n[+] All models saved to {model_dir}")
    print("[+] Training complete!")

    return {
        "rf_model": rf_model,
        "iso_model": iso_model,
        "type_model": type_model,
        "scaler": scaler,
        "label_encoder": le,
        "feature_columns": feature_cols,
        "rf_accuracy": roc_auc_score(y_test, y_proba_rf),
        "feature_importances": importances.to_dict()
    }


if __name__ == "__main__":
    train_models()
