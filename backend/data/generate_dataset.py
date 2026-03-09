"""
BlockGuard - Synthetic Ethereum Transaction Dataset Generator
Generates realistic blockchain transactions with fraud patterns:
  - Normal transactions
  - Wash trading (circular fund movement)
  - Phishing (wallet draining)
  - Rug pull (large sudden withdrawal)
"""

import numpy as np
import pandas as pd
import hashlib
import random
import time
import json
from datetime import datetime, timedelta


def generate_eth_address():
    """Generate a realistic-looking Ethereum address."""
    raw = hashlib.sha256(str(random.random()).encode()).hexdigest()[:40]
    return f"0x{raw}"


def generate_tx_hash():
    """Generate a realistic transaction hash."""
    raw = hashlib.sha256(str(random.random()).encode() + str(time.time()).encode()).hexdigest()
    return f"0x{raw}"


def generate_normal_transactions(n=3000, addresses=None):
    """Generate normal, legitimate Ethereum transactions."""
    if addresses is None:
        addresses = [generate_eth_address() for _ in range(200)]

    transactions = []
    base_time = datetime(2024, 1, 1)

    for i in range(n):
        sender = random.choice(addresses)
        receiver = random.choice([a for a in addresses if a != sender])

        # Normal: moderate values, reasonable gas, varied timing
        value_eth = np.random.lognormal(mean=-1, sigma=1.5)
        value_eth = min(value_eth, 50)  # Cap at 50 ETH for normal
        gas_price_gwei = np.random.normal(30, 10)
        gas_price_gwei = max(5, gas_price_gwei)
        gas_used = random.randint(21000, 100000)

        tx_time = base_time + timedelta(
            days=random.randint(0, 365),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        transactions.append({
            "tx_hash": generate_tx_hash(),
            "block_number": 18000000 + i * random.randint(1, 5),
            "timestamp": tx_time.isoformat(),
            "from_address": sender,
            "to_address": receiver,
            "value_eth": round(value_eth, 6),
            "gas_price_gwei": round(gas_price_gwei, 2),
            "gas_used": gas_used,
            "tx_fee_eth": round((gas_price_gwei * gas_used) / 1e9, 8),
            "is_contract_interaction": random.random() < 0.3,
            "input_data_length": random.choice([0, 0, 0, 68, 136, 200]),
            "nonce": random.randint(0, 5000),
            "fraud_type": "normal",
            "is_fraud": 0
        })

    return transactions


def generate_wash_trading(n=400, addresses=None):
    """
    Wash Trading: Circular movement of LARGE funds between same addresses
    to fake volume. Pattern: A->B->A->B with VERY HIGH VALUES and EXTREME frequency.
    DISTINCT FEATURE: sender_frequency & receiver_frequency both 60+
    """
    transactions = []
    base_time = datetime(2024, 3, 1)

    # Create wash trading rings (groups of 2 addresses for circular trading)
    num_rings = n // 20

    for ring_idx in range(num_rings):
        # Only 2 addresses trading back and forth (DISTINCT!)
        ring_addresses = [generate_eth_address(), generate_eth_address()]
        # VERY HIGH base value to distinguish from phishing/rug pull
        base_value = np.random.uniform(80, 200)  # Much larger!

        ring_time = base_time + timedelta(days=random.randint(0, 200))

        for cycle in range(n // num_rings):
            sender = ring_addresses[cycle % 2]
            receiver = ring_addresses[(cycle + 1) % 2]

            # Wash trading: very similar values, quick succession, VERY high gas
            value_eth = base_value * np.random.uniform(0.99, 1.01)
            gas_price_gwei = np.random.normal(85, 20)  # VERY high gas
            gas_used = random.randint(100000, 180000)  # MUCH higher!

            tx_time = ring_time + timedelta(minutes=cycle)

            transactions.append({
                "tx_hash": generate_tx_hash(),
                "block_number": 18200000 + ring_idx * 200 + cycle,
                "timestamp": tx_time.isoformat(),
                "from_address": sender,
                "to_address": receiver,
                "value_eth": round(value_eth, 6),
                "gas_price_gwei": round(max(5, gas_price_gwei), 2),
                "gas_used": gas_used,
                "tx_fee_eth": round((gas_price_gwei * gas_used) / 1e9, 8),
                "is_contract_interaction": True,
                "input_data_length": 200,  # Complex data
                "nonce": random.randint(100, 500),  # Established accounts
                "fraud_type": "wash_trading",
                "is_fraud": 1
            })

    return transactions[:n]


def generate_phishing_transactions(n=400, addresses=None):
    """
    Phishing: DUST transactions from brand new wallets to suspicious addresses.
    Pattern: Attacker sends TINY amounts with VERY LOW nonce to drain wallets.
    DISTINCT FEATURES: value_eth < 0.01, nonce = 1-5, sender_frequency = 1
    """
    transactions = []
    base_time = datetime(2024, 5, 1)

    num_campaigns = n // 10

    for campaign in range(num_campaigns):
        attacker_wallets = [generate_eth_address() for _ in range(3)]
        drain_address = generate_eth_address()

        campaign_time = base_time + timedelta(days=random.randint(0, 180))

        for idx in range(n // num_campaigns):
            attacker = attacker_wallets[idx % 3]

            # PHISHING: Dust attack with EXTREME characteristics
            tx_time = campaign_time + timedelta(hours=idx)
            # VERY SMALL amount (DUST) - KEY FEATURE!
            dust_value = np.random.uniform(0.0001, 0.005)
            gas_price_gwei = np.random.normal(110, 25)  # VERY high gas for small amount
            gas_used = random.randint(35000, 60000)

            transactions.append({
                "tx_hash": generate_tx_hash(),
                "block_number": 18400000 + campaign * 100 + idx,
                "timestamp": tx_time.isoformat(),
                "from_address": attacker,
                "to_address": drain_address,
                "value_eth": round(dust_value, 6),  # DUST AMOUNT - DISTINCT!
                "gas_price_gwei": round(max(5, gas_price_gwei), 2),
                "gas_used": gas_used,
                "tx_fee_eth": round((gas_price_gwei * gas_used) / 1e9, 8),
                "is_contract_interaction": True,
                "input_data_length": random.choice([300, 332, 368]),  # Complex payload
                "nonce": random.randint(1, 5),  # VERY LOW NONCE - BRAND NEW WALLET - DISTINCT!
                "fraud_type": "phishing",
                "is_fraud": 1
            })

    return transactions[:n]


def generate_rug_pull_transactions(n=400, addresses=None):
    """
    Rug Pull: MASSIVE withdrawals from established addresses to brand new addresses.
    Pattern: Established account (high nonce) sends VERY LARGE amount to NEW address (nonce=1)
    DISTINCT FEATURES: value_eth > 200, sender established (nonce 500+), receiver brand new (nonce 1)
    """
    transactions = []
    base_time = datetime(2024, 7, 1)

    num_rugs = n // 20

    for rug_idx in range(num_rugs):
        # Established deployer (high nonce)
        deployer = generate_eth_address()
        # Brand new victim/withdrawal address (low nonce)
        victim = generate_eth_address()

        rug_time = base_time + timedelta(days=random.randint(0, 120))

        for tx_idx in range(n // num_rugs):
            # Deployer sends MASSIVE amount to new address (DISTINCT!)
            tx_time = rug_time + timedelta(hours=tx_idx)
            # VERY LARGE withdrawal amount - KEY FEATURE!
            withdrawal_value = np.random.uniform(200, 1000)
            gas_price_gwei = np.random.normal(60, 15)
            gas_used = random.randint(80000, 150000)

            transactions.append({
                "tx_hash": generate_tx_hash(),
                "block_number": 18600000 + rug_idx * 300 + tx_idx,
                "timestamp": tx_time.isoformat(),
                "from_address": deployer,
                "to_address": victim,
                "value_eth": round(withdrawal_value, 6),  # VERY LARGE - DISTINCT!
                "gas_price_gwei": round(max(5, gas_price_gwei), 2),
                "gas_used": gas_used,
                "tx_fee_eth": round((gas_price_gwei * gas_used) / 1e9, 8),
                "is_contract_interaction": True,
                "input_data_length": 68,
                "nonce": random.randint(500, 5000),  # ESTABLISHED ACCOUNT - DISTINCT!
                "fraud_type": "rug_pull",
                "is_fraud": 1
            })

    return transactions[:n]


def generate_full_dataset():
    """Generate the complete dataset with all fraud types."""
    print("[*] Generating normal transactions...")
    normal = generate_normal_transactions(3000)

    print("[*] Generating wash trading transactions...")
    wash = generate_wash_trading(400)

    print("[*] Generating phishing transactions...")
    phishing = generate_phishing_transactions(400)

    print("[*] Generating rug pull transactions...")
    rug_pull = generate_rug_pull_transactions(400)

    all_transactions = normal + wash + phishing + rug_pull
    random.shuffle(all_transactions)

    df = pd.DataFrame(all_transactions)

    print(f"\n[+] Dataset generated: {len(df)} transactions")
    print(f"    Normal:       {len(normal)}")
    print(f"    Wash Trading: {len(wash)}")
    print(f"    Phishing:     {len(phishing)}")
    print(f"    Rug Pull:     {len(rug_pull)}")
    print(f"    Fraud Rate:   {df['is_fraud'].mean()*100:.1f}%")

    return df


def save_dataset(df, path="dataset.csv"):
    """Save dataset to CSV."""
    df.to_csv(path, index=False)
    print(f"[+] Dataset saved to {path}")


if __name__ == "__main__":
    np.random.seed(42)
    random.seed(42)

    df = generate_full_dataset()
    save_dataset(df, "C:/Users/rohan/OneDrive/Desktop/CS project/BlockGuard/backend/data/dataset.csv")

    # Also save as JSON for MongoDB import
    records = df.to_dict(orient="records")
    with open("C:/Users/rohan/OneDrive/Desktop/CS project/BlockGuard/backend/data/dataset.json", "w") as f:
        json.dump(records, f, indent=2, default=str)
    print("[+] Dataset also saved as JSON")
