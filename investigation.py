"""Deterministic investigation orchestrator for the CryptoShield MVP.

This module deliberately contains no LLM calls.  It coordinates the data and
analysis functions exposed by ``tools.py`` and returns only JSON-serializable
objects suitable for a CLI, API, or Streamlit UI.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import tools


DEFAULT_CASES = ("CASE001", "CASE002", "CASE003")
REQUIRED_ALERT_FIELDS = ("customer_id", "transaction_id", "wallet_address")


def _json_safe(value: Any) -> Any:
    """Recursively convert common Python values into strict JSON values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return str(value)


def _error_result(
    case_id: str,
    message: str,
    *,
    error_type: str,
    validation: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build the same predictable error envelope for every failure path."""
    return _json_safe(
        {
            "case_id": case_id,
            "status": "error",
            "error": {"type": error_type, "message": message},
            "warnings": warnings or [],
            "validation": validation,
            "alert": None,
            "findings": None,
            "risk": None,
        }
    )


def _highest_risk_wallet(
    assessments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the highest-scoring discovered wallet for risk-score input."""
    if not assessments:
        return {
            "found": False,
            "wallet_address": None,
            "risk_label": "Unknown",
            "risk_score": None,
            "risk_tags": [],
        }

    def rank(item: dict[str, Any]) -> tuple[float, int]:
        raw_score = item.get("risk_score")
        try:
            score = float(raw_score) if raw_score is not None else -1.0
        except (TypeError, ValueError):
            score = -1.0
        label_rank = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
            "unknown": 0,
        }.get(str(item.get("risk_label") or "unknown").lower(), 0)
        return score, label_rank

    return max(assessments, key=rank)


