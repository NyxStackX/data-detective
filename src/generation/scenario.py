"""Injection du scenario de CASE #001.

Ce module encode la verite de l'enquete sous forme de flux financiers. Il est
volontairement le seul endroit du generateur ou cette verite existe : les
transactions produites ici passent par les memes constructeurs que le socle
legitime et ne portent aucun marqueur exploitable.

Decomposition des 47,8 M EUR :
  A  31,2 M  perte d'investissement reelle, dissimulee par un rendement falsifie
  B  13,5 M  flux circulaires de comblement, sortis puis revenus dans le groupe
  C   3,1 M  detournement personnel

Les montants et les dates ci-dessous sont la source de verite ; `case_truth.json`
en est derive, jamais l'inverse.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from . import config
from .transactions import _make_row
from .utils import (business_days_before_quarter_end, days_to_quarter_end,
                    from_eur, make_rng, previous_business_day)

# --------------------------------------------------------------------------
# Constantes du scenario
# --------------------------------------------------------------------------

AMOUNT_A = 31_200_000.0   # perte dissimulee
AMOUNT_B = 13_500_000.0   # flux circulaires
AMOUNT_C = 3_100_000.0    # detournement
TOTAL_CASE = AMOUNT_A + AMOUNT_B + AMOUNT_C  # 47 800 000

AURUM = "ENT-0012"
HELVETIA = "ENT-0013"
CRESCENT = "ENT-0014"
ZEPHYR = "ENT-0015"
AL_REEM = "ENT-0016"
SENTINEL = "ENT-0017"

CAPITAL_PARTNERS = "ENT-0002"
REAL_ESTATE = "ENT-0003"
HOSPITALITY = "ENT-0004"
MAISON = "ENT-0005"
MARINE = "ENT-0007"
MIDDLE_EAST = "ENT-0009"
USA = "ENT-0010"

VASSEUR = "EMP-0004"     # Treasury Manager, saisit les paiements
DAUTRAY = "EMP-0003"     # Investment Director, approuve

# Repartition des 24 paiements du circuit entre les trois filiales payeuses.
PAYER_SPLIT = {HOSPITALITY: 9, REAL_ESTATE: 8, MAISON: 7}

# Trimestres concernes : du T4 2024 au T3 2025. Les paiements cessent
# brutalement apres septembre 2025, lorsque le rapprochement bancaire
# automatique est mis en service.
SCENARIO_QUARTER_ENDS = [
    dt.date(2024, 12, 31),
    dt.date(2025, 3, 31),
    dt.date(2025, 6, 30),
    dt.date(2025, 9, 30),
]

INVESTMENT_TRANCHES = [
    (dt.date(2024, 2, 15), 12_500_000.0),
    (dt.date(2024, 4, 23), 11_200_000.0),
    (dt.date(2024, 7, 9), 7_500_000.0),
]

FALSIFIED_RETURN = 0.042
COLLAPSE_DATE = dt.date(2024, 9, 17)
RECLASSIFICATION_DATE = dt.date(2024, 10, 21)
REFINANCING_DATE = dt.date(2024, 11, 1)


def _entity_map(entities) -> dict[str, dict]:
    return {e["entity_id"]: e for e in entities.to_dict("records")}


# --------------------------------------------------------------------------
# Composante A : l'investissement qui s'effondre
# --------------------------------------------------------------------------

def _build_investment_leg(rng, roster, accounts_idx, emap) -> list[dict]:
    rows: list[dict] = []
    for day, amount_eur in INVESTMENT_TRANCHES:
        # Dotation du vehicule de Dubai depuis Geneve.
        rows.append(_make_row(
            rng, roster, accounts_idx, day,
            source=emap[CAPITAL_PARTNERS], destination=emap[MIDDLE_EAST],
            amount=from_eur(amount_eur, "CHF", day), currency="CHF",
            transaction_type="internal_transfer",
            description="Capital allocation - development programme",
            source_account_type="investment", destination_account_type="treasury",
            created_by=VASSEUR, authorized_by=DAUTRAY, status="completed",
        ))
        # Appel de fonds du projet.
        call_day = previous_business_day(day + dt.timedelta(days=4))
        rows.append(_make_row(
            rng, roster, accounts_idx, call_day,
            source=emap[MIDDLE_EAST], destination=emap[CRESCENT],
            amount=from_eur(amount_eur, "AED", call_day), currency="AED",
            transaction_type="investment",
            description="Development programme - capital call",
            created_by=VASSEUR, authorized_by="EMP-0002", status="completed",
        ))
    return rows


# --------------------------------------------------------------------------
# Composantes B et C : le circuit Aurum
# --------------------------------------------------------------------------

def _circuit_amounts(rng) -> list[float]:
    """24 montants en EUR, tous sous le seuil de double approbation.

    Tires uniformement dans une bande etroite situee juste sous 750 000 EUR,
    puis renormalises pour que la somme corresponde exactement a B + C.
    """
    target = AMOUNT_B + AMOUNT_C
    raw = rng.uniform(668_000, 742_000, size=24)
    scaled = raw * (target / raw.sum())
    scaled = np.clip(scaled, 664_000, 747_000)
    # Ajustement final sur le dernier montant pour retomber au centime pres.
    scaled[-1] += target - scaled.sum()
    return [round(float(x), 2) for x in scaled]


def _build_circuit_inflow(rng, roster, accounts_idx, emap) -> tuple[list[dict], list[dict]]:
    """Les 24 paiements des filiales vers Aurum."""
    amounts = _circuit_amounts(rng)
    schedule: list[tuple[dt.date, str]] = []

    payers = []
    for payer, count in PAYER_SPLIT.items():
        payers += [payer] * count
    payers = list(rng.permutation(payers))

    per_quarter = [6, 6, 6, 6]
    cursor = 0
    for quarter_end, count in zip(SCENARIO_QUARTER_ENDS, per_quarter):
        window = business_days_before_quarter_end(quarter_end, 5)
        for _ in range(count):
            day = window[int(rng.integers(0, len(window)))]
            schedule.append((day, payers[cursor]))
            cursor += 1

    schedule.sort(key=lambda x: x[0])

    rows: list[dict] = []
    detail: list[dict] = []
    for (day, payer), amount_eur in zip(schedule, amounts):
        currency = "GBP" if payer == REAL_ESTATE else "EUR"
        row = _make_row(
            rng, roster, accounts_idx, day,
            source=emap[payer], destination=emap[AURUM],
            amount=from_eur(amount_eur, currency, day), currency=currency,
            transaction_type="service_payment",
            description=str(rng.choice(config.ADVISORY_DESCRIPTIONS)),
            source_account_type="operating",
            created_by=VASSEUR, authorized_by=DAUTRAY, status="completed",
        )
        rows.append(row)
        detail.append({
            "date": day.isoformat(),
            "payer_entity_id": payer,
            "amount_eur": row["amount_eur"],
            "currency": currency,
            "days_to_quarter_end": days_to_quarter_end(day),
        })
    return rows, detail


def _build_circuit_outflow(rng, roster, accounts_idx, emap) -> tuple[list[dict], list[dict]]:
    """Reversements d'Aurum : retour dans le groupe (B) et sortie reelle (C)."""
    rows: list[dict] = []
    rows_c: list[dict] = []

    # B : 14 virements vers le relais suisse, puis retour a Geneve sous
    # l'apparence de remboursements d'une facilite structuree. Aucun
    # decaissement de pret correspondant n'existe dans le dataset.
    n_b = 14
    b_amounts = rng.uniform(0.85, 1.15, size=n_b)
    b_amounts = b_amounts / b_amounts.sum() * AMOUNT_B
    start = dt.date(2025, 1, 14)
    for k, amount_eur in enumerate(b_amounts):
        day = previous_business_day(start + dt.timedelta(days=int(22 * k + rng.integers(0, 7))))
        if day > config.PERIOD_END:
            day = previous_business_day(config.PERIOD_END)
        rows.append(_make_row(
            rng, roster, accounts_idx, day,
            source=emap[AURUM], destination=emap[HELVETIA],
            amount=round(float(amount_eur), 2), currency="EUR",
            transaction_type="transfer",
            description="Mandate settlement - structured programme",
            created_by="EXTERNAL", authorized_by="EXTERNAL", status="completed",
        ))
        back_day = previous_business_day(day + dt.timedelta(days=int(rng.integers(4, 12))))
        if back_day > config.PERIOD_END:
            back_day = previous_business_day(config.PERIOD_END)
        rows.append(_make_row(
            rng, roster, accounts_idx, back_day,
            source=emap[HELVETIA], destination=emap[CAPITAL_PARTNERS],
            amount=from_eur(float(amount_eur) * 0.998, "CHF", back_day), currency="CHF",
            transaction_type="repayment",
            description="Facility repayment - tranche settlement",
            destination_account_type="investment",
            created_by=VASSEUR, authorized_by=DAUTRAY, status="completed",
        ))

    # C : 6 honoraires de succes vers une structure de nominees a Singapour.
    n_c = 6
    c_amounts = rng.uniform(0.8, 1.2, size=n_c)
    c_amounts = c_amounts / c_amounts.sum() * AMOUNT_C
    c_start = dt.date(2025, 2, 6)
    for k, amount_eur in enumerate(c_amounts):
        day = previous_business_day(c_start + dt.timedelta(days=int(46 * k + rng.integers(0, 9))))
        if day > config.PERIOD_END:
            day = previous_business_day(config.PERIOD_END)
        rows_c.append(_make_row(
            rng, roster, accounts_idx, day,
            source=emap[AURUM], destination=emap[SENTINEL],
            amount=round(float(amount_eur), 2), currency="EUR",
            transaction_type="transfer",
            description="Success fee - advisory mandate",
            created_by="EXTERNAL", authorized_by="EXTERNAL", status="completed",
        ))
    return rows, rows_c


