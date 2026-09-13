"""Utilitaires partages par les modules de generation.

Contient le calendrier ouvre, la table de change deterministe et les
constructeurs d'identifiants. Aucune logique metier liee a l'enquete ici.
"""

from __future__ import annotations

import datetime as dt
import hashlib

import numpy as np

from . import config


# --------------------------------------------------------------------------
# Generateur aleatoire
# --------------------------------------------------------------------------


def make_rng(stream: str) -> np.random.Generator:
    """Retourne un generateur independant mais deterministe par flux.

    Chaque module de generation utilise son propre flux nomme. Cela permet de
    modifier la volumetrie d'une table sans decaler les tirages des autres,
    ce qui garde le dataset stable entre deux evolutions du generateur.
    """
    digest = hashlib.sha256(f"{config.SEED}:{stream}".encode()).digest()
    seed = int.from_bytes(digest[:8], "big")
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------
# Calendrier
# --------------------------------------------------------------------------

_QUARTER_ENDS = [
    dt.date(y, m, d)
    for y in (2024, 2025)
    for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))
]

# Jours feries approximes (fermeture bancaire commune aux places couvertes).
_HOLIDAYS = {
    dt.date(2024, 1, 1), dt.date(2024, 3, 29), dt.date(2024, 4, 1),
    dt.date(2024, 5, 1), dt.date(2024, 12, 25), dt.date(2024, 12, 26),
    dt.date(2025, 1, 1), dt.date(2025, 4, 18), dt.date(2025, 4, 21),
    dt.date(2025, 5, 1), dt.date(2025, 12, 25), dt.date(2025, 12, 26),
}


def is_business_day(day: dt.date) -> bool:
    return day.weekday() < 5 and day not in _HOLIDAYS


def business_days(start: dt.date, end: dt.date) -> list[dt.date]:
    days: list[dt.date] = []
    current = start
    while current <= end:
        if is_business_day(current):
            days.append(current)
        current += dt.timedelta(days=1)
    return days


ALL_BUSINESS_DAYS: list[dt.date] = business_days(config.PERIOD_START, config.PERIOD_END)


def previous_business_day(day: dt.date) -> dt.date:
    current = day
    while not is_business_day(current):
        current -= dt.timedelta(days=1)
    return current


def quarter_end(day: dt.date) -> dt.date:
    """Dernier jour du trimestre contenant `day`."""
    quarter = (day.month - 1) // 3
    month, last = ((3, 31), (6, 30), (9, 30), (12, 31))[quarter]
    return dt.date(day.year, month, last)


def days_to_quarter_end(day: dt.date) -> int:
    return (quarter_end(day) - day).days


def business_days_before_quarter_end(qe: dt.date, n: int) -> list[dt.date]:
    """Les `n` derniers jours ouvres d'un trimestre, du plus ancien au plus recent."""
    days: list[dt.date] = []
    current = qe
    while len(days) < n:
        if is_business_day(current):
            days.append(current)
        current -= dt.timedelta(days=1)
    return sorted(days)


QUARTER_ENDS: list[dt.date] = list(_QUARTER_ENDS)


# --------------------------------------------------------------------------
# Change
# --------------------------------------------------------------------------

def _build_fx_table() -> dict[tuple[str, int, int], float]:
    """Table de change mensuelle : (devise, annee, mois) -> taux vers EUR.

    La derive est un bruit gaussien cumule, tire une seule fois a partir de la
    seed. Les taux restent dans une bande realiste sur deux ans.
    """
    rng = make_rng("fx")
    table: dict[tuple[str, int, int], float] = {}
    months = [(y, m) for y in (2024, 2025) for m in range(1, 13)]
    for currency, base in config.FX_BASE.items():
        vol = config.FX_MONTHLY_VOLATILITY[currency]
        rate = base
        for year, month in months:
            if vol:
                rate *= float(np.exp(rng.normal(0.0, vol)))
                rate = float(np.clip(rate, base * 0.90, base * 1.10))
            table[(currency, year, month)] = round(rate, 6)
    return table


FX_TABLE: dict[tuple[str, int, int], float] = _build_fx_table()


def fx_rate(currency: str, day: dt.date) -> float:
    """Taux de change mensuel. Les dates hors periode sont ramenees aux bornes."""
    if currency == "EUR":
        return 1.0
    key = (currency, day.year, day.month)
    if key in FX_TABLE:
        return FX_TABLE[key]
    if day < config.PERIOD_START:
        return FX_TABLE[(currency, config.PERIOD_START.year, config.PERIOD_START.month)]
    return FX_TABLE[(currency, config.PERIOD_END.year, config.PERIOD_END.month)]


def to_eur(amount: float, currency: str, day: dt.date) -> float:
    return round(amount * fx_rate(currency, day), 2)


def from_eur(amount_eur: float, currency: str, day: dt.date) -> float:
    return round(amount_eur / fx_rate(currency, day), 2)


def currency_of(country: str) -> str:
    return config.COUNTRIES[country]["currency"]


# --------------------------------------------------------------------------
# Identifiants
# --------------------------------------------------------------------------

def entity_id(index: int) -> str:
    return f"ENT-{index:04d}"


def employee_id(index: int) -> str:
    return f"EMP-{index:04d}"


def account_id(index: int) -> str:
    return f"ACC-{index:04d}"


def transaction_id(index: int) -> str:
    return f"TRX-{index:06d}"


def investment_id(index: int) -> str:
    return f"INV-{index:04d}"


def company_id(index: int) -> str:
    return f"CMP-{index:04d}"


def officer_id(index: int) -> str:
    return f"OFF-{index:04d}"


def log_id(index: int) -> str:
    return f"LOG-{index:06d}"


def relationship_id(index: int) -> str:
    return f"REL-{index:04d}"


def bank_reference(rng: np.random.Generator, day: dt.date) -> str:
    """Reference bancaire au format commun a toutes les transactions."""
    return f"{day.strftime('%y%m')}-{rng.integers(100000, 999999)}"