def investigate_case(
    case_id: str,
    *,
    data_dir: str | Path | None = None,
    max_hops: int = 3,
) -> dict[str, Any]:
    """Run the complete deterministic CryptoShield investigation workflow.

    Expected operational/data problems are returned in a stable error envelope
    instead of escaping to the UI.  A successful result contains the alert,
    structured evidence, deterministic risk score, and non-fatal warnings.
    """
    normalized_case_id = str(case_id or "").strip().upper()
    if not normalized_case_id:
        return _error_result(
            normalized_case_id,
            "case_id must be a non-empty string",
            error_type="invalid_case_id",
        )
    if not isinstance(max_hops, int) or isinstance(max_hops, bool) or not 0 <= max_hops <= 10:
        return _error_result(
            normalized_case_id,
            "max_hops must be an integer between 0 and 10",
            error_type="invalid_max_hops",
        )

    warnings: list[str] = []
    validation: dict[str, Any] | None = None

    try:
        # Step 1: Validate all five datasets before relying on their links.
        validation = tools.validate_data(data_dir=data_dir)
        warnings.extend(validation.get("warnings") or [])
        if not validation.get("valid", False):
            errors = validation.get("errors") or ["Unknown data validation error"]
            return _error_result(
                normalized_case_id,
                "; ".join(str(error) for error in errors),
                error_type="data_validation_failed",
                validation=validation,
                warnings=warnings,
            )

        # Step 2: Load the incoming AML alert that starts the investigation.
        alert = tools.get_alert(normalized_case_id, data_dir=data_dir)
        if alert is None:
            return _error_result(
                normalized_case_id,
                f"No alert was found for case_id {normalized_case_id}",
                error_type="alert_not_found",
                validation=validation,
                warnings=warnings,
            )

        missing_fields = [field for field in REQUIRED_ALERT_FIELDS if not alert.get(field)]
        if missing_fields:
            return _error_result(
                normalized_case_id,
                "Alert is missing required values: " + ", ".join(missing_fields),
                error_type="incomplete_alert",
                validation=validation,
                warnings=warnings,
            )

        wallet_address = str(alert["wallet_address"])
        customer_id = str(alert["customer_id"])
        transaction_id = str(alert["transaction_id"])

        # Step 3: Retrieve transactions touching the alert wallet for this case.
        history = tools.get_transaction_history(
            wallet_address,
            direction="both",
            case_id=normalized_case_id,
            data_dir=data_dir,
        )
        if not history.get("transactions"):
            warnings.append("No transaction history was found for the alert wallet")
        elif transaction_id not in {
            str(tx.get("transaction_id")) for tx in history.get("transactions", [])
        }:
            warnings.append("The alert transaction is not present in the wallet history")

        # Step 4: Trace the local transaction graph to discover connected nodes.
        network = tools.trace_transaction_network(
            wallet_address,
            max_hops=max_hops,
            direction="both",
            case_id=normalized_case_id,
            data_dir=data_dir,
        )
        discovered_wallets = list(
            dict.fromkeys(
                node.get("wallet_address")
                for node in network.get("nodes", [])
                if node.get("wallet_address")
            )
        )
        if wallet_address not in discovered_wallets:
            discovered_wallets.insert(0, wallet_address)

        # Step 5: Detect explainable patterns such as structuring and rapid flow.
        patterns = tools.analyze_transaction_patterns(
            wallet_address,
            case_id=normalized_case_id,
            max_hops=max_hops,
            data_dir=data_dir,
        )

        # Step 6: Inspect every node; retain all evidence and a scoring summary.
        wallet_assessments = [
            tools.lookup_wallet_risk(address, data_dir=data_dir)
            for address in discovered_wallets
        ]
        unknown_wallets = [
            result.get("wallet_address")
            for result in wallet_assessments
            if not result.get("found")
        ]
        if unknown_wallets:
            warnings.append(
                f"Risk metadata was unavailable for {len(unknown_wallets)} wallet(s)"
            )
        highest_risk_wallet = _highest_risk_wallet(wallet_assessments)

        # Step 7: Check direct and indirect sanctions exposure from all nodes.
        sanctions = tools.check_sanctions(
            discovered_wallets,
            max_hops=max_hops,
            data_dir=data_dir,
        )

        # Step 8: Load KYC/customer context.  A missing profile is non-fatal and
        # is represented explicitly so the risk result never invents evidence.
        customer_profile = tools.get_customer_profile(customer_id, data_dir=data_dir)
        if customer_profile is None:
            warnings.append(f"Customer profile was not found for {customer_id}")

        # Step 9: Compare this alert transaction with the customer's known range.
        behavior = tools.compare_customer_behavior(
            customer_id,
            transaction_id=transaction_id,
            data_dir=data_dir,
        )
        if not behavior.get("profile_found", False):
            warnings.append("Customer behavior could not be evaluated")

        # Step 10: Assemble the exact structured sections expected by the
        # deterministic scoring function, plus richer evidence for the UI.
        findings = {
            "transaction_history": history,
            "network": network,
            "patterns": patterns,
            "wallet_risk": highest_risk_wallet,
            "wallet_assessments": wallet_assessments,
            "sanctions": sanctions,
            "customer_profile": customer_profile or {
                "customer_id": customer_id,
                "profile_found": False,
            },
            "behavior": behavior,
        }

        # Step 11: Calculate the final explainable score using tools.py only.
        risk = tools.calculate_risk_score(findings)

        result = {
            "case_id": normalized_case_id,
            "status": "success",
            "error": None,
            "warnings": list(dict.fromkeys(warnings)),
            "validation": validation,
            "alert": alert,
            "findings": findings,
            "risk": risk,
        }
        return _json_safe(result)

    except FileNotFoundError as exc:
        return _error_result(
            normalized_case_id,
            str(exc),
            error_type="data_file_not_found",
            validation=validation,
            warnings=warnings,
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return _error_result(
            normalized_case_id,
            str(exc),
            error_type="investigation_failed",
            validation=validation,
            warnings=warnings,
        )


def main() -> int:
    """Run CASE001/CASE002/CASE003 by default and print valid JSON."""
    parser = argparse.ArgumentParser(
        description="Run deterministic CryptoShield case investigations."
    )
    parser.add_argument(
        "case_ids",
        nargs="*",
        default=list(DEFAULT_CASES),
        help="Case IDs to investigate (default: CASE001 CASE002 CASE003)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory containing the five CryptoShield CSV files",
    )
    parser.add_argument(
        "--max-hops",
        type=int,
        default=3,
        help="Maximum network trace depth from 0 to 10 (default: 3)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON",
    )
    args = parser.parse_args()

    results = [
        investigate_case(
            case_id,
            data_dir=args.data_dir,
            max_hops=args.max_hops,
        )
        for case_id in args.case_ids
    ]
    output: Any = results[0] if len(results) == 1 else results
    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            allow_nan=False,
        )
    )
    return 0 if all(result.get("status") == "success" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