def _build_helvetia_noise(rng, roster, accounts_idx, emap, entities) -> list[dict]:
    """Activite legitime du relais suisse.

    Sans ce bruit, Helvetia serait une coquille evidente. Avec lui, seule
    l'analyse du ratio entrant/sortant par contrepartie revele l'anomalie.
    """
    rows: list[dict] = []
    others = entities[entities["_category"].isin(["client", "supplier", "financial"])]
    others = others[others["entity_id"] != HELVETIA].to_dict("records")
    for _ in range(70):
        other = others[int(rng.integers(0, len(others)))]
        day = config.PERIOD_START + dt.timedelta(days=int(rng.integers(6, 720)))
        day = previous_business_day(day)
        inbound = rng.random() < 0.62
        source, destination = ((other, emap[HELVETIA]) if inbound
                               else (emap[HELVETIA], other))
        rows.append(_make_row(
            rng, roster, accounts_idx, day,
            source=source, destination=destination,
            amount=float(np.exp(rng.normal(np.log(46_000), 0.8))),
            transaction_type="transfer",
            description="Trade finance settlement",
            created_by="EXTERNAL", authorized_by="EXTERNAL",
        ))
    return rows


# --------------------------------------------------------------------------
# Fausses pistes
# --------------------------------------------------------------------------

