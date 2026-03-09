"""
BlockGuard - Smart Contract Deployment & Interaction
Deploys FraudRegistry to local Ganache and provides interaction methods.
"""

import json
import os
from web3 import Web3
from solcx import compile_standard, install_solc


def get_web3(ganache_url="http://127.0.0.1:8545"):
    """Connect to Ganache."""
    w3 = Web3(Web3.HTTPProvider(ganache_url))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Ganache at {ganache_url}")
    print(f"[+] Connected to Ganache. Chain ID: {w3.eth.chain_id}")
    return w3


def compile_contract():
    """Compile the FraudRegistry Solidity contract."""
    print("[*] Installing Solidity compiler...")
    install_solc("0.8.19")

    contract_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "contracts", "FraudRegistry.sol"
    )

    with open(contract_path, "r") as f:
        contract_source = f.read()

    print("[*] Compiling FraudRegistry.sol...")
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"FraudRegistry.sol": {"content": contract_source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
                }
            },
        },
        solc_version="0.8.19",
    )

    contract_data = compiled_sol["contracts"]["FraudRegistry.sol"]["FraudRegistry"]
    abi = contract_data["abi"]
    bytecode = contract_data["evm"]["bytecode"]["object"]

    # Save compiled ABI
    abi_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract_abi.json")
    with open(abi_path, "w") as f:
        json.dump(abi, f, indent=2)

    print("[+] Contract compiled successfully")
    return abi, bytecode


def deploy_contract(w3=None, ganache_url="http://127.0.0.1:8545"):
    """Deploy FraudRegistry to Ganache."""
    if w3 is None:
        w3 = get_web3(ganache_url)

    abi, bytecode = compile_contract()

    account = w3.eth.accounts[0]
    print(f"[*] Deploying from account: {account}")

    FraudRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx = FraudRegistry.constructor().build_transaction({
        "from": account,
        "nonce": w3.eth.get_transaction_count(account),
        "gas": 5000000,
        "gasPrice": w3.to_wei("20", "gwei"),
    })

    # Ganache doesn't need signing - send directly
    tx_hash = w3.eth.send_transaction({
        "from": account,
        "data": tx["data"],
        "gas": tx["gas"],
        "gasPrice": tx["gasPrice"],
    })

    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress

    print(f"[+] FraudRegistry deployed at: {contract_address}")
    print(f"    Transaction hash: {tx_hash.hex()}")
    print(f"    Gas used: {tx_receipt.gasUsed}")

    # Save contract address
    config = {
        "contract_address": contract_address,
        "deployer": account,
        "chain_id": w3.eth.chain_id,
        "ganache_url": ganache_url,
    }

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    return contract_address, abi


class FraudRegistryClient:
    """Client for interacting with the deployed FraudRegistry contract."""

    def __init__(self, ganache_url="http://127.0.0.1:8545", contract_address=None):
        self.w3 = get_web3(ganache_url)
        self.account = self.w3.eth.accounts[0]

        # Load ABI
        abi_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract_abi.json")
        with open(abi_path, "r") as f:
            self.abi = json.load(f)

        # Load contract address from config if not provided
        if contract_address is None:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contract_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                contract_address = config["contract_address"]
            else:
                raise ValueError("No contract address provided and no config found. Deploy first.")

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=self.abi
        )
        print(f"[+] FraudRegistry client initialized at {contract_address}")

    def report_fraud(self, tx_hash, fraud_type, risk_score, details=""):
        """Submit a fraud report to the blockchain."""
        risk_score_int = int(min(100, max(0, risk_score * 100)))

        tx = self.contract.functions.reportFraud(
            tx_hash, fraud_type, risk_score_int, details
        ).build_transaction({
            "from": self.account,
            "nonce": self.w3.eth.get_transaction_count(self.account),
            "gas": 500000,
            "gasPrice": self.w3.to_wei("20", "gwei"),
        })

        tx_hash_sent = self.w3.eth.send_transaction({
            "from": self.account,
            "to": self.contract.address,
            "data": tx["data"],
            "gas": tx["gas"],
            "gasPrice": tx["gasPrice"],
        })

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_sent)

        # Parse events
        fraud_events = self.contract.events.FraudReported().process_receipt(receipt)
        alert_events = self.contract.events.AlertTriggered().process_receipt(receipt)

        result = {
            "blockchain_tx_hash": tx_hash_sent.hex(),
            "gas_used": receipt.gasUsed,
            "block_number": receipt.blockNumber,
            "report_id": fraud_events[0]['args']['reportId'] if fraud_events else None,
            "alert_triggered": len(alert_events) > 0,
            "alert_severity": alert_events[0]['args']['severity'] if alert_events else None,
        }

        return result

    def is_flagged(self, tx_hash):
        """Check if a transaction hash is flagged on-chain."""
        return self.contract.functions.isFlagged(tx_hash).call()

    def get_report(self, report_id):
        """Get a fraud report by ID."""
        result = self.contract.functions.getReport(report_id).call()
        return {
            "tx_hash": result[0],
            "fraud_type": result[1],
            "risk_score": result[2],
            "timestamp": result[3],
            "reported_by": result[4],
            "details": result[5],
        }

    def get_report_count(self):
        """Get total number of fraud reports."""
        return self.contract.functions.getReportCount().call()


if __name__ == "__main__":
    # Deploy the contract
    w3 = get_web3()
    address, abi = deploy_contract(w3)
    print(f"\n[+] Contract ready at {address}")
