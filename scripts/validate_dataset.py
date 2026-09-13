#!/usr/bin/env python3
"""Validation du dataset DATA DETECTIVE.

Deux niveaux de controle :

1. Integrite technique - cles etrangeres, unicite, dates, devises, montants.
2. Integrite de l'enquete - la verite de CASE #001 est-elle reellement
   presente et retrouvable par analyse ? Chaque indice du canon fait l'objet
   d'un controle chiffre. Si l'un d'eux cesse d'etre detectable, le dataset
   est invalide meme si toutes les cles etrangeres sont correctes.

Usage :
    python scripts/validate_dataset.py [--data data/generated] [--truth data/truth]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generation import config  # noqa: E402

SPECIAL_ACTORS = {"SYSTEM_AUTO", "EXTERNAL"}


class Report:
    """Collecteur de resultats de controle."""

    def __init__(self) -> None:
        self.sections: dict[str, list[tuple[str, bool, str]]] = {}
        self.failures = 0

    def check(self, section: str, label: str, passed: bool, detail: str = "") -> bool:
        self.sections.setdefault(section, []).append((label, passed, detail))
        if not passed:
            self.failures += 1
        return passed

    def render(self) -> str:
        lines = ["", "DATASET VALIDATION", "-" * 66, ""]
        for section, checks in self.sections.items():
            lines.append(f"{section}")
            for label, passed, detail in checks:
                status = "PASS" if passed else "FAIL"
                suffix = f"   {detail}" if detail else ""
                lines.append(f"  {label:<44s} {status}{suffix}")
            lines.append("")
        lines.append("-" * 66)
        verdict = "PASS" if self.failures == 0 else f"FAIL ({self.failures} controle(s))"
        lines.append(f"{'RESULTAT GLOBAL':<46s} {verdict}")
        lines.append("")
        return "\n".join(lines)


def load(data_dir: Path) -> dict[str, pd.DataFrame]:
    names = ["entities", "employees", "accounts", "transactions", "investments",
             "companies", "company_officers", "entity_relationships", "audit_logs"]
    tables: dict[str, pd.DataFrame] = {}
    for name in names:
        path = data_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Table manquante : {path}")
        tables[name] = pd.read_csv(path)
    return tables


# --------------------------------------------------------------------------
# Niveau 1 - integrite technique
# --------------------------------------------------------------------------

def check_structure(tables: dict[str, pd.DataFrame], report: Report) -> None:
    expected_min = {
        "entities": 100, "employees": 300, "accounts": 200, "transactions": 100_000,
        "investments": 100, "companies": 100, "company_officers": 100,
        "entity_relationships": 100, "audit_logs": 40_000,
    }
    for name, frame in tables.items():
        report.check("Tables", name.capitalize(),
                     len(frame) >= expected_min[name], f"{len(frame):,} lignes")


def check_primary_keys(tables: dict[str, pd.DataFrame], report: Report) -> None:
    keys = {
        "entities": "entity_id", "employees": "employee_id", "accounts": "account_id",
        "transactions": "transaction_id", "investments": "investment_id",
        "companies": "company_id", "company_officers": "officer_id",
        "entity_relationships": "relationship_id", "audit_logs": "log_id",
    }
    duplicates = []
    for name, key in keys.items():
        frame = tables[name]
        n_dup = int(frame[key].duplicated().sum()) + int(frame[key].isna().sum())
        if n_dup:
            duplicates.append(f"{name}:{n_dup}")
    report.check("Cles", "Unicite des cles primaires", not duplicates,
                 ", ".join(duplicates))


def check_foreign_keys(tables: dict[str, pd.DataFrame], report: Report) -> None:
    entity_ids = set(tables["entities"]["entity_id"])
    account_ids = set(tables["accounts"]["account_id"])
    employee_ids = set(tables["employees"]["employee_id"])
    company_ids = set(tables["companies"]["company_id"])
    tx = tables["transactions"]

    problems: list[str] = []

    def orphans(series: pd.Series, universe: set, label: str, allow: set = frozenset()) -> None:
        values = series.dropna()
        values = values[~values.isin(allow)]
        missing = int((~values.isin(universe)).sum())
        if missing:
            problems.append(f"{label}:{missing}")

    orphans(tx["source_entity_id"], entity_ids, "tx.source_entity_id")
    orphans(tx["destination_entity_id"], entity_ids, "tx.destination_entity_id")
    orphans(tx["source_account_id"], account_ids, "tx.source_account_id")
    orphans(tx["destination_account_id"], account_ids, "tx.destination_account_id")
    orphans(tx["created_by"], employee_ids, "tx.created_by", SPECIAL_ACTORS)
    orphans(tx["authorized_by"], employee_ids, "tx.authorized_by", SPECIAL_ACTORS)
    orphans(tables["accounts"]["entity_id"], entity_ids, "accounts.entity_id")
    orphans(tables["employees"]["entity_id"], entity_ids, "employees.entity_id")
    orphans(tables["entities"]["parent_entity_id"], entity_ids, "entities.parent_entity_id")
    orphans(tables["investments"]["entity_id"], entity_ids, "investments.entity_id")
    orphans(tables["investments"]["target_entity_id"], entity_ids,
            "investments.target_entity_id")
    orphans(tables["companies"]["entity_id"], entity_ids, "companies.entity_id")
    orphans(tables["company_officers"]["company_id"], company_ids,
            "company_officers.company_id")
    orphans(tables["entity_relationships"]["source_entity_id"], entity_ids, "rel.source")
    orphans(tables["entity_relationships"]["target_entity_id"], entity_ids, "rel.target")
    orphans(tables["audit_logs"]["employee_id"], employee_ids, "audit.employee_id")
    orphans(tables["audit_logs"]["entity_id"], entity_ids, "audit.entity_id")

    report.check("Integrite", "Cles etrangeres", not problems, ", ".join(problems))


def check_transactions(tables: dict[str, pd.DataFrame], report: Report) -> None:
    tx = tables["transactions"].copy()
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])

    report.check("Integrite", "Montants strictement positifs",
                 bool((tx["amount"] > 0).all() and (tx["amount_eur"] > 0).all()))

    same = int((tx["source_account_id"] == tx["destination_account_id"]).sum())
    report.check("Integrite", "Source et destination distinctes", same == 0,
                 f"{same} identiques" if same else "")

    in_period = tx["transaction_date"].dt.date.between(config.PERIOD_START, config.PERIOD_END)
    report.check("Dates", "Transactions dans la periode", bool(in_period.all()),
                 f"{int((~in_period).sum())} hors periode")

    accounts = tables["accounts"].copy()
    accounts["opening_date"] = pd.to_datetime(accounts["opening_date"])
    accounts["closing_date"] = pd.to_datetime(accounts["closing_date"])
    merged = tx.merge(accounts[["account_id", "opening_date", "closing_date", "currency"]],
                      left_on="source_account_id", right_on="account_id", how="left")
    before_opening = int((merged["transaction_date"] < merged["opening_date"]).sum())
    after_closing = int((merged["closing_date"].notna()
                         & (merged["transaction_date"] > merged["closing_date"])).sum())
    report.check("Dates", "Comptes ouverts a la date d'operation",
                 before_opening == 0 and after_closing == 0,
                 f"{before_opening} avant ouverture, {after_closing} apres cloture")

    mismatch = int((merged["currency_x"] != merged["currency_y"]).sum())
    report.check("Devises", "Devise conforme au compte source", mismatch == 0,
                 f"{mismatch} ecarts" if mismatch else "")

    known = set(config.FX_BASE)
    unknown = set(tx["currency"].unique()) - known
    report.check("Devises", "Devises referencees", not unknown, ", ".join(sorted(unknown)))

    # Coherence du montant converti : l'ecart doit rester dans la bande de
    # change mensuelle utilisee par le generateur.
    ratio = tx["amount_eur"] / tx["amount"]
    eur = tx["currency"] == "EUR"
    report.check("Devises", "Conversion EUR coherente",
                 bool((ratio[eur].round(6) == 1.0).all()))


def check_people_and_entities(tables: dict[str, pd.DataFrame], report: Report) -> None:
    employees = tables["employees"].copy()
    entities = tables["entities"].copy()
    employees["hire_date"] = pd.to_datetime(employees["hire_date"])
    employees["termination_date"] = pd.to_datetime(employees["termination_date"])
    entities["creation_date"] = pd.to_datetime(entities["creation_date"])

    merged = employees.merge(entities[["entity_id", "creation_date"]], on="entity_id",
                             how="left")
    early = int((merged["hire_date"] < merged["creation_date"]).sum())
    report.check("Dates", "Embauches posterieures a la creation de l'entite", early == 0,
                 f"{early} anterieures" if early else "")

    bad_term = int((employees["termination_date"].notna()
                    & (employees["termination_date"] < employees["hire_date"])).sum())
    report.check("Dates", "Sorties posterieures aux embauches", bad_term == 0)

    active_with_term = int(((employees["status"] == "active")
                            & employees["termination_date"].notna()).sum())
    report.check("Coherence", "Statut RH coherent avec la date de sortie",
                 active_with_term == 0)

    levels = employees["authorization_level"]
    report.check("Coherence", "Niveaux d'autorisation dans [1,5]",
                 bool(levels.between(1, 5).all()))

    # Aucune boucle capitalistique.
    parents = dict(zip(entities["entity_id"], entities["parent_entity_id"]))
    cycles = 0
    for start in parents:
        seen, current, depth = {start}, parents.get(start), 0
        while isinstance(current, str) and depth < 20:
            if current in seen:
                cycles += 1
                break
            seen.add(current)
            current = parents.get(current)
            depth += 1
    report.check("Coherence", "Absence de cycle dans la structure", cycles == 0)


def check_audit(tables: dict[str, pd.DataFrame], report: Report) -> None:
    logs = tables["audit_logs"].copy()
    logs["timestamp"] = pd.to_datetime(logs["timestamp"])
    in_period = logs["timestamp"].dt.date.between(config.PERIOD_START, config.PERIOD_END)
    report.check("Dates", "Journaux dans la periode", bool(in_period.all()),
                 f"{int((~in_period).sum())} hors periode")

    tx_ids = set(tables["transactions"]["transaction_id"])
    refs = logs[logs["resource_type"] == "transaction"]["resource_id"].dropna()
    missing = int((~refs.isin(tx_ids)).sum())
    report.check("Integrite", "Ressources de type transaction existantes", missing == 0,
                 f"{missing} references inconnues" if missing else "")


def check_no_leakage(tables: dict[str, pd.DataFrame], report: Report) -> None:
    """Aucune colonne ne doit designer la solution."""
    forbidden = {"is_suspicious", "is_fraud", "is_criminal", "flag", "anomaly",
                 "suspicious", "fraud_score", "label", "target"}
    found = []
    for name, frame in tables.items():
        for column in frame.columns:
            if column.lower() in forbidden:
                found.append(f"{name}.{column}")
    report.check("Etancheite", "Absence de colonne revelatrice", not found, ", ".join(found))

    # Les libelles du circuit doivent etre indiscernables des libelles courants.
    tx = tables["transactions"]
    circuit = tx[tx["destination_entity_id"] == "ENT-0012"]
    others = tx[(tx["transaction_type"] == "service_payment")
                & (tx["destination_entity_id"] != "ENT-0012")]
    exclusive = set(circuit["description"]) - set(others["description"])
    report.check("Etancheite", "Libelles du circuit non distinctifs", not exclusive,
                 ", ".join(sorted(exclusive)))


# --------------------------------------------------------------------------
# Niveau 2 - integrite de l'enquete
# --------------------------------------------------------------------------

def _days_to_quarter_end(day: dt.date) -> int:
    quarter = (day.month - 1) // 3
    month, last = ((3, 31), (6, 30), (9, 30), (12, 31))[quarter]
    return (dt.date(day.year, month, last) - day).days


def check_case_integrity(tables: dict[str, pd.DataFrame], truth: dict,
                         report: Report) -> None:
    tx = tables["transactions"].copy()
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])
    inv = tables["investments"]

    circuit_ids = set(truth["suspicious_transactions"]["all_circuit"])
    present = int(tx["transaction_id"].isin(circuit_ids).sum())
    report.check("Enquete", "Transactions du circuit presentes",
                 present == len(circuit_ids), f"{present}/{len(circuit_ids)}")

    # --- Reconstitution des 47,8 M EUR --------------------------------------
    inflow = tx[tx["transaction_id"].isin(
        truth["suspicious_transactions"]["circuit_inflow"])]
    a = float(inv.loc[inv["investment_id"] == "INV-0001", "amount_eur"].iloc[0])
    b_c = float(inflow["amount_eur"].sum())
    total = a + b_c
    report.check("Enquete", "Reconstitution du montant de l'affaire",
                 abs(total - truth["total_amount_eur"]) < 1_500,
                 f"{total:,.0f} EUR pour {truth['total_amount_eur']:,.0f} attendus")

    # --- EV-01 bunching sous le seuil ---------------------------------------
    threshold = truth["dual_approval_threshold_eur"]
    service = tx[(tx["transaction_type"] == "service_payment")
                 & (tx["status"] == "completed")]
    below = service[service["amount_eur"].between(threshold * 0.88, threshold)]
    above = service[service["amount_eur"].between(threshold, threshold * 1.12)]
    ratio = len(below) / max(len(above), 1)
    report.check("Enquete", "EV-01 concentration sous le seuil", ratio >= 1.8,
                 f"{len(below)} sous / {len(above)} au-dessus (x{ratio:.1f})")
    report.check("Enquete", "EV-01 aucun paiement du circuit au-dessus du seuil",
                 bool((inflow["amount_eur"] < threshold).all()))

    # --- EV-02 fin de trimestre ---------------------------------------------
    circuit_dqe = inflow["transaction_date"].dt.date.map(_days_to_quarter_end)
    baseline_dqe = service[~service["transaction_id"].isin(circuit_ids)]
    baseline_share = baseline_dqe["transaction_date"].dt.date.map(
        _days_to_quarter_end).le(8).mean()
    report.check("Enquete", "EV-02 concentration en fin de trimestre",
                 bool((circuit_dqe <= 8).all()) and baseline_share < 0.25,
                 f"circuit 100 % vs socle {baseline_share:.1%}")

    # --- EV-03 graphe -------------------------------------------------------
    sources = tx[tx["destination_entity_id"] == "ENT-0012"]["source_entity_id"].nunique()
    out_total = tx[tx["source_entity_id"] == "ENT-0012"]["amount_eur"].sum()
    in_total = tx[tx["destination_entity_id"] == "ENT-0012"]["amount_eur"].sum()
    report.check("Enquete", "EV-03 contreparties d'Aurum limitees", sources <= 3,
                 f"{sources} sources")
    report.check("Enquete", "EV-03 reversement integral",
                 abs(out_total - in_total) < 1_000,
                 f"entrees {in_total:,.0f} / sorties {out_total:,.0f}")
    loans = tx[(tx["transaction_type"] == "loan")
               & (tx["source_entity_id"] == "ENT-0013")]
    repayments = tx[(tx["transaction_type"] == "repayment")
                    & (tx["source_entity_id"] == "ENT-0013")]
    report.check("Enquete", "EV-03 remboursements sans pret d'origine",
                 len(loans) == 0 and len(repayments) > 0,
                 f"{len(repayments)} remboursements, {len(loans)} decaissement")

    # --- EV-04 lien nominatif ------------------------------------------------
    officers = tables["company_officers"]
    employees = tables["employees"]
    companies = tables["companies"]
    joined = officers.merge(employees, on=["first_name", "last_name"], how="inner")
    joined = joined.merge(companies[["company_id", "entity_id"]], on="company_id",
                          suffixes=("", "_company"))
    aurum = joined[joined["entity_id_company"] == "ENT-0012"]
    report.check("Enquete", "EV-04 dirigeant d'Aurum rapprochable du fichier RH",
                 len(aurum) == 1 and bool((aurum["status"] == "inactive").all()))
    report.check("Enquete", "EV-04 faux positifs de rapprochement presents",
                 len(joined) >= 20, f"{len(joined)} rapprochements bruts")

    # --- EV-05 rendement -----------------------------------------------------
    cohort = inv[(inv["sector"] == "luxury_real_estate") & (inv["currency"] == "AED")
                 & (inv["investment_date"] >= "2023-10-01")]
    others = cohort[cohort["investment_id"] != "INV-0001"]["actual_return"]
    crescent = float(cohort.loc[cohort["investment_id"] == "INV-0001",
                                "actual_return"].iloc[0])
    z = (crescent - others.mean()) / others.std()
    report.check("Enquete", "EV-05 rendement hors cohorte", z >= 3.0,
                 f"z = {z:.1f} sur {len(others)} comparables")

    # --- EV-06 sequence d'acces ---------------------------------------------
    logs = tables["audit_logs"].copy()
    logs["timestamp"] = pd.to_datetime(logs["timestamp"])
    home = dict(zip(employees["employee_id"], employees["country"]))
    logs["home"] = logs["employee_id"].map(home)
    night = logs[logs["timestamp"].dt.hour.isin([23, 0, 1, 2])
                 & logs["ip_region"].notna()
                 & (logs["ip_region"] != logs["home"])]
    counts = night["employee_id"].value_counts()
    report.check("Enquete", "EV-06 sequence d'acces presente",
                 counts.get("EMP-0004", 0) >= 18,
                 f"{counts.get('EMP-0004', 0)} acces nocturnes hors zone")
    report.check("Enquete", "EV-06 autres profils comparables presents",
                 int((counts >= 8).sum()) >= 3,
                 f"{int((counts >= 8).sum())} employes au-dessus de 8 acces")

    # --- Fausses pistes ------------------------------------------------------
    lead_checks: list[str] = []
    for lead in truth["false_leads"]:
        ids = lead.get("transaction_ids") or []
        if ids and int(tx["transaction_id"].isin(ids).sum()) != len(ids):
            lead_checks.append(lead["id"])
    report.check("Fausses pistes", "Transactions des fausses pistes presentes",
                 not lead_checks, ", ".join(lead_checks))

    cancelled = tx[tx["status"] == "cancelled"]
    milan_rate = len(cancelled[cancelled["source_entity_id"] == "ENT-0004"]) / max(
        len(tx[tx["source_entity_id"] == "ENT-0004"]), 1)
    global_rate = len(cancelled) / len(tx)
    report.check("Fausses pistes", "FL-05 taux d'annulation distinctif",
                 milan_rate > global_rate * 1.8,
                 f"Milan {milan_rate:.2%} vs groupe {global_rate:.2%}")

    big = tx[tx["amount_eur"] >= config.CFO_APPROVAL_THRESHOLD_EUR]
    cfo_share = float((big["authorized_by"] == "EMP-0002").mean())
    report.check("Fausses pistes", "FL-02 signature systematique du CFO",
                 cfo_share > 0.75 and int((inflow["authorized_by"] == "EMP-0002").sum()) == 0,
                 f"{cfo_share:.0%} des operations > 1 M EUR, 0 dans le circuit")

    # --- Discretion du circuit ----------------------------------------------
    share_count = len(circuit_ids) / len(tx)
    # Le tri decroissant sur le montant ne doit pas remonter le circuit de
    # facturation. L'investissement initial, lui, est legitimement volumineux
    # et figure normalement parmi les plus grosses operations du groupe.
    billing_ids = set(truth["suspicious_transactions"]["circuit_inflow"]) | set(
        truth["suspicious_transactions"]["diversion"])
    top_amounts = tx.nlargest(300, "amount_eur")["transaction_id"]
    in_top = int(top_amounts.isin(billing_ids).sum())
    report.check("Enquete", "Circuit non resoluble par simple tri sur le montant",
                 in_top == 0, f"{in_top} paiements du circuit dans le top 300")
    report.check("Enquete", "Circuit dilue dans le volume", share_count < 0.002,
                 f"{share_count:.4%} des transactions")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validation du dataset DATA DETECTIVE")
    parser.add_argument("--data", default="data/generated", type=Path)
    parser.add_argument("--truth", default="data/truth", type=Path)
    parser.add_argument("--save", type=Path, default=None,
                        help="Chemin d'ecriture du rapport texte")
    args = parser.parse_args()

    tables = load(ROOT / args.data)
    with (ROOT / args.truth / "case_truth.json").open(encoding="utf-8") as handle:
        truth = json.load(handle)

    report = Report()
    check_structure(tables, report)
    check_primary_keys(tables, report)
    check_foreign_keys(tables, report)
    check_transactions(tables, report)
    check_people_and_entities(tables, report)
    check_audit(tables, report)
    check_no_leakage(tables, report)
    check_case_integrity(tables, truth, report)

    rendered = report.render()
    print(rendered)
    if args.save:
        (ROOT / args.save).write_text(rendered, encoding="utf-8")
    return 0 if report.failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
