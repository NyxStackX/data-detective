"""Generation du socle de transactions legitimes.

Le principe directeur est qu'aucune transaction n'est tiree isolement : le
generateur construit d'abord des *relations commerciales* (un fournisseur sert
telle filiale a telle frequence pour tel ordre de grandeur), puis deroule ces
relations sur la periode. C'est ce qui produit des habitudes de paiement
stables, condition necessaire pour qu'une rupture d'habitude soit detectable.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config
from .accounts import pick_account
from .utils import (ALL_BUSINESS_DAYS, currency_of, is_business_day, make_rng,
                    previous_business_day, to_eur, bank_reference)

# Coefficients de saisonnalite par industrie et par mois (index 0 = janvier).
# Stables d'une annee sur l'autre : une pointe recurrente n'est pas une anomalie.
SEASONALITY: dict[str, list[float]] = {
    "hospitality":        [0.78, 0.80, 0.92, 1.02, 1.10, 1.26, 1.38, 1.42, 1.08, 0.94, 0.86, 1.24],
    "fine_dining":        [0.82, 0.88, 0.94, 1.00, 1.08, 1.18, 1.24, 1.20, 1.04, 0.98, 0.94, 1.32],
    "jewellery":          [0.72, 0.86, 0.94, 0.96, 1.06, 1.02, 0.94, 0.90, 0.98, 1.08, 1.26, 1.68],
    "private_aviation":   [0.94, 0.92, 0.98, 1.02, 1.08, 1.22, 1.34, 1.30, 1.02, 0.94, 0.88, 1.16],
    "yachting":           [0.68, 0.74, 0.92, 1.10, 1.28, 1.44, 1.48, 1.40, 1.06, 0.82, 0.66, 0.72],
    "luxury_real_estate": [0.96, 0.98, 1.06, 1.04, 1.08, 1.10, 0.92, 0.78, 1.06, 1.10, 1.04, 1.08],
    "art_collections":    [0.86, 0.92, 1.04, 1.02, 1.16, 1.22, 0.84, 0.76, 1.08, 1.18, 1.14, 1.08],
    "investments":        [1.00, 1.00, 1.06, 1.00, 1.00, 1.06, 1.00, 0.94, 1.00, 1.00, 1.00, 1.06],
    "holding":            [1.02, 0.98, 1.06, 1.00, 0.98, 1.04, 0.96, 0.90, 1.02, 1.02, 1.00, 1.08],
}

_FREQUENCIES = {
    "high": 11.0,      # approvisionnement courant : plusieurs fois par semaine
    "weekly": 4.3,
    "biweekly": 2.15,
    "monthly": 1.0,
    "quarterly": 0.34,
}


def _month_factor(industry: str, day: dt.date) -> float:
    return SEASONALITY.get(industry, SEASONALITY["holding"])[day.month - 1]


def _lognormal(rng: np.random.Generator, median: float, sigma: float) -> float:
    return float(median * np.exp(rng.normal(0.0, sigma)))


class Roster:
    """Acces rapide aux employes habilites, par entite et par niveau."""

    def __init__(self, employees: pd.DataFrame) -> None:
        active = employees[employees["status"] == "active"]
        self.by_entity_level: dict[tuple[str, int], list[str]] = {}
        for entity in active["entity_id"].unique():
            subset = active[active["entity_id"] == entity]
            for level in range(1, 6):
                ids = subset[subset["authorization_level"] >= level]["employee_id"].tolist()
                self.by_entity_level[(entity, level)] = ids
        self.creators: dict[str, list[str]] = {}
        for entity in active["entity_id"].unique():
            subset = active[
                (active["entity_id"] == entity)
                & (active["department"].isin(["Finance", "Treasury", "Operations", "Procurement"]))
                & (active["authorization_level"] >= 2)
            ]
            ids = subset["employee_id"].tolist()
            self.creators[entity] = ids or active[
                active["entity_id"] == entity]["employee_id"].tolist()
        # Equipe de tresorerie groupe : elle execute des paiements pour le
        # compte des filiales dans le cadre de la centralisation de tresorerie.
        group_treasury = active[
            (active["entity_id"] == "ENT-0002") & (active["department"] == "Treasury")
        ]
        self.group_treasury: list[str] = group_treasury["employee_id"].tolist()

    def creator(self, rng: np.random.Generator, entity: str) -> str:
        pool = self.creators.get(entity) or ["EMP-0001"]
        return str(rng.choice(pool))

    def approver(self, rng: np.random.Generator, entity: str, amount_eur: float) -> str:
        if amount_eur < config.AUTO_APPROVAL_THRESHOLD_EUR:
            return "SYSTEM_AUTO"
        if amount_eur >= config.CFO_APPROVAL_THRESHOLD_EUR:
            # Regle de gouvernance : au-dela de 1 M EUR, la signature du Group
            # CFO est requise. Sa presence sur une operation n'est donc pas
            # informative en soi.
            return "EMP-0002" if rng.random() < 0.88 else "EMP-0001"
        level = 4 if amount_eur >= 250_000 else 3
        pool = self.by_entity_level.get((entity, level), [])
        if not pool:
            pool = self.by_entity_level.get((entity, 2), [])
        if not pool:
            return "EMP-0002"
        return str(rng.choice(pool))


def _status(rng: np.random.Generator, day: dt.date) -> str:
    # Les operations des dernieres semaines peuvent encore etre en cours.
    if day >= config.PERIOD_END - dt.timedelta(days=12) and rng.random() < 0.35:
        return "pending"
    draw = rng.random()
    if draw < 0.004:
        return "failed"
    if draw < 0.010:
        return "cancelled"
    return "completed"


def _schedule(rng: np.random.Generator, frequency: str, industry: str) -> list[dt.date]:
    """Dates d'execution d'une relation commerciale sur toute la periode."""
    per_month = _FREQUENCIES[frequency]
    days: list[dt.date] = []
    current = config.PERIOD_START
    while current <= config.PERIOD_END:
        expected = per_month * _month_factor(industry, current)
        count = int(rng.poisson(expected))
        month_end = (current.replace(day=28) + dt.timedelta(days=6)).replace(day=1)
        span = (min(month_end, config.PERIOD_END + dt.timedelta(days=1)) - current).days
        if span <= 0:
            break
        for _ in range(count):
            day = current + dt.timedelta(days=int(rng.integers(0, span)))
            if not is_business_day(day):
                day = previous_business_day(day)
            if config.PERIOD_START <= day <= config.PERIOD_END:
                days.append(day)
        current = month_end
    return days


def build_supplier_flows(entities, accounts_idx, roster) -> list[dict]:
    """Paiements fournisseurs : l'essentiel du volume du dataset."""
    rng = make_rng("flow_suppliers")
    internal = entities[entities["_category"] == "internal"].to_dict("records")
    suppliers = entities[entities["_category"] == "supplier"].to_dict("records")
    rows: list[dict] = []

    for buyer in internal:
        n_contracts = int(rng.integers(52, 73))
        chosen = rng.choice(len(suppliers), size=min(n_contracts, len(suppliers)),
                            replace=False)
        for pos in chosen:
            supplier = suppliers[pos]
            frequency = str(rng.choice(list(_FREQUENCIES),
                                       p=[0.22, 0.20, 0.18, 0.30, 0.10]))
            median = float(rng.choice([4_200, 9_500, 18_000, 46_000, 120_000],
                                      p=[0.30, 0.28, 0.22, 0.14, 0.06]))
            sigma = float(rng.uniform(0.38, 0.72))
            descriptions = config.SUPPLIER_DESCRIPTIONS.get(
                buyer["industry"], config.SUPPLIER_DESCRIPTIONS["holding"])

            for day in _schedule(rng, frequency, buyer["industry"]):
                amount_local = _lognormal(rng, median * _month_factor(buyer["industry"], day),
                                          sigma)
                rows.append(_make_row(
                    rng, roster, accounts_idx, day,
                    source=buyer, destination=supplier,
                    amount=amount_local,
                    transaction_type="payment",
                    description=str(rng.choice(descriptions)),
                ))
    return rows


