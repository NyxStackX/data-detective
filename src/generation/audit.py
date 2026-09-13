"""Generation des journaux d'audit applicatif.

Les logs remplissent trois fonctions : refleter l'activite normale des
collaborateurs, documenter les approbations effectivement tracees dans
`transactions`, et porter le sixieme indice - une sequence d'acces qui precede
systematiquement les paiements du circuit.

Le bruit est calibre pour que ni l'horaire tardif, ni la region IP inhabituelle
ne soient discriminants pris isolement : seule leur conjonction, correlee aux
dates de paiement, l'est.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config
from .utils import ALL_BUSINESS_DAYS, log_id, make_rng

_RESOURCE_TYPES = ["transaction", "account", "investment", "report", "entity", "employee"]

_ACTION_WEIGHTS = {
    "login": 0.20, "logout": 0.17, "view_transaction": 0.18, "view_account": 0.10,
    "view_report": 0.12, "export_data": 0.05, "download_document": 0.06,
    "run_reconciliation": 0.05, "modify_record": 0.04, "failed_login": 0.03,
}


def _business_hour(rng: np.random.Generator) -> tuple[int, int, int]:
    """Horaire d'activite : concentre sur la journee, avec une queue en soiree."""
    draw = rng.random()
    if draw < 0.88:
        hour = int(np.clip(rng.normal(14, 2.8), 7, 20))
    elif draw < 0.97:
        hour = int(rng.integers(20, 23))
    else:
        # 3 % d'activite nocturne legitime : astreintes, cloture, fuseaux.
        hour = int(rng.choice([23, 0, 1, 2]))
    return hour, int(rng.integers(0, 60)), int(rng.integers(0, 60))


