"""Generation des comptes bancaires.

Chaque entite du groupe dispose d'un jeu de comptes coherent avec son activite
(exploitation, tresorerie, paie, investissement) et d'eventuels comptes en
devises etrangeres justifies par ses flux. Les contreparties externes ont un
ou deux comptes dans leur juridiction.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from . import config
from .utils import make_rng, account_id, currency_of

_INTERNAL_ACCOUNT_TYPES = ["operating", "treasury", "payroll", "investment", "escrow"]
_EXTERNAL_ACCOUNT_TYPES = ["operating", "business", "settlement"]

# Comptes figes utilises par le scenario.
SCENARIO_ACCOUNTS: list[dict] = [
    {"entity_id": "ENT-0012", "country": "LU", "currency": "EUR", "account_type": "operating",
     "opening_date": dt.date(2023, 3, 21), "bank_name": "Fiduciaire Ardenne SA"},
    {"entity_id": "ENT-0012", "country": "LU", "currency": "EUR", "account_type": "settlement",
     "opening_date": dt.date(2024, 10, 15), "bank_name": "Banque Verlaine"},
    {"entity_id": "ENT-0013", "country": "CH", "currency": "CHF", "account_type": "operating",
     "opening_date": dt.date(2019, 5, 9), "bank_name": "Alpenrand Bank AG"},
    {"entity_id": "ENT-0013", "country": "CH", "currency": "EUR", "account_type": "settlement",
     "opening_date": dt.date(2021, 2, 17), "bank_name": "Zurichsee Privatbank AG"},
    {"entity_id": "ENT-0014", "country": "AE", "currency": "AED", "account_type": "operating",
     "opening_date": dt.date(2021, 9, 14), "bank_name": "Gulf Meridian Bank PJSC"},
    {"entity_id": "ENT-0015", "country": "MC", "currency": "EUR", "account_type": "operating",
     "opening_date": dt.date(2024, 2, 5), "bank_name": "Banque de Roquebrune"},
    {"entity_id": "ENT-0016", "country": "AE", "currency": "AED", "account_type": "operating",
     "opening_date": dt.date(2017, 7, 3), "bank_name": "Al Sadara Commercial Bank"},
    {"entity_id": "ENT-0017", "country": "SG", "currency": "USD", "account_type": "business",
     "opening_date": dt.date(2024, 11, 6), "bank_name": "Southbay Private Trust"},
]


def build_accounts(entities: pd.DataFrame) -> pd.DataFrame:
    rng = make_rng("accounts")
    rows: list[dict] = []
    index = 1

    scenario_entities = {a["entity_id"] for a in SCENARIO_ACCOUNTS}

    for _, ent in entities.iterrows():
        country = ent["country"]
        base_currency = currency_of(country)
        city = ent["city"]

        if ent["_category"] == "internal":
            types = ["operating", "treasury", "payroll"]
            if ent["entity_type"] in ("holding", "investment_company"):
                types.append("investment")
            if rng.random() < 0.3:
                types.append("escrow")
            currencies = [base_currency] * len(types)
            # Comptes en devise etrangere pour les entites exposees a l'international.
            for foreign in ("USD", "GBP", "CHF", "AED"):
                if foreign != base_currency and rng.random() < 0.28:
                    types.append("operating")
                    currencies.append(foreign)
        elif ent["entity_id"] in scenario_entities:
            continue
        else:
            n = int(rng.integers(1, 3))
            types = [str(rng.choice(_EXTERNAL_ACCOUNT_TYPES)) for _ in range(n)]
            currencies = [base_currency] * n

        for account_type, currency in zip(types, currencies):
            banks = config.BANKS[country]
            opening_floor = max(ent["creation_date"], config.HISTORY_START)
            span = (config.PERIOD_START - opening_floor).days
            opening = opening_floor + dt.timedelta(days=int(rng.integers(0, max(span, 1))))

            closing = None
            status = "active"
            # Rotation bancaire normale : quelques comptes sont clotures en
            # cours de periode, y compris chez des contreparties irreprochables.
            if rng.random() < 0.05:
                closing = config.PERIOD_START + dt.timedelta(
                    days=int(rng.integers(120, (config.PERIOD_END - config.PERIOD_START).days))
                )
                status = "closed"

            rows.append({
                "account_id": account_id(index),
                "entity_id": ent["entity_id"],
                "bank_name": str(rng.choice(banks)),
                "country": country,
                "city": city,
                "currency": currency,
                "account_type": account_type,
                "opening_date": opening,
                "closing_date": closing,
                "status": status,
            })
            index += 1

    for item in SCENARIO_ACCOUNTS:
        ent = entities.loc[entities["entity_id"] == item["entity_id"]].iloc[0]
        rows.append({
            "account_id": account_id(index),
            "entity_id": item["entity_id"],
            "bank_name": item["bank_name"],
            "country": item["country"],
            "city": ent["city"],
            "currency": item["currency"],
            "account_type": item["account_type"],
            "opening_date": item["opening_date"],
            "closing_date": None,
            "status": "active",
        })
        index += 1

    return pd.DataFrame(rows)


def account_index(accounts: pd.DataFrame) -> dict[str, list[dict]]:
    """Index comptes par entite, pour tirage rapide pendant la generation."""
    index: dict[str, list[dict]] = {}
    for row in accounts.to_dict("records"):
        index.setdefault(row["entity_id"], []).append(row)
    return index


def pick_account(index: dict[str, list[dict]], entity: str, day: dt.date,
                 currency: str | None = None, account_type: str | None = None,
                 rng=None) -> dict | None:
    """Selectionne un compte ouvert a la date donnee, filtre si demande.

    Les filtres sont degrades plutot qu'appliques strictement : si l'entite n'a
    pas de compte dans la devise demandee, un autre compte est retenu, ce qui
    reproduit le comportement reel d'une tresorerie multidevise.
    """
    candidates = [
        a for a in index.get(entity, [])
        if a["opening_date"] <= day and (a["closing_date"] is None or a["closing_date"] > day)
    ]
    if not candidates:
        return None
    if currency:
        filtered = [a for a in candidates if a["currency"] == currency]
        candidates = filtered or candidates
    if account_type:
        filtered = [a for a in candidates if a["account_type"] == account_type]
        candidates = filtered or candidates
    if rng is not None and len(candidates) > 1:
        return candidates[int(rng.integers(0, len(candidates)))]
    return candidates[0]
