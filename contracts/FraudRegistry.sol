// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title FraudRegistry
 * @dev Immutable on-chain registry for flagged fraudulent transactions.
 *      Part of the BlockGuard decentralized fraud detection system.
 */
contract FraudRegistry {

    struct FraudReport {
        string txHash;           // Original transaction hash
        string fraudType;        // "wash_trading", "phishing", "rug_pull"
        uint256 riskScore;       // 0-100 risk score
        uint256 timestamp;       // Block timestamp when reported
        address reportedBy;      // Address that submitted the report
        string details;          // JSON string with additional details
    }

    // All fraud reports
    FraudReport[] public fraudReports;

    // Mapping from tx hash to report index (1-indexed, 0 means not found)
    mapping(string => uint256) public txHashToIndex;

    // Total reports count
    uint256 public totalReports;

    // Owner of the contract
    address public owner;

    // Events
    event FraudReported(
        uint256 indexed reportId,
        string txHash,
        string fraudType,
        uint256 riskScore,
        address reportedBy,
        uint256 timestamp
    );

    event AlertTriggered(
        uint256 indexed reportId,
        string txHash,
        string severity
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    constructor() {
        owner = msg.sender;
        totalReports = 0;
    }

    /**
     * @dev Report a fraudulent transaction
     * @param _txHash The hash of the fraudulent transaction
     * @param _fraudType Type of fraud detected
     * @param _riskScore Risk score from 0-100
     * @param _details JSON string with additional details
     */
    function reportFraud(
        string memory _txHash,
        string memory _fraudType,
        uint256 _riskScore,
        string memory _details
    ) public returns (uint256) {
        require(_riskScore <= 100, "Risk score must be 0-100");
        require(bytes(_txHash).length > 0, "TX hash cannot be empty");

        FraudReport memory report = FraudReport({
            txHash: _txHash,
            fraudType: _fraudType,
            riskScore: _riskScore,
            timestamp: block.timestamp,
            reportedBy: msg.sender,
            details: _details
        });

        fraudReports.push(report);
        totalReports++;

        uint256 reportId = fraudReports.length - 1;
        txHashToIndex[_txHash] = reportId + 1; // 1-indexed

        emit FraudReported(
            reportId,
            _txHash,
            _fraudType,
            _riskScore,
            msg.sender,
            block.timestamp
        );

        // Trigger alert for high-risk reports
        if (_riskScore > 80) {
            emit AlertTriggered(reportId, _txHash, "CRITICAL");
        } else if (_riskScore > 60) {
            emit AlertTriggered(reportId, _txHash, "HIGH");
        }

        return reportId;
    }

    /**
     * @dev Get a fraud report by ID
     */
    function getReport(uint256 _reportId) public view returns (
        string memory txHash,
        string memory fraudType,
        uint256 riskScore,
        uint256 timestamp,
        address reportedBy,
        string memory details
    ) {
        require(_reportId < fraudReports.length, "Report does not exist");
        FraudReport memory report = fraudReports[_reportId];
        return (
            report.txHash,
            report.fraudType,
            report.riskScore,
            report.timestamp,
            report.reportedBy,
            report.details
        );
    }

    /**
     * @dev Check if a transaction has been flagged
     */
    function isFlagged(string memory _txHash) public view returns (bool) {
        return txHashToIndex[_txHash] > 0;
    }

    /**
     * @dev Get total number of reports
     */
    function getReportCount() public view returns (uint256) {
        return totalReports;
    }

    /**
     * @dev Get reports within a range (for pagination)
     */
    function getReportsInRange(uint256 _start, uint256 _count) public view returns (
        string[] memory txHashes,
        string[] memory fraudTypes,
        uint256[] memory riskScores,
        uint256[] memory timestamps
    ) {
        require(_start < fraudReports.length, "Start index out of range");

        uint256 end = _start + _count;
        if (end > fraudReports.length) {
            end = fraudReports.length;
        }
        uint256 actualCount = end - _start;

        txHashes = new string[](actualCount);
        fraudTypes = new string[](actualCount);
        riskScores = new uint256[](actualCount);
        timestamps = new uint256[](actualCount);

        for (uint256 i = 0; i < actualCount; i++) {
            FraudReport memory report = fraudReports[_start + i];
            txHashes[i] = report.txHash;
            fraudTypes[i] = report.fraudType;
            riskScores[i] = report.riskScore;
            timestamps[i] = report.timestamp;
        }

        return (txHashes, fraudTypes, riskScores, timestamps);
    }
}