def _build_false_lead_al_reem(rng, roster, accounts_idx, emap) -> list[dict]:
    """FP1 : acquisition hoteliere de 12,4 M EUR a Abu Dhabi, parfaitement reguliere."""
    day = dt.date(2025, 3, 12)
    rows = [_make_row(
        rng, roster, accounts_idx, day,
        source=emap[MIDDLE_EAST], destination=emap[AL_REEM],
        amount=from_eur(12_400_000.0, "AED", day), currency="AED",
        transaction_type="acquisition",
        description="Hotel asset acquisition - final settlement",
        created_by="EMP-0004", authorized_by="EMP-0002", status="completed",
    )]
    # Acompte verse deux mois plus tot : la sequence est documentee.
    deposit_day = dt.date(2025, 1, 20)
    rows.append(_make_row(
        rng, roster, accounts_idx, deposit_day,
        source=emap[MIDDLE_EAST], destination=emap[AL_REEM],
        amount=from_eur(1_240_000.0, "AED", deposit_day), currency="AED",
        transaction_type="acquisition",
        description="Hotel asset acquisition - deposit",
        created_by="EMP-0004", authorized_by="EMP-0002", status="completed",
    ))
    return rows


def _build_false_lead_zephyr(rng, roster, accounts_idx, emap, entities) -> list[dict]:
    """FP3 : refit d'un yacht, 6,8 M EUR echelonnes selon un calendrier de chantier."""
    rows: list[dict] = []
    milestones = [
        (dt.date(2024, 3, 6), 0.30), (dt.date(2024, 5, 15), 0.08),
        (dt.date(2024, 7, 24), 0.08), (dt.date(2024, 10, 2), 0.08),
        (dt.date(2024, 12, 11), 0.08), (dt.date(2025, 2, 19), 0.08),
        (dt.date(2025, 4, 30), 0.08), (dt.date(2025, 7, 9), 0.08),
        (dt.date(2025, 9, 17), 0.14),
    ]
    total = 6_800_000.0
    for day, share in milestones:
        rows.append(_make_row(
            rng, roster, accounts_idx, previous_business_day(day),
            source=emap[MARINE], destination=emap[ZEPHYR],
            amount=round(total * share, 2), currency="EUR",
            transaction_type="payment",
            description="Refit programme - milestone invoice",
            status="completed",
        ))
    # Zephyr a une activite propre : ses sorties sont diversifiees, ce qui la
    # distingue d'une societe de facade.
    suppliers = entities[entities["_category"] == "supplier"].to_dict("records")
    for _ in range(58):
        supplier = suppliers[int(rng.integers(0, len(suppliers)))]
        day = previous_business_day(
            config.PERIOD_START + dt.timedelta(days=int(rng.integers(70, 700))))
        rows.append(_make_row(
            rng, roster, accounts_idx, day,
            source=emap[ZEPHYR], destination=supplier,
            amount=float(np.exp(rng.normal(np.log(38_000), 0.7))), currency="EUR",
            transaction_type="payment",
            description="Subcontracting - refit works",
            created_by="EXTERNAL", authorized_by="EXTERNAL",
        ))
    return rows


