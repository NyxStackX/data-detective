"""Generation du portefeuille d'investissements.

La table sert deux objectifs : donner au groupe une activite d'investissement
credible, et porter l'anomalie de rendement de la composante A. L'anomalie
n'est pas un montant hors norme mais un rendement *trop bon* au regard de sa
cohorte sectorielle et geographique - detectable uniquement par comparaison.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config
from .scenario import (AMOUNT_A, CAPITAL_PARTNERS, CRESCENT, AL_REEM, FALSIFIED_RETURN,
                       MIDDLE_EAST)
from .utils import investment_id, make_rng, to_eur, currency_of

SECTORS = ["luxury_real_estate", "hospitality", "private_aviation", "yachting",
           "jewellery", "art_collections", "fine_dining", "technology", "infrastructure"]

# Rendements attendus moyens par secteur (annualises).
SECTOR_RETURN = {
    "luxury_real_estate": 0.085, "hospitality": 0.072, "private_aviation": 0.061,
    "yachting": 0.048, "jewellery": 0.094, "art_collections": 0.112,
    "fine_dining": 0.055, "technology": 0.135, "infrastructure": 0.058,
}

# Choc sectoriel : le marche residentiel haut de gamme de Dubai se retourne au
# second semestre 2024. Toutes les lignes de la cohorte en portent la trace.
DUBAI_SHOCK_SECTOR = "luxury_real_estate"
DUBAI_SHOCK_COUNTRY = "AE"


def build_investments(entities: pd.DataFrame) -> pd.DataFrame:
    rng = make_rng("investments")
    investors = entities[
        entities["_category"] == "internal"
    ]
    investors = investors[
        investors["entity_type"].isin(["holding", "investment_company", "subsidiary"])
    ].to_dict("records")
    targets = entities[entities["_category"].isin(["client", "financial", "supplier"])]
    targets = targets.to_dict("records")

    rows: list[dict] = []
    index = 1

    # --- Ligne du scenario : la participation qui s'effondre -----------------
    rows.append({
        "investment_id": investment_id(index),
        "entity_id": MIDDLE_EAST,
        "investment_date": dt.date(2024, 2, 15),
        "target_entity_id": CRESCENT,
        "amount": round(AMOUNT_A / 0.2467, 2),
        "currency": "AED",
        "amount_eur": AMOUNT_A,
        "sector": DUBAI_SHOCK_SECTOR,
        "expected_return": 0.115,
        "actual_return": FALSIFIED_RETURN,
        "maturity_date": dt.date(2029, 2, 15),
        "status": "active",
    })
    index += 1

    # --- Cohorte de comparaison : meme secteur, meme pays, meme annee -------
    cohort = [
        (dt.date(2024, 1, 22), 4_800_000.0, -0.244, "impaired"),
        (dt.date(2024, 3, 8), 2_650_000.0, -0.301, "impaired"),
        (dt.date(2024, 4, 17), 7_200_000.0, -0.187, "impaired"),
        (dt.date(2024, 5, 29), 3_400_000.0, -0.352, "written_off"),
        (dt.date(2024, 6, 11), 5_950_000.0, -0.208, "impaired"),
        (dt.date(2024, 8, 5), 1_900_000.0, -0.279, "impaired"),
        (dt.date(2024, 9, 30), 6_100_000.0, -0.226, "impaired"),
        (dt.date(2023, 11, 14), 8_300_000.0, -0.163, "impaired"),
    ]
    for day, amount_eur, actual, status in cohort:
        target = targets[int(rng.integers(0, len(targets)))]
        rows.append({
            "investment_id": investment_id(index),
            "entity_id": str(rng.choice([MIDDLE_EAST, CAPITAL_PARTNERS])),
            "investment_date": day,
            "target_entity_id": target["entity_id"],
            "amount": round(amount_eur / 0.2467, 2),
            "currency": "AED",
            "amount_eur": amount_eur,
            "sector": DUBAI_SHOCK_SECTOR,
            "expected_return": round(float(rng.uniform(0.09, 0.13)), 4),
            "actual_return": actual,
            "maturity_date": day + dt.timedelta(days=int(rng.integers(1100, 2200))),
            "status": status,
        })
        index += 1

    # --- Fausse piste FP1 : l'acquisition hoteliere d'Abu Dhabi -------------
    rows.append({
        "investment_id": investment_id(index),
        "entity_id": MIDDLE_EAST,
        "investment_date": dt.date(2025, 3, 12),
        "target_entity_id": AL_REEM,
        "amount": round(12_400_000.0 / 0.2467, 2),
        "currency": "AED",
        "amount_eur": 12_400_000.0,
        "sector": "hospitality",
        "expected_return": 0.068,
        "actual_return": 0.061,
        "maturity_date": dt.date(2032, 3, 12),
        "status": "active",
    })
    index += 1

    # --- Portefeuille courant ----------------------------------------------
    while index <= config.N_INVESTMENTS:
        investor = investors[int(rng.integers(0, len(investors)))]
        target = targets[int(rng.integers(0, len(targets)))]
        sector = str(rng.choice(SECTORS))
        country = target["country"]
        currency = currency_of(country)

        day = config.PERIOD_START - dt.timedelta(days=int(rng.integers(0, 1500)))
        if rng.random() < 0.55:
            day = config.PERIOD_START + dt.timedelta(
                days=int(rng.integers(0, (config.PERIOD_END - config.PERIOD_START).days)))

        amount_eur = float(np.exp(rng.normal(np.log(1_900_000), 0.95)))
        expected = SECTOR_RETURN[sector] * float(rng.normal(1.0, 0.18))

        # Le realise s'ecarte de l'attendu ; le choc emirati s'applique aux
        # lignes concernees, ce qui rend la cohorte de comparaison credible.
        noise = float(rng.normal(0.0, 0.055))
        actual = expected + noise
        if sector == DUBAI_SHOCK_SECTOR and country == DUBAI_SHOCK_COUNTRY \
                and day >= dt.date(2023, 10, 1):
            actual = float(rng.uniform(-0.34, -0.16))

        matured = day + dt.timedelta(days=int(rng.integers(900, 3000)))
        if matured < config.PERIOD_END:
            status = "closed" if actual >= 0 else "written_off"
        elif actual < -0.12:
            status = "impaired"
        else:
            status = "active"

        rows.append({
            "investment_id": investment_id(index),
            "entity_id": investor["entity_id"],
            "investment_date": day,
            "target_entity_id": target["entity_id"],
            "amount": round(amount_eur / (to_eur(1.0, currency, max(day, config.PERIOD_START))
                                          or 1.0), 2),
            "currency": currency,
            "amount_eur": round(amount_eur, 2),
            "sector": sector,
            "expected_return": round(expected, 4),
            "actual_return": round(actual, 4),
            "maturity_date": matured,
            "status": status,
        })
        index += 1

    return pd.DataFrame(rows)