def build_advisory_flows(entities, accounts_idx, roster) -> list[dict]:
    """Prestations immaterielles : conseil, etudes, valorisation.

    Sous-ensemble analytiquement sensible : les montants y sont eleves et la
    contrepartie n'a pas de livrable physique verifiable. C'est dans cette
    population que se dissimulent les paiements du circuit.
    """
    rng = make_rng("flow_advisory")
    internal = entities[entities["_category"] == "internal"].to_dict("records")
    advisors = entities[entities["_category"] == "advisory"].to_dict("records")
    rows: list[dict] = []

    for buyer in internal:
        n_contracts = int(rng.integers(9, 15))
        chosen = rng.choice(len(advisors), size=n_contracts, replace=False)
        for pos in chosen:
            advisor = advisors[pos]
            frequency = str(rng.choice(["monthly", "quarterly"], p=[0.42, 0.58]))
            median = float(rng.choice([65_000, 140_000, 240_000, 380_000],
                                      p=[0.34, 0.32, 0.22, 0.12]))
            for day in _schedule(rng, frequency, "holding"):
                amount_local = _lognormal(rng, median, 0.62)
                rows.append(_make_row(
                    rng, roster, accounts_idx, day,
                    source=buyer, destination=advisor,
                    amount=amount_local,
                    transaction_type="service_payment",
                    description=str(rng.choice(config.ADVISORY_DESCRIPTIONS)),
                ))
    return rows


