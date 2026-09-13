#!/usr/bin/env python3
"""Generation complete du dataset DATA DETECTIVE - CASE #001.

Usage :
    python scripts/generate_data.py [--output data/generated]

Le script est deterministe : a seed constante, il reproduit exactement le meme
dataset, y compris les identifiants.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generation import config  # noqa: E402
from src.generation.accounts import account_index, build_accounts  # noqa: E402
from src.generation.audit import build_audit_logs  # noqa: E402
from src.generation.entities import build_entities, build_relationships  # noqa: E402
from src.generation.investments import build_investments  # noqa: E402
from src.generation.people import build_employees, build_officers  # noqa: E402
from src.generation.scenario import build_scenario  # noqa: E402
from src.generation.transactions import Roster, build_baseline  # noqa: E402
from src.generation.truth import build_case_truth  # noqa: E402
from src.generation.utils import transaction_id  # noqa: E402

PUBLIC_COLUMNS = {
    "entities": ["entity_id", "entity_name", "entity_type", "parent_entity_id", "country",
                 "city", "industry", "creation_date", "status"],
    "employees": ["employee_id", "first_name", "last_name", "position", "department",
                  "entity_id", "country", "hire_date", "termination_date",
                  "authorization_level", "status"],
    "accounts": ["account_id", "entity_id", "bank_name", "country", "city", "currency",
                 "account_type", "opening_date", "closing_date", "status"],
    "transactions": ["transaction_id", "transaction_date", "source_account_id",
                     "destination_account_id", "source_entity_id", "destination_entity_id",
                     "amount", "currency", "amount_eur", "transaction_type", "reference",
                     "description", "status", "authorized_by", "created_by"],
    "investments": ["investment_id", "entity_id", "investment_date", "target_entity_id",
                    "amount", "currency", "amount_eur", "sector", "expected_return",
                    "actual_return", "maturity_date", "status"],
    "companies": ["company_id", "company_name", "entity_id", "country", "city", "industry",
                  "creation_date", "ownership_type", "risk_level", "status"],
    "company_officers": ["officer_id", "company_id", "first_name", "last_name", "role",
                         "appointment_date", "nationality"],
    "entity_relationships": ["relationship_id", "source_entity_id", "target_entity_id",
                             "relationship_type", "start_date", "end_date",
                             "confidence_score"],
    "audit_logs": ["log_id", "employee_id", "timestamp", "action", "resource_type",
                   "resource_id", "entity_id", "result", "ip_region"],
}


def _log(step: str, started: float) -> float:
    now = time.time()
    print(f"  {step:<44s} {now - started:6.2f}s")
    return now


def generate(output_dir: Path, truth_dir: Path) -> dict:
    print(f"\nDATA DETECTIVE - generation du dataset (SEED={config.SEED})")
    print(f"Periode : {config.PERIOD_START} -> {config.PERIOD_END}\n")
    clock = time.time()

    entities, companies = build_entities()
    clock = _log("referentiel entites et societes", clock)

    employees = build_employees(entities)
    officers = build_officers(entities, companies, employees)
    clock = _log("employes et dirigeants", clock)

    accounts = build_accounts(entities)
    accounts_idx = account_index(accounts)
    clock = _log("comptes bancaires", clock)

    roster = Roster(employees)
    baseline = build_baseline(entities, accounts_idx, roster)
    clock = _log(f"socle de transactions ({len(baseline):,})", clock)

    scenario_rows, truth_seed = build_scenario(entities, accounts_idx, roster)
    clock = _log(f"scenario et fausses pistes ({len(scenario_rows):,})", clock)

    for row in baseline:
        row["_tag"] = "baseline"
    all_rows = baseline + scenario_rows

    transactions = pd.DataFrame(all_rows)
    # Tri chronologique avant attribution des identifiants : l'ordre
    # d'injection interne du generateur ne doit laisser aucune trace.
    transactions = transactions.sort_values(
        ["transaction_date", "amount_eur", "source_entity_id", "destination_entity_id"],
        kind="mergesort",
    ).reset_index(drop=True)
    transactions.insert(0, "transaction_id",
                        [transaction_id(i + 1) for i in range(len(transactions))])
    clock = _log(f"consolidation transactions ({len(transactions):,})", clock)

    investments = build_investments(entities)
    relationships = build_relationships(entities)
    clock = _log("investissements et relations", clock)

    circuit_dates = [dt.date.fromisoformat(d) for d in truth_seed["circuit_payment_dates"]]
    audit_logs = build_audit_logs(employees, transactions, circuit_dates)
    clock = _log(f"journaux d'audit ({len(audit_logs):,})", clock)

    truth = build_case_truth(truth_seed, transactions, investments)

    # --- Ecriture -----------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    tables = {
        "entities": entities,
        "employees": employees,
        "accounts": accounts,
        "transactions": transactions,
        "investments": investments,
        "companies": companies,
        "company_officers": officers,
        "entity_relationships": relationships,
        "audit_logs": audit_logs,
    }

    for name, frame in tables.items():
        public = frame[PUBLIC_COLUMNS[name]]
        public.to_csv(output_dir / f"{name}.csv", index=False)

    with (truth_dir / "case_truth.json").open("w", encoding="utf-8") as handle:
        json.dump(truth, handle, indent=2, ensure_ascii=False)

    _log("ecriture des fichiers", clock)

    _print_statistics(tables, truth)
    return {"tables": tables, "truth": truth}


def _print_statistics(tables: dict[str, pd.DataFrame], truth: dict) -> None:
    tx = tables["transactions"]
    completed = tx[tx["status"] == "completed"]
    print("\n" + "=" * 62)
    print("STATISTIQUES DU DATASET")
    print("=" * 62)
    print(f"  Entites                      {len(tables['entities']):>12,}")
    print(f"  Societes externes            {len(tables['companies']):>12,}")
    print(f"  Dirigeants declares          {len(tables['company_officers']):>12,}")
    print(f"  Employes                     {len(tables['employees']):>12,}")
    print(f"  Comptes bancaires            {len(tables['accounts']):>12,}")
    print(f"  Transactions                 {len(tx):>12,}")
    print(f"  Investissements              {len(tables['investments']):>12,}")
    print(f"  Relations declarees          {len(tables['entity_relationships']):>12,}")
    print(f"  Journaux d'audit             {len(tables['audit_logs']):>12,}")
    print("-" * 62)
    print(f"  Volume financier total       {completed['amount_eur'].sum():>12,.0f} EUR")
    print(f"  Montant median               {completed['amount_eur'].median():>12,.0f} EUR")
    print(f"  Pays couverts                {tx['currency'].nunique():>12,} devises, "
          f"{tables['entities']['country'].nunique()} pays")
    print("-" * 62)
    print(f"  Montant de l'affaire         {truth['total_amount_eur']:>12,.0f} EUR")
    print(f"  Transactions du circuit      {truth['statistics']['circuit_transactions']:>12,}")
    print(f"  Part du volume total         {truth['statistics']['circuit_share_of_volume']:>11.3%}")
    print(f"  Part du nombre total         {truth['statistics']['circuit_share_of_count']:>11.4%}")
    print(f"  Transactions fausses pistes  {truth['statistics']['false_lead_transactions']:>12,}")
    print("=" * 62 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generateur de dataset DATA DETECTIVE")
    parser.add_argument("--output", default="data/generated", type=Path)
    parser.add_argument("--truth", default="data/truth", type=Path)
    args = parser.parse_args()
    generate(ROOT / args.output, ROOT / args.truth)


if __name__ == "__main__":
    main()