def _build_false_lead_erp(rng, roster, accounts_idx, emap, entities) -> list[dict]:
    """FP5 : annulations en serie a Milan, dues a une migration d'ERP.

    Chaque annulation est suivie le jour ouvre suivant d'une operation
    identique portant une nouvelle reference bancaire. Le phenomene s'arrete
    net a la fin de la migration.
    """
    rows: list[dict] = []
    suppliers = entities[entities["_category"] == "supplier"].to_dict("records")
    window_start = dt.date(2024, 3, 4)
    window_days = (dt.date(2024, 7, 26) - window_start).days
    descriptions = config.SUPPLIER_DESCRIPTIONS["hospitality"]

    for _ in range(180):
        supplier = suppliers[int(rng.integers(0, len(suppliers)))]
        day = previous_business_day(window_start + dt.timedelta(
            days=int(rng.integers(0, window_days))))
        amount = float(np.exp(rng.normal(np.log(14_000), 0.75)))
        description = str(rng.choice(descriptions))
        cancelled = _make_row(
            rng, roster, accounts_idx, day,
            source=emap[HOSPITALITY], destination=supplier,
            amount=amount, currency="EUR",
            transaction_type="payment", description=description,
            status="cancelled",
        )
        rows.append(cancelled)
        retry_day = previous_business_day(day + dt.timedelta(days=3))
        retry = _make_row(
            rng, roster, accounts_idx, retry_day,
            source=emap[HOSPITALITY], destination=supplier,
            amount=amount, currency="EUR",
            transaction_type="payment", description=description,
            status="completed",
            created_by=cancelled["created_by"], authorized_by=cancelled["authorized_by"],
        )
        rows.append(retry)
    return rows


