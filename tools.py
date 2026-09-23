"""Deterministic data tools for the CryptoShield classroom MVP.

The module uses only the Python standard library.  Every public function returns
plain dictionaries/lists, so its results can be displayed directly by
Streamlit or passed to a later agent layer.

By default CSV files are read from ``data/`` beside this file.  Set the
``CRYPTOSHIELD_DATA_DIR`` environment variable or pass ``data_dir=...`` to a
function when the files live elsewhere.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DATA_DIR = Path(
    os.getenv("CRYPTOSHIELD_DATA_DIR", Path(__file__).with_name("data"))
)

FILES = {
    "alerts": "alerts.csv",
    "customers": "customers.csv",
    "sanctions": "sanctions_watchlist.csv",
    "transactions": "transactions.csv",
    "wallets": "wallets.csv",
}

REQUIRED_COLUMNS = {
    "alerts": {
        "case_id", "customer_id", "transaction_id", "wallet_address",
        "chain", "amount", "asset", "timestamp", "alert_reason",
        "initial_risk_indicator", "initial_risk_label",
    },
    "customers": {
        "customer_id", "case_id", "account_open_date", "kyc_risk_rating",
        "expected_monthly_volume_usd", "typical_tx_min_usd",
        "typical_tx_max_usd", "primary_wallet",
    },
    "sanctions": {
        "watchlist_id", "wallet_address", "entity_name", "program",
        "risk_category", "is_sanctioned",
    },
    "transactions": {
        "transaction_id", "case_id", "timestamp", "chain", "asset",
        "from_wallet", "to_wallet", "amount", "usd_value",
        "transaction_type", "status",
    },
    "wallets": {
        "wallet_address", "case_id", "chain", "owner_customer_id",
        "entity_type", "wallet_age_days", "risk_label", "risk_score",
        "risk_tags", "kyc_verified",
    },
}

FLOAT_FIELDS = {
    "amount", "usd_value", "expected_monthly_volume_usd",
    "typical_tx_min_usd", "typical_tx_max_usd", "risk_score",
}
INT_FIELDS = {"wallet_age_days"}
BOOL_FIELDS = {"kyc_verified", "is_sanctioned"}


def _data_path(data_dir: str | Path | None) -> Path:
    return Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR


def _as_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _clean_row(row: dict[str, str]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, raw_value in row.items():
        value = raw_value.strip() if isinstance(raw_value, str) else raw_value
        if value == "":
            value = None
        if key in FLOAT_FIELDS and value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = None
        elif key in INT_FIELDS and value is not None:
            try:
                value = int(float(value))
            except (TypeError, ValueError):
                value = None
        elif key in BOOL_FIELDS:
            value = _as_bool(value)
        clean[key] = value
    return clean


@lru_cache(maxsize=32)
def _read_csv_cached(path_text: str) -> tuple[dict[str, Any], ...]:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"Required CryptoShield data file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(_clean_row(row) for row in csv.DictReader(handle))


def _rows(name: str, data_dir: str | Path | None = None) -> list[dict[str, Any]]:
    path = (_data_path(data_dir) / FILES[name]).resolve()
    return [dict(row) for row in _read_csv_cached(str(path))]


def _first(rows: Iterable[dict[str, Any]], key: str, value: Any) -> dict[str, Any] | None:
    wanted = str(value).casefold()
    return next(
        (row for row in rows if str(row.get(key) or "").casefold() == wanted),
        None,
    )


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def validate_data(data_dir: str | Path | None = None) -> dict[str, Any]:
    """Validate schemas, unique IDs and relationships across all five CSVs."""
    errors: list[str] = []
    warnings: list[str] = []
    tables: dict[str, list[dict[str, Any]]] = {}
    schemas: dict[str, list[str]] = {}

    for name, filename in FILES.items():
        path = _data_path(data_dir) / filename
        if not path.exists():
            errors.append(f"Missing file: {filename}")
            tables[name] = []
            schemas[name] = []
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
        schemas[name] = columns
        missing = REQUIRED_COLUMNS[name] - set(columns)
        if missing:
            errors.append(f"{filename}: missing columns {sorted(missing)}")
        tables[name] = _rows(name, data_dir)

    unique_keys = {
        "alerts": "case_id", "customers": "customer_id",
        "transactions": "transaction_id", "wallets": "wallet_address",
        "sanctions": "watchlist_id",
    }
    for name, key in unique_keys.items():
        values = [row.get(key) for row in tables[name] if row.get(key)]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            errors.append(f"{FILES[name]}: duplicate {key} values {duplicates}")

    customer_ids = {row.get("customer_id") for row in tables["customers"]}
    transaction_ids = {row.get("transaction_id") for row in tables["transactions"]}
    wallet_addresses = {row.get("wallet_address") for row in tables["wallets"]}
    case_ids = {row.get("case_id") for row in tables["alerts"]}

    for alert in tables["alerts"]:
        case_id = alert.get("case_id")
        if alert.get("customer_id") not in customer_ids:
            errors.append(f"{case_id}: customer_id is not present in customers.csv")
        if alert.get("transaction_id") not in transaction_ids:
            errors.append(f"{case_id}: transaction_id is not present in transactions.csv")
        if alert.get("wallet_address") not in wallet_addresses:
            errors.append(f"{case_id}: wallet_address is not present in wallets.csv")

    transaction_wallets = {
        wallet
        for row in tables["transactions"]
        for wallet in (row.get("from_wallet"), row.get("to_wallet"))
        if wallet
    }
    unknown_wallets = sorted(transaction_wallets - wallet_addresses)
    if unknown_wallets:
        warnings.append(
            f"{len(unknown_wallets)} transaction wallet(s) have no metadata record: "
            + ", ".join(unknown_wallets)
        )

    for row in tables["customers"] + tables["transactions"] + tables["wallets"]:
        if row.get("case_id") and row["case_id"] not in case_ids:
            warnings.append(f"Unknown case_id {row['case_id']} referenced in a data row")

    for row in tables["sanctions"]:
        if row.get("wallet_address") not in wallet_addresses:
            warnings.append(
                f"Sanctions wallet {row.get('wallet_address')} has no wallets.csv metadata"
            )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "row_counts": {name: len(rows) for name, rows in tables.items()},
        "schemas": schemas,
    }


def get_alert(case_id: str, *, data_dir: str | Path | None = None) -> dict[str, Any] | None:
    """Return one alert by case ID, or ``None`` when it is not found."""
    if not case_id:
        return None
    return _first(_rows("alerts", data_dir), "case_id", case_id)


def get_transaction_history(
    wallet_address: str,
    *,
    direction: str = "both",
    case_id: str | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Return incoming/outgoing transactions and USD totals for a wallet."""
    direction = direction.lower()
    if direction not in {"both", "incoming", "outgoing"}:
        raise ValueError("direction must be 'both', 'incoming', or 'outgoing'")
    if not wallet_address:
        return {
            "wallet_address": wallet_address, "direction": direction,
            "transaction_count": 0, "total_incoming_usd": 0.0,
            "total_outgoing_usd": 0.0, "transactions": [],
        }

    address = wallet_address.casefold()
    matched = []
    for tx in _rows("transactions", data_dir):
        if case_id and str(tx.get("case_id") or "").casefold() != case_id.casefold():
            continue
        incoming = str(tx.get("to_wallet") or "").casefold() == address
        outgoing = str(tx.get("from_wallet") or "").casefold() == address
        if (direction == "both" and (incoming or outgoing)) or (
            direction == "incoming" and incoming
        ) or (direction == "outgoing" and outgoing):
            item = dict(tx)
            item["direction"] = "incoming" if incoming else "outgoing"
            matched.append(item)

    matched.sort(key=lambda row: row.get("timestamp") or "")
    incoming_total = sum(
        float(row.get("usd_value") or 0) for row in matched if row["direction"] == "incoming"
    )
    outgoing_total = sum(
        float(row.get("usd_value") or 0) for row in matched if row["direction"] == "outgoing"
    )
    return {
        "wallet_address": wallet_address,
        "direction": direction,
        "case_id": case_id,
        "transaction_count": len(matched),
        "total_incoming_usd": round(incoming_total, 2),
        "total_outgoing_usd": round(outgoing_total, 2),
        "transactions": matched,
    }