def build_audit_logs(employees: pd.DataFrame, transactions: pd.DataFrame,
                     circuit_payment_dates: list[dt.date]) -> pd.DataFrame:
    rng = make_rng("audit")
    active = employees[employees["status"] == "active"]
    staff = active[["employee_id", "entity_id", "country", "department",
                    "authorization_level"]].to_dict("records")

    rows: list[dict] = []

    # --- Activite courante ---------------------------------------------------
    actions = list(_ACTION_WEIGHTS)
    weights = np.array([_ACTION_WEIGHTS[a] for a in actions])
    weights = weights / weights.sum()

    tx_ids = transactions["transaction_id"].to_numpy()
    account_ids = transactions["source_account_id"].drop_duplicates().to_numpy()

    # Les profils conformite et audit consultent structurellement plus de
    # donnees que les autres : c'est leur mission, pas un signal.
    def intensity(person: dict) -> float:
        if person["department"] in ("Compliance", "Audit"):
            return 3.6
        if person["department"] in ("Finance", "Treasury"):
            return 1.8
        return 1.0

    weights_staff = np.array([intensity(p) for p in staff], dtype=float)
    weights_staff = weights_staff / weights_staff.sum()

    n_noise = config.N_AUDIT_NOISE_LOGS
    picks = rng.choice(len(staff), size=n_noise, p=weights_staff)
    for pick in picks:
        person = staff[int(pick)]
        day = ALL_BUSINESS_DAYS[int(rng.integers(0, len(ALL_BUSINESS_DAYS)))]
        hour, minute, second = _business_hour(rng)
        action = str(rng.choice(actions, p=weights))
        resource_type = str(rng.choice(_RESOURCE_TYPES))
        if action in ("view_transaction",):
            resource_type = "transaction"
            resource_id = str(tx_ids[int(rng.integers(0, len(tx_ids)))])
        elif action in ("view_account", "run_reconciliation"):
            resource_type = "account"
            resource_id = str(account_ids[int(rng.integers(0, len(account_ids)))])
        else:
            resource_id = None

        # 14 % d'acces depuis une autre region : deplacements professionnels.
        if rng.random() < 0.14:
            ip_region = str(rng.choice(config.IP_REGIONS))
        else:
            ip_region = person["country"]

        rows.append({
            "employee_id": person["employee_id"],
            "timestamp": dt.datetime.combine(day, dt.time(hour, minute, second)),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "entity_id": person["entity_id"],
            "result": "failure" if action == "failed_login" else (
                "success" if rng.random() > 0.012 else "denied"),
            "ip_region": ip_region,
        })

    # --- Approbations tracees ------------------------------------------------
    approvals = transactions[
        (transactions["authorized_by"].str.startswith("EMP-"))
        & (transactions["amount_eur"] >= config.AUTO_APPROVAL_THRESHOLD_EUR)
    ]
    if len(approvals) > 18_000:
        approvals = approvals.sample(18_000, random_state=config.SEED)
    for row in approvals.itertuples():
        hour, minute, second = _business_hour(rng)
        rows.append({
            "employee_id": row.authorized_by,
            "timestamp": dt.datetime.combine(row.transaction_date,
                                             dt.time(hour, minute, second)),
            "action": "approve_transaction",
            "resource_type": "transaction",
            "resource_id": row.transaction_id,
            "entity_id": row.source_entity_id,
            "result": "success",
            "ip_region": "FR" if row.authorized_by == "EMP-0002" else None,
        })

    # --- Profils de deplacement soutenu --------------------------------------
    # Quelques collaborateurs cumulent horaires tardifs et region IP etrangere
    # pour des raisons parfaitement banales : suivi de chantier, decalage
    # horaire, astreinte de cloture. Sans eux, un simple tri par nombre
    # d'acces nocturnes hors zone designerait un seul employe.
    travellers = active[
        (active["department"].isin(["Investments", "Operations", "Finance"]))
        & (active["authorization_level"] >= 3)
        & (active["employee_id"] != "EMP-0004")
    ]["employee_id"].tolist()
    if travellers:
        chosen = rng.choice(travellers, size=min(4, len(travellers)), replace=False)
        for person_id in chosen:
            home = employees.loc[employees["employee_id"] == person_id, "country"].iloc[0]
            elsewhere = [r for r in config.IP_REGIONS if r != home]
            region = str(rng.choice(elsewhere))
            for _ in range(int(rng.integers(9, 17))):
                day = ALL_BUSINESS_DAYS[int(rng.integers(0, len(ALL_BUSINESS_DAYS)))]
                hour = int(rng.choice([23, 0, 1, 2]))
                rows.append({
                    "employee_id": person_id,
                    "timestamp": dt.datetime.combine(
                        day, dt.time(hour, int(rng.integers(0, 60)), int(rng.integers(0, 60)))),
                    "action": str(rng.choice(
                        ["view_transaction", "view_report", "run_reconciliation",
                         "view_account", "login"])),
                    "resource_type": "transaction",
                    "resource_id": str(tx_ids[int(rng.integers(0, len(tx_ids)))]),
                    "entity_id": employees.loc[
                        employees["employee_id"] == person_id, "entity_id"].iloc[0],
                    "result": "success",
                    "ip_region": region,
                })

    # --- Sequence liee au circuit -------------------------------------------
    # 21 des 24 paiements sont precedes d'un acces de rapprochement bancaire
    # nocturne, depuis une region qui ne correspond pas au rattachement.
    selected = rng.choice(len(circuit_payment_dates), size=21, replace=False)
    for pick in selected:
        payment_day = circuit_payment_dates[int(pick)]
        lead = int(rng.choice([1, 2]))
        day = payment_day - dt.timedelta(days=lead)
        hour = int(rng.choice([23, 0, 1, 2]))
        if hour == 23:
            log_day = day
        else:
            log_day = day + dt.timedelta(days=1)
        rows.append({
            "employee_id": "EMP-0004",
            "timestamp": dt.datetime.combine(
                log_day, dt.time(hour, int(rng.integers(0, 60)), int(rng.integers(0, 60)))),
            "action": "run_reconciliation",
            "resource_type": "account",
            "resource_id": str(account_ids[int(rng.integers(0, len(account_ids)))]),
            "entity_id": "ENT-0002",
            "result": "success",
            "ip_region": "AE",
        })

    # --- Trace de la falsification et de son approbation --------------------
    from .scenario import RECLASSIFICATION_DATE

    rows.append({
        "employee_id": "EMP-0003",
        "timestamp": dt.datetime.combine(RECLASSIFICATION_DATE, dt.time(21, 47, 12)),
        "action": "modify_record",
        "resource_type": "investment",
        "resource_id": "INV-0001",
        "entity_id": "ENT-0002",
        "result": "success",
        "ip_region": "CH",
    })
    rows.append({
        "employee_id": "EMP-0003",
        "timestamp": dt.datetime.combine(RECLASSIFICATION_DATE, dt.time(22, 3, 55)),
        "action": "export_data",
        "resource_type": "report",
        "resource_id": "RPT-Q3-2024-INV",
        "entity_id": "ENT-0002",
        "result": "success",
        "ip_region": "CH",
    })
    # Le dirigeant approuve le reclassement sans avoir consulte les pieces
    # sources : aucun `view_report` a son nom sur cette ressource.
    rows.append({
        "employee_id": "EMP-0001",
        "timestamp": dt.datetime.combine(RECLASSIFICATION_DATE, dt.time(9, 12, 8)),
        "action": "approve_transaction",
        "resource_type": "investment",
        "resource_id": "INV-0001",
        "entity_id": "ENT-0001",
        "result": "success",
        "ip_region": "FR",
    })

    logs = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    logs.insert(0, "log_id", [log_id(i + 1) for i in range(len(logs))])
    return logs