def build_client_flows(entities, accounts_idx, roster) -> list[dict]:
    """Encaissements clients : chiffre d'affaires du groupe."""
    rng = make_rng("flow_clients")
    internal = entities[entities["_category"] == "internal"].to_dict("records")
    clients = entities[entities["_category"] == "client"].to_dict("records")
    rows: list[dict] = []

    for seller in internal:
        if seller["entity_type"] in ("holding", "investment_company"):
            continue
        n_contracts = int(rng.integers(32, 45))
        chosen = rng.choice(len(clients), size=min(n_contracts, len(clients)), replace=False)
        for pos in chosen:
            client = clients[pos]
            frequency = str(rng.choice(list(_FREQUENCIES),
                                       p=[0.20, 0.24, 0.22, 0.28, 0.06]))
            median = float(rng.choice([12_000, 38_000, 95_000, 260_000],
                                      p=[0.34, 0.32, 0.24, 0.10]))
            for day in _schedule(rng, frequency, seller["industry"]):
                amount_local = _lognormal(rng, median * _month_factor(seller["industry"], day),
                                          0.58)
                rows.append(_make_row(
                    rng, roster, accounts_idx, day,
                    source=client, destination=seller,
                    amount=amount_local,
                    transaction_type="payment",
                    description=str(rng.choice(config.CLIENT_DESCRIPTIONS)),
                    creator_entity=seller["entity_id"],
                ))
    return rows


def build_internal_flows(entities, accounts_idx, roster) -> list[dict]:
    """Transferts intragroupe, paie, dividendes, prets et remboursements."""
    rng = make_rng("flow_internal")
    internal = entities[entities["_category"] == "internal"].to_dict("records")
    by_id = {e["entity_id"]: e for e in internal}
    holding = by_id["ENT-0001"]
    rows: list[dict] = []

    # Paie : un lot mensuel par entite, du compte d'exploitation vers le compte
    # de paie. Le montant suit l'effectif.
    for ent in internal:
        for year in (2024, 2025):
            for month in range(1, 13):
                day = previous_business_day(dt.date(year, month, 26))
                base = ent["_headcount"] * float(rng.normal(7_400, 320))
                if month == 12:
                    base *= 1.9  # primes de fin d'annee
                rows.append(_make_row(
                    rng, roster, accounts_idx, day,
                    source=ent, destination=ent,
                    amount=base,
                    transaction_type="salary",
                    description="Monthly payroll settlement",
                    source_account_type="operating",
                    destination_account_type="payroll",
                ))

    # Transferts de tresorerie entre entites du groupe.
    for ent in internal:
        if ent["entity_id"] == "ENT-0001":
            continue
        schedule = _schedule(rng, "weekly", ent["industry"]) + _schedule(
            rng, "weekly", ent["industry"])
        for day in schedule:
            counterpart = holding if rng.random() < 0.6 else by_id["ENT-0002"]
            source, destination = (ent, counterpart) if rng.random() < 0.7 else (counterpart, ent)
            rows.append(_make_row(
                rng, roster, accounts_idx, day,
                source=source, destination=destination,
                amount=_lognormal(rng, 180_000, 0.85),
                transaction_type="internal_transfer",
                description="Intragroup cash pooling",
                source_account_type="treasury",
                destination_account_type="treasury",
            ))

    # Remontees de dividendes : une fois par an, apres approbation des comptes.
    for ent in internal:
        parent = ent["parent_entity_id"]
        if parent is None or pd.isna(parent):
            continue
        for year in (2024, 2025):
            day = previous_business_day(dt.date(year, 6, 18))
            rows.append(_make_row(
                rng, roster, accounts_idx, day,
                source=ent, destination=by_id[parent],
                amount=_lognormal(rng, 2_400_000, 0.55),
                transaction_type="dividend",
                description="Annual dividend distribution",
                source_account_type="treasury",
                destination_account_type="treasury",
            ))

    # Prets intragroupe et remboursements echelonnes.
    for _ in range(18):
        borrower = internal[int(rng.integers(1, len(internal)))]
        start = config.PERIOD_START + dt.timedelta(days=int(rng.integers(0, 430)))
        start = previous_business_day(start)
        principal = _lognormal(rng, 3_200_000, 0.5)
        rows.append(_make_row(
            rng, roster, accounts_idx, start,
            source=by_id["ENT-0002"], destination=borrower,
            amount=principal,
            transaction_type="loan",
            description="Intragroup facility drawdown",
            source_account_type="treasury",
            destination_account_type="treasury",
        ))
        n_instalments = int(rng.integers(6, 19))
        for k in range(1, n_instalments + 1):
            day = start + dt.timedelta(days=30 * k)
            if day > config.PERIOD_END:
                break
            rows.append(_make_row(
                rng, roster, accounts_idx, previous_business_day(day),
                source=borrower, destination=by_id["ENT-0002"],
                amount=principal / n_instalments * float(rng.normal(1.0, 0.01)),
                transaction_type="repayment",
                description="Intragroup facility repayment",
                source_account_type="treasury",
                destination_account_type="treasury",
            ))

    # Avoirs et remboursements commerciaux.
    external = entities[entities["_category"].isin(["supplier", "client"])].to_dict("records")
    for _ in range(11_500):
        ent = internal[int(rng.integers(0, len(internal)))]
        other = external[int(rng.integers(0, len(external)))]
        day = ALL_BUSINESS_DAYS[int(rng.integers(0, len(ALL_BUSINESS_DAYS)))]
        rows.append(_make_row(
            rng, roster, accounts_idx, day,
            source=ent, destination=other,
            amount=_lognormal(rng, 5_800, 0.7),
            transaction_type="refund",
            description="Commercial credit note settlement",
        ))

    return rows