def _build_false_lead_repayments(rng, roster, accounts_idx, emap) -> list[dict]:
    """FP6 : sequence dense de remboursements par l'entite americaine.

    Refinancement documente : le decaissement initial figure dans les donnees,
    ce qui distingue cette serie des retours du circuit.
    """
    rows: list[dict] = []
    principal = 9_600_000.0
    start = dt.date(2025, 1, 9)
    rows.append(_make_row(
        rng, roster, accounts_idx, start,
        source=emap[CAPITAL_PARTNERS], destination=emap[USA],
        amount=from_eur(principal, "CHF", start), currency="CHF",
        transaction_type="loan",
        description="Refinancing facility - drawdown",
        source_account_type="treasury", destination_account_type="treasury",
        authorized_by="EMP-0002",
    ))
    for k in range(1, 25):
        day = previous_business_day(start + dt.timedelta(days=28 * k))
        if day > config.PERIOD_END:
            break
        rows.append(_make_row(
            rng, roster, accounts_idx, day,
            source=emap[USA], destination=emap[CAPITAL_PARTNERS],
            amount=from_eur(principal / 24 * float(rng.normal(1.0, 0.008)), "USD", day),
            currency="USD",
            transaction_type="repayment",
            description="Refinancing facility - instalment",
            source_account_type="treasury", destination_account_type="treasury",
        ))
    return rows


# --------------------------------------------------------------------------
# Point d'entree
# --------------------------------------------------------------------------

def build_scenario(entities, accounts_idx, roster) -> tuple[list[dict], dict]:
    rng = make_rng("scenario")
    emap = _entity_map(entities)

    inflow, inflow_detail = _build_circuit_inflow(rng, roster, accounts_idx, emap)
    outflow_b, outflow_c = _build_circuit_outflow(rng, roster, accounts_idx, emap)

    groups: list[tuple[str, list[dict]]] = [
        ("A_investment_leg", _build_investment_leg(rng, roster, accounts_idx, emap)),
        ("BC_circuit_inflow", inflow),
        ("B_circuit_return", outflow_b),
        ("C_diversion", outflow_c),
        ("noise_helvetia", _build_helvetia_noise(rng, roster, accounts_idx, emap, entities)),
        ("false_lead_al_reem", _build_false_lead_al_reem(rng, roster, accounts_idx, emap)),
        ("false_lead_zephyr",
         _build_false_lead_zephyr(rng, roster, accounts_idx, emap, entities)),
        ("false_lead_erp_migration",
         _build_false_lead_erp(rng, roster, accounts_idx, emap, entities)),
        ("false_lead_us_repayments",
         _build_false_lead_repayments(rng, roster, accounts_idx, emap)),
    ]

    rows: list[dict] = []
    for tag, group in groups:
        for row in group:
            if not row:
                continue
            # Marqueur interne au generateur : retire avant ecriture du CSV.
            row["_tag"] = tag
            rows.append(row)

    truth = {
        "case_id": "CASE-001",
        "case_name": "THE MISSING FORTUNE",
        "total_amount_eur": TOTAL_CASE,
        "components": {
            "A_concealed_investment_loss_eur": AMOUNT_A,
            "B_circular_replenishment_eur": AMOUNT_B,
            "C_personal_diversion_eur": AMOUNT_C,
        },
        "circuit_payments": inflow_detail,
        "dual_approval_threshold_eur": config.DUAL_APPROVAL_THRESHOLD_EUR,
        "circuit_payment_dates": [d["date"] for d in inflow_detail],
    }
    return rows, truth
