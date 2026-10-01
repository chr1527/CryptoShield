# 🛡️ CryptoShield AI

**CryptoShield AI** is an AI-assisted AML investigation prototype for cryptocurrency transactions.

The system starts after an existing transaction-monitoring system generates an AML alert. It then retrieves transaction and customer information, analyses wallet relationships and suspicious patterns, calculates an explainable risk score, and generates an evidence-grounded investigation summary for a human compliance officer.

> This project is an educational proof of concept and uses synthetic data for demonstration purposes.

---

## 🔗 Live Demo

👉 [CryptoShield AI Streamlit Demo](https://cryptoshield-aapppsue6ai65j3jfnpn6qv.streamlit.app/)

---

## 🎯 Project Objective

Crypto AML investigations can require analysts to manually:

- trace transactions across multiple wallets
- identify suspicious transaction patterns
- check wallet attribution and risk indicators
- screen for scam or sanctions exposure
- compare transactions with customer KYC and historical behaviour
- assemble evidence into an investigation report

CryptoShield AI demonstrates how these steps can be combined into an explainable investigation workflow while keeping the final compliance decision with a human reviewer.

---

## 🧠 Conceptual Architecture

The full conceptual design uses a multi-agent architecture:

- **Investigation Agent**  
  Plans the investigation, coordinates specialised tasks, integrates evidence, and prepares the final summary.

- **Blockchain Analysis Agent**  
  Traces transactions, analyses wallet relationships, and detects suspicious on-chain patterns.

- **Risk & Compliance Agent**  
  Reviews customer context, sanctions exposure, behavioural anomalies, and compliance-related risk indicators.

For the working prototype, this architecture is simplified into a **single investigation workflow supported by specialised deterministic tools**.

This improves reliability and reproducibility while preserving the same separation of responsibilities.

---

## ⚙️ Prototype Workflow

```text
Transaction Monitoring Alert
            ↓
      Investigation Workflow
            ↓
 ┌─────────────────────────────┐
 │     Deterministic Tools     │
 │                             │
 │ • Transaction retrieval     │
 │ • Wallet tracing            │
 │ • Pattern detection         │
 │ • Wallet risk lookup        │
 │ • Sanctions screening       │
 │ • Customer/KYC retrieval    │
 │ • Behaviour comparison      │
 │ • Risk scoring              │
 └─────────────────────────────┘
            ↓
     Structured Evidence
            ↓
   Explainable Risk Score
            ↓
 AI Investigation Summary
            ↓
 Human Compliance Officer