def _make_row(rng, roster: Roster, accounts_idx, day: dt.date, *, source: dict,
              destination: dict, amount: float, transaction_type: str, description: str,
              source_account_type: str | None = None,
              destination_account_type: str | None = None,
              creator_entity: str | None = None,
              status: str | None = None,
              created_by: str | None = None,
              authorized_by: str | None = None,
              currency: str | None = None) -> dict:
    """Assemble une ligne de transaction coherente avec les referentiels."""
    currency = currency or currency_of(source["country"])
    src_account = pick_account(accounts_idx, source["entity_id"], day, currency,
                               source_account_type, rng)
    dst_account = pick_account(accounts_idx, destination["entity_id"], day, currency,
                               destination_account_type, rng)
    if src_account is None:
        src_account = pick_account(accounts_idx, source["entity_id"], day, None, None, rng)
    if dst_account is None:
        dst_account = pick_account(accounts_idx, destination["entity_id"], day, None, None, rng)
    if src_account is None or dst_account is None:
        return {}
    if src_account["account_id"] == dst_account["account_id"]:
        # Cas des virements internes a une meme entite : il faut deux comptes
        # distincts, sinon l'operation n'a pas de sens comptable.
        alternatives = [
            a for a in accounts_idx.get(destination["entity_id"], [])
            if a["account_id"] != src_account["account_id"]
            and a["opening_date"] <= day
            and (a["closing_date"] is None or a["closing_date"] > day)
        ]
        if not alternatives:
            return {}
        preferred = [a for a in alternatives
                     if a["account_type"] == (destination_account_type or "")]
        pool = preferred or alternatives
        dst_account = pool[int(rng.integers(0, len(pool)))]

    currency = src_account["currency"]
    amount = round(max(amount, 120.0), 2)
    amount_eur = to_eur(amount, currency, day)

    owner = creator_entity or source["entity_id"]
    if created_by is None:
        created_by = roster.creator(rng, owner)
        # Centralisation de tresorerie : une partie des paiements significatifs
        # des filiales est saisie par l'equipe groupe a Geneve.
        if (amount_eur > 100_000 and roster.group_treasury
                and transaction_type in ("payment", "service_payment", "transfer",
                                         "internal_transfer")
                and rng.random() < 0.22):
            created_by = str(rng.choice(roster.group_treasury))
    if authorized_by is None:
        authorized_by = roster.approver(rng, owner, amount_eur)

    return {
        "transaction_date": day,
        "source_account_id": src_account["account_id"],
        "destination_account_id": dst_account["account_id"],
        "source_entity_id": source["entity_id"],
        "destination_entity_id": destination["entity_id"],
        "amount": amount,
        "currency": currency,
        "amount_eur": amount_eur,
        "transaction_type": transaction_type,
        "reference": bank_reference(rng, day),
        "description": description,
        "status": status or _status(rng, day),
        "authorized_by": authorized_by,
        "created_by": created_by,
    }


def build_baseline(entities: pd.DataFrame, accounts_idx, roster: Roster) -> list[dict]:
    rows: list[dict] = []
    rows += build_supplier_flows(entities, accounts_idx, roster)
    rows += build_client_flows(entities, accounts_idx, roster)
    rows += build_advisory_flows(entities, accounts_idx, roster)
    rows += build_internal_flows(entities, accounts_idx, roster)
    return [r for r in rows if r]