def get_customer_profile(
    customer_id: str, *, data_dir: str | Path | None = None
) -> dict[str, Any] | None:
    """Return a customer/KYC profile, or ``None`` when it is not found."""
    if not customer_id:
        return None
    return _first(_rows("customers", data_dir), "customer_id", customer_id)


def lookup_wallet_risk(
    wallet_address: str, *, data_dir: str | Path | None = None
) -> dict[str, Any]:
    """Return normalized wallet-risk metadata without failing on unknown wallets."""
    row = _first(_rows("wallets", data_dir), "wallet_address", wallet_address)
    if row is None:
        return {
            "found": False,
            "wallet_address": wallet_address,
            "risk_label": "Unknown",
            "risk_score": None,
            "risk_tags": [],
        }
    result = dict(row)
    result["found"] = True
    result["risk_tags_raw"] = result.get("risk_tags")
    result["risk_tags"] = [
        tag for tag in str(result.get("risk_tags") or "").split("|") if tag
    ]
    return result


def trace_transaction_network(
    wallet_address: str,
    max_hops: int = 3,
    *,
    direction: str = "both",
    case_id: str | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Breadth-first trace of upstream, downstream, or both transaction paths."""
    if not isinstance(max_hops, int) or not 0 <= max_hops <= 10:
        raise ValueError("max_hops must be an integer between 0 and 10")
    direction = direction.lower()
    if direction not in {"both", "upstream", "downstream"}:
        raise ValueError("direction must be 'both', 'upstream', or 'downstream'")
    if not wallet_address:
        return {
            "start_wallet": wallet_address, "max_hops": max_hops,
            "direction": direction, "connected_wallets": [], "nodes": [],
            "edges": [], "paths": {}, "max_depth_reached": 0,
        }

    transactions = [
        tx for tx in _rows("transactions", data_dir)
        if not case_id or str(tx.get("case_id") or "").casefold() == case_id.casefold()
    ]
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    canonical: dict[str, str] = {wallet_address.casefold(): wallet_address}
    for tx in transactions:
        source = str(tx.get("from_wallet") or "")
        target = str(tx.get("to_wallet") or "")
        if not source or not target:
            continue
        canonical[source.casefold()] = source
        canonical[target.casefold()] = target
        outgoing[source.casefold()].append(tx)
        incoming[target.casefold()].append(tx)

    start = wallet_address.casefold()
    distances = {start: 0}
    path_keys: dict[str, list[str]] = {start: [start]}
    queue = deque([start])
    edge_by_id: dict[str, dict[str, Any]] = {}

    while queue:
        current = queue.popleft()
        depth = distances[current]
        if depth >= max_hops:
            continue
        candidates: list[tuple[dict[str, Any], str, str]] = []
        if direction in {"both", "downstream"}:
            candidates.extend((tx, str(tx.get("to_wallet") or "").casefold(), "downstream") for tx in outgoing[current])
        if direction in {"both", "upstream"}:
            candidates.extend((tx, str(tx.get("from_wallet") or "").casefold(), "upstream") for tx in incoming[current])
        for tx, neighbor, trace_direction in candidates:
            if not neighbor:
                continue
            edge = dict(tx)
            edge["trace_direction"] = trace_direction
            edge_by_id[str(tx.get("transaction_id"))] = edge
            if neighbor not in distances:
                distances[neighbor] = depth + 1
                path_keys[neighbor] = path_keys[current] + [neighbor]
                queue.append(neighbor)

    nodes = []
    for key, hop in sorted(distances.items(), key=lambda item: (item[1], item[0])):
        address = canonical.get(key, key)
        metadata = lookup_wallet_risk(address, data_dir=data_dir)
        nodes.append({
            "wallet_address": address,
            "hop": hop,
            "entity_type": metadata.get("entity_type"),
            "entity_name": metadata.get("entity_name"),
            "risk_label": metadata.get("risk_label", "Unknown"),
            "risk_tags": metadata.get("risk_tags", []),
        })

    paths = {
        canonical.get(key, key): [canonical.get(part, part) for part in parts]
        for key, parts in path_keys.items()
    }
    connected = [node["wallet_address"] for node in nodes if node["hop"] > 0]
    return {
        "start_wallet": wallet_address,
        "case_id": case_id,
        "max_hops": max_hops,
        "direction": direction,
        "connected_wallets": connected,
        "nodes": nodes,
        "edges": sorted(edge_by_id.values(), key=lambda row: row.get("timestamp") or ""),
        "paths": paths,
        "max_depth_reached": max(distances.values(), default=0),
    }


def check_sanctions(
    wallet_address: str | Iterable[str],
    max_hops: int = 3,
    *,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Check direct and graph-reachable sanctions exposure for one or more wallets."""
    seeds = [wallet_address] if isinstance(wallet_address, str) else list(wallet_address)
    seeds = [seed for seed in seeds if seed]
    active = {
        str(row.get("wallet_address") or "").casefold(): row
        for row in _rows("sanctions", data_dir)
        if row.get("wallet_address") and row.get("is_sanctioned") is not False
    }
    matches: dict[str, dict[str, Any]] = {}

    for seed in seeds:
        network = trace_transaction_network(
            seed, max_hops=max_hops, direction="both", data_dir=data_dir
        )
        for node in network["nodes"]:
            address = node["wallet_address"]
            watchlist = active.get(address.casefold())
            if watchlist is None:
                continue
            distance = int(node["hop"])
            match = dict(watchlist)
            match.update({
                "seed_wallet": seed,
                "distance_hops": distance,
                "exposure_type": "direct" if distance == 0 else "indirect",
                "path": network["paths"].get(address, [seed, address]),
            })
            existing = matches.get(address.casefold())
            if existing is None or distance < existing["distance_hops"]:
                matches[address.casefold()] = match

    ordered = sorted(matches.values(), key=lambda item: item["distance_hops"])
    direct = [match for match in ordered if match["distance_hops"] == 0]
    indirect = [match for match in ordered if match["distance_hops"] > 0]
    return {
        "checked_wallets": seeds,
        "max_hops": max_hops,
        "is_match": bool(ordered),
        "direct_match": bool(direct),
        "indirect_match": bool(indirect),
        "nearest_distance_hops": ordered[0]["distance_hops"] if ordered else None,
        "matches": ordered,
    }


def analyze_transaction_patterns(
    wallet_address: str,
    *,
    case_id: str | None = None,
    max_hops: int = 3,
    rapid_window_minutes: int = 60,
    structuring_window_minutes: int = 120,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Detect simple, explainable patterns in the wallet's local transaction graph."""
    wallet_meta = lookup_wallet_risk(wallet_address, data_dir=data_dir)
    inferred_case = case_id or wallet_meta.get("case_id")
    network = trace_transaction_network(
        wallet_address, max_hops=max_hops, direction="both",
        case_id=inferred_case, data_dir=data_dir,
    )
    transactions = network["edges"]
    all_wallets = [network["start_wallet"], *network["connected_wallets"]]
    metadata = {address: lookup_wallet_risk(address, data_dir=data_dir) for address in all_wallets}

    by_destination: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming_by_wallet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    outgoing_by_wallet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tx in transactions:
        source = str(tx.get("from_wallet") or "")
        target = str(tx.get("to_wallet") or "")
        by_destination[target].append(tx)
        incoming_by_wallet[target].append(tx)
        outgoing_by_wallet[source].append(tx)

    rapid_events = []
    for address, inbound in incoming_by_wallet.items():
        for in_tx in inbound:
            in_time = _parse_time(in_tx.get("timestamp"))
            if in_time is None:
                continue
            for out_tx in outgoing_by_wallet.get(address, []):
                out_time = _parse_time(out_tx.get("timestamp"))
                if out_time is None:
                    continue
                minutes = (out_time - in_time).total_seconds() / 60
                if 0 <= minutes <= rapid_window_minutes:
                    rapid_events.append({
                        "wallet_address": address,
                        "incoming_transaction_id": in_tx.get("transaction_id"),
                        "outgoing_transaction_id": out_tx.get("transaction_id"),
                        "minutes_between": round(minutes, 1),
                    })

    structuring_events = []
    for destination, inflows in by_destination.items():
        ordered = sorted(
            (tx for tx in inflows if _parse_time(tx.get("timestamp"))),
            key=lambda tx: tx["timestamp"],
        )
        for start_index in range(len(ordered)):
            window = []
            start_time = _parse_time(ordered[start_index].get("timestamp"))
            for tx in ordered[start_index:]:
                tx_time = _parse_time(tx.get("timestamp"))
                if start_time and tx_time and (tx_time - start_time).total_seconds() / 60 <= structuring_window_minutes:
                    window.append(tx)
            values = [float(tx.get("usd_value") or 0) for tx in window]
            positive = [value for value in values if value > 0]
            similar = positive and min(positive) >= max(positive) * 0.8
            if len(window) >= 3 and similar:
                structuring_events.append({
                    "destination_wallet": destination,
                    "transaction_ids": [tx.get("transaction_id") for tx in window],
                    "transaction_count": len(window),
                    "total_usd": round(sum(values), 2),
                    "window_minutes": round(
                        (_parse_time(window[-1]["timestamp"]) - start_time).total_seconds() / 60, 1
                    ),
                })
                break

    new_wallets = [
        address for address, info in metadata.items()
        if info.get("wallet_age_days") is not None and info["wallet_age_days"] <= 30
    ]
    mixer_wallets = [
        address for address, info in metadata.items()
        if info.get("entity_type") == "mixer" or "KNOWN_MIXER" in info.get("risk_tags", [])
    ]
    scam_wallets = [
        address for address, info in metadata.items()
        if info.get("entity_type") == "scam_wallet" or "KNOWN_SCAM" in info.get("risk_tags", [])
    ]
    start_folded = wallet_address.casefold()
    scam_type = (
        "direct" if any(address.casefold() == start_folded for address in scam_wallets)
        else "indirect" if scam_wallets else "none"
    )
    incoming_counts = {wallet: len(items) for wallet, items in incoming_by_wallet.items()}
    outgoing_counts = {wallet: len(items) for wallet, items in outgoing_by_wallet.items()}
    branching_wallets = sorted({
        wallet for wallet in set(incoming_counts) | set(outgoing_counts)
        if incoming_counts.get(wallet, 0) >= 2 or outgoing_counts.get(wallet, 0) >= 2
    })

    return {
        "wallet_address": wallet_address,
        "case_id": inferred_case,
        "rapid_movement": bool(rapid_events),
        "rapid_movement_events": rapid_events,
        "structuring": bool(structuring_events),
        "structuring_events": structuring_events,
        "new_wallet_cluster": len(new_wallets) >= 2,
        "new_wallets": new_wallets,
        "multiple_hops": network["max_depth_reached"] >= 2,
        "max_hops_observed": network["max_depth_reached"],
        "branching_network": bool(branching_wallets),
        "branching_wallets": branching_wallets,
        "mixer_exposure": bool(mixer_wallets),
        "mixer_wallets": mixer_wallets,
        "scam_exposure": bool(scam_wallets),
        "scam_exposure_type": scam_type,
        "scam_wallets": scam_wallets,
        "transaction_count_analyzed": len(transactions),
    }


def compare_customer_behavior(
    customer_id: str,
    *,
    transaction_id: str | None = None,
    amount_usd: float | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Compare an alert/transaction value with the customer's stated KYC ranges."""
    profile = get_customer_profile(customer_id, data_dir=data_dir)
    if profile is None:
        return {
            "customer_id": customer_id, "profile_found": False,
            "behaviour_mismatch": None, "severity": "Unknown",
            "reason": "Customer profile not found",
        }

    selected_tx = None
    selected_alert = None
    if transaction_id:
        selected_tx = _first(_rows("transactions", data_dir), "transaction_id", transaction_id)
    else:
        selected_alert = _first(_rows("alerts", data_dir), "customer_id", customer_id)
        if selected_alert:
            transaction_id = selected_alert.get("transaction_id")
            selected_tx = _first(_rows("transactions", data_dir), "transaction_id", transaction_id)

    current_usd = float(amount_usd) if amount_usd is not None else (
        float(selected_tx.get("usd_value")) if selected_tx and selected_tx.get("usd_value") is not None else None
    )
    typical_max = profile.get("typical_tx_max_usd")
    monthly_expected = profile.get("expected_monthly_volume_usd")
    ratio_to_max = current_usd / typical_max if current_usd is not None and typical_max else None
    ratio_to_monthly = current_usd / monthly_expected if current_usd is not None and monthly_expected else None

    if current_usd is None:
        severity, mismatch = "Unknown", None
        reason = "No USD transaction value was available"
    elif ratio_to_max is not None and ratio_to_max >= 3:
        severity, mismatch = "High", True
        reason = "Transaction is at least 3x the customer's typical maximum"
    elif ratio_to_max is not None and ratio_to_max > 1:
        severity, mismatch = "Medium", True
        reason = "Transaction exceeds the customer's typical maximum"
    else:
        severity, mismatch = "Low", False
        reason = "Transaction is within the customer's stated typical range"

    return {
        "customer_id": customer_id,
        "profile_found": True,
        "transaction_id": transaction_id,
        "current_amount_usd": current_usd,
        "typical_min_usd": profile.get("typical_tx_min_usd"),
        "typical_max_usd": typical_max,
        "expected_monthly_volume_usd": monthly_expected,
        "ratio_to_typical_max": round(ratio_to_max, 2) if ratio_to_max is not None else None,
        "ratio_to_expected_monthly_volume": round(ratio_to_monthly, 2) if ratio_to_monthly is not None else None,
        "behaviour_mismatch": mismatch,
        "severity": severity,
        "reason": reason,
        "kyc_risk_rating": profile.get("kyc_risk_rating"),
    }


def calculate_risk_score(findings: dict[str, Any]) -> dict[str, Any]:
    """Calculate a deterministic 0-100 score from structured tool findings.

    Expected sections are ``patterns``, ``sanctions``, ``behavior``,
    ``wallet_risk`` and ``customer_profile``.  Flat keys are also accepted.
    Unknown or missing fields add no points.
    """
    patterns = findings.get("patterns") or findings.get("transaction_patterns") or findings
    sanctions = findings.get("sanctions") or findings.get("sanctions_check") or findings
    behavior = findings.get("behavior") or findings.get("customer_behavior") or findings
    wallet = findings.get("wallet_risk") or findings.get("wallet") or findings
    customer = findings.get("customer_profile") or findings.get("customer") or findings

    components: list[dict[str, Any]] = []

    def add(indicator: str, points: int, evidence: Any = True) -> None:
        components.append({"indicator": indicator, "points": points, "evidence": evidence})

    if sanctions.get("direct_match"):
        add("Direct sanctions match", 45)
    elif sanctions.get("indirect_match"):
        add("Indirect sanctions exposure", 30, sanctions.get("nearest_distance_hops"))

    if patterns.get("mixer_exposure"):
        add("Mixer exposure", 25, patterns.get("mixer_wallets"))
    scam_type = str(patterns.get("scam_exposure_type") or "").lower()
    if patterns.get("scam_exposure") and scam_type == "direct":
        add("Direct scam-wallet exposure", 25, patterns.get("scam_wallets"))
    elif patterns.get("scam_exposure"):
        add("Indirect scam-wallet exposure", 15, patterns.get("scam_wallets"))
    if patterns.get("structuring"):
        add("Transaction splitting / structuring", 15)
    if patterns.get("rapid_movement"):
        add("Rapid movement of funds", 10)
    if patterns.get("new_wallet_cluster"):
        add("Cluster of newly created wallets", 5)
    if patterns.get("multiple_hops"):
        add("Multi-hop transaction path", 5)
    if patterns.get("branching_network"):
        add("Branching or consolidation network", 5)

    behavior_severity = str(behavior.get("severity") or "").lower()
    if behavior.get("behaviour_mismatch") and behavior_severity == "high":
        add("High customer-behaviour mismatch", 10, behavior.get("ratio_to_typical_max"))
    elif behavior.get("behaviour_mismatch"):
        add("Customer-behaviour mismatch", 5, behavior.get("ratio_to_typical_max"))

    wallet_label = str(wallet.get("risk_label") or "").lower()
    if wallet_label == "critical":
        add("Critical wallet-risk label", 10)
    elif wallet_label == "high":
        add("High wallet-risk label", 5)
    elif wallet_label == "medium":
        add("Medium wallet-risk label", 2)

    kyc_label = str(
        customer.get("kyc_risk_rating") or behavior.get("kyc_risk_rating") or ""
    ).lower()
    if kyc_label == "high":
        add("High KYC risk rating", 5)
    elif kyc_label == "medium":
        add("Medium KYC risk rating", 3)

    raw_score = sum(component["points"] for component in components)
    score = min(100, raw_score)
    if score >= 75:
        level = "Critical"
        action = "Escalate for enhanced human compliance review"
    elif score >= 50:
        level = "High"
        action = "Escalate to a compliance officer"
    elif score >= 25:
        level = "Medium"
        action = "Continue monitoring and request more information if needed"
    else:
        level = "Low"
        action = "Consider closing after human review"

    return {
        "score": score,
        "risk_level": level,
        "components": components,
        "recommended_action": action,
        "method": "Deterministic weighted rules; score capped at 100",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate_data(), indent=2))
