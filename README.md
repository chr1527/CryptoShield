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
---

## 📂 Project Structure

```text
CryptoShield/
│
├── data/
│   ├── alerts.csv
│   ├── transactions.csv
│   ├── wallets.csv
│   ├── customers.csv
│   └── sanctions_watchlist.csv
│
├── tools.py
├── investigation.py
├── agent.py
├── app.py
├── requirements.txt
└── README.md
```

### Core Components

- **`tools.py`**  
  Contains deterministic investigation tools for retrieving transaction data,
  tracing wallet relationships, detecting suspicious transaction patterns,
  checking wallet risk and sanctions exposure, comparing customer behaviour,
  and calculating the final explainable risk score.

- **`investigation.py`**  
  Orchestrates the end-to-end investigation workflow. It starts from an existing
  AML alert, gathers structured evidence from the available tools, and combines
  the results into a complete investigation record.

- **`agent.py`**  
  Converts the structured investigation results into an evidence-grounded,
  human-readable investigation summary. The AI layer does not independently
  calculate or modify the risk score, sanctions result, or deterministic findings.

- **`app.py`**  
  Provides the interactive Streamlit interface used to demonstrate the three
  investigation cases.

- **`data/`**  
  Contains the five synthetic datasets used by the prototype.

---

## 📊 Prototype Data

The working prototype uses five synthetic datasets:

| Dataset | Purpose |
|---|---|
| `alerts.csv` | Incoming AML alerts and alert-trigger information |
| `transactions.csv` | Cryptocurrency transaction flows |
| `wallets.csv` | Wallet metadata, attribution, and risk indicators |
| `customers.csv` | Customer KYC profiles and expected transaction behaviour |
| `sanctions_watchlist.csv` | Sanctions and watchlist information |

### Why Synthetic Data?

Synthetic data is used in the prototype to:

- create controlled and reproducible investigation scenarios
- avoid exposing real customer or KYC information
- ensure that each demonstration case contains the intended AML risk patterns
- remove dependency on third-party API availability during the live demonstration

In a production environment, these data sources could be replaced or supplemented
by live blockchain APIs, wallet-intelligence providers, sanctions databases,
and internal financial-institution systems.

---

## 📈 Explainable Risk Scoring

CryptoShield does **not** ask the language model to decide how risky a transaction is.

Instead, the prototype uses a deterministic weighted scoring engine based on
observable investigation findings.

### Example Risk Indicators

| Risk Indicator | Weight |
|---|---:|
| Direct sanctions match | +45 |
| Indirect sanctions exposure | +30 |
| Mixer exposure | +25 |
| Direct scam-wallet exposure | +25 |
| Indirect scam-wallet exposure | +15 |
| Transaction splitting / structuring | +15 |
| Rapid movement of funds | +10 |
| High customer-behaviour mismatch | +10 |
| Cluster of newly created wallets | +5 |
| Multi-hop transaction path | +5 |
| Branching / consolidation network | +5 |

Additional adjustments may also be applied based on wallet-risk labels and
customer KYC risk ratings.

### Risk Levels

```text
0–24      Low
25–49     Medium
50–74     High
75–100    Critical
```

The final score is capped at 100.

> **The LLM explains the result but does not calculate or override the risk score.**

---

## 🤖 Role of AI in the Prototype

The prototype separates factual analysis from language generation.

```text
Structured Transaction & Customer Data
                ↓
      Deterministic Investigation Tools
                ↓
        Structured Evidence
                ↓
      Deterministic Risk Score
                ↓
       AI Investigation Summary
                ↓
       Human Compliance Review
```

The AI summary layer is designed to:

- use only evidence returned by the investigation workflow
- explain the main risk indicators in concise language
- distinguish between direct, indirect, and no detected exposure
- prepare a readable investigation summary for a compliance reviewer

The AI is **not allowed to**:

- invent missing transactions or customer information
- modify the deterministic risk score
- override sanctions or wallet-risk findings
- accuse a customer of money laundering
- make the final compliance decision

If the OpenAI API is unavailable or no API key is configured, the application
can fall back to a deterministic summary template so that the demonstration
remains usable.

---

## 🧪 Demonstration Cases

The prototype includes three investigation scenarios designed to demonstrate
different AML outcomes.

### Case 1 — Normal Customer Activity

A long-standing customer makes a deposit that is slightly above their normal
transaction range.

The investigation finds:

- a long-standing customer wallet
- stable historical behaviour
- no suspicious wallet-hopping pattern
- no scam exposure
- no sanctions exposure

**Purpose:** Demonstrate that an AML alert does not automatically result in a
high-risk assessment.

**Expected outcome:** Low risk and potential false-positive clearance after
human review.

---

### Case 2 — Suspicious Exchange Deposit

A customer deposits funds that have moved rapidly through several recently
created wallets.

The investigation identifies:

- newly created wallets
- transaction splitting / structuring
- rapid movement of funds
- multiple wallet hops
- indirect scam exposure
- customer-behaviour mismatch

**Purpose:** Demonstrate how multiple pieces of evidence can be combined into
an explainable high-risk assessment.

**Expected outcome:** Escalation for enhanced human compliance review.

---

### Case 3 — Complex Wallet Network

A customer's deposit traces back through a deeper, branching transaction network
that includes mixer exposure and an indirect sanctions connection.

The investigation identifies:

- multi-hop transaction paths
- branching wallet relationships
- newly created wallets
- mixer exposure
- indirect sanctions exposure several hops upstream

**Purpose:** Demonstrate how CryptoShield surfaces complex transaction
relationships without making an automatic enforcement decision.

**Expected outcome:** Critical-risk escalation for senior compliance review.

---

## 👤 Human-in-the-Loop

CryptoShield is designed as a **compliance investigation co-pilot**, not an
autonomous compliance decision-maker.

The system can:

- collect and organise evidence
- identify suspicious transaction patterns
- calculate an explainable risk score
- generate an investigation summary
- recommend a next investigation step

The final decision remains with a **human compliance officer**.

The prototype does not independently:

- freeze customer funds
- terminate customer accounts
- accuse customers of money laundering
- file a SAR / STR
- make final regulatory or enforcement decisions

---

## 🛠️ Technology Stack

- **Python**
- **Streamlit**
- **OpenAI API** for optional evidence-grounded summaries
- **CSV-based synthetic datasets**
- **Deterministic rule-based analysis and risk scoring**

---

## ⚠️ Prototype Limitations

The current implementation is an educational proof of concept rather than a
production AML platform.

The prototype currently uses:

- synthetic blockchain and customer data
- a simplified single investigation workflow
- deterministic Python tools
- predefined demonstration scenarios

It does not currently include:

- production-grade blockchain intelligence APIs
- real financial-institution KYC systems
- real-time wallet screening infrastructure
- full cross-chain transaction tracing
- regulatory-policy RAG
- autonomous multi-agent task delegation
- production case-management infrastructure
- automatic regulatory reporting

---

## 🚀 Future Development

The conceptual architecture can be extended by replacing or expanding individual
prototype components.

Potential future developments include:

- live blockchain API integration
- commercial wallet-intelligence and attribution services
- real-time sanctions and watchlist screening
- interactive transaction-network visualisation
- cross-chain fund tracing
- regulatory-policy retrieval using RAG
- specialised Blockchain Analysis and Risk & Compliance agents
- dynamic task delegation between agents
- case-management and audit-trail integration

The current prototype therefore demonstrates the **core investigation logic**
while leaving the architecture modular enough for future expansion.
