"""Generation du referentiel d'entites, du registre societes et des relations.

Le referentiel est la colonne vertebrale du dataset : toutes les autres tables
pointent vers `entity_id`. Les societes externes sont tirees par categorie
(fournisseur, conseil, client, financier) afin que les flux generes ensuite
restent coherents avec le secteur d'activite de chaque contrepartie.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from . import config
from .utils import make_rng, entity_id, company_id

_PREFIXES = [
    "Ardel", "Belcour", "Calvane", "Dorset", "Ebren", "Falmere", "Grandcourt", "Harlow",
    "Ivrel", "Jorcy", "Kestrel", "Lorval", "Maldon", "Norwell", "Orvieto", "Pentland",
    "Quernay", "Rosswell", "Sablon", "Turenne", "Umbria", "Valmiera", "Westbourne", "Yarrow",
    "Aubisque", "Brancourt", "Cormeille", "Delmare", "Estrel", "Fenwick", "Galtier", "Havreux",
    "Ilvano", "Joubert", "Kaltbrunn", "Lindau", "Merano", "Nordheim", "Ostend", "Perrine",
    "Rivalta", "Serrano", "Talbrook", "Vionnaz", "Wexham", "Zermat",
]

_SUFFIXES = {
    "FR": ["SAS", "SARL", "SA"],
    "CH": ["AG", "SA", "GmbH"],
    "GB": ["Ltd", "LLP", "Holdings Ltd"],
    "IT": ["SpA", "Srl"],
    "MC": ["SAM", "SARL"],
    "AE": ["LLC", "FZE", "DMCC"],
    "US": ["Inc", "LLC", "Corp"],
    "LU": ["S.a r.l.", "SA"],
    "SG": ["Pte Ltd"],
    "BE": ["NV", "SPRL"],
    "ES": ["SL", "SA"],
}

_SUPPLIER_WORDS = ["Supplies", "Industries", "Services", "Works", "Logistics", "Solutions",
                   "Maintenance", "Provisions", "Technic", "Atelier", "Manufacture"]
_ADVISORY_WORDS = ["Advisory", "Consulting", "Partners", "Associates", "Strategy", "Counsel",
                   "Research", "Analytics"]
_CLIENT_WORDS = ["Group", "Ventures", "Estates", "Family Office", "Capital", "Trust",
                 "Investments", "Collection"]
_FINANCIAL_WORDS = ["Finance", "Credit", "Trade Solutions", "Treasury", "Asset Management",
                    "Nominees", "Fiduciary"]

_CATEGORY_WORDS = {
    "supplier": _SUPPLIER_WORDS,
    "advisory": _ADVISORY_WORDS,
    "client": _CLIENT_WORDS,
    "financial": _FINANCIAL_WORDS,
}

_CATEGORY_ENTITY_TYPE = {
    "supplier": "supplier",
    "advisory": "partner",
    "client": "partner",
    "financial": "financial_entity",
}

# Poids geographiques : les contreparties suivent l'implantation du groupe.
_COUNTRY_WEIGHTS = {
    "FR": 0.22, "IT": 0.15, "GB": 0.15, "CH": 0.12, "MC": 0.08,
    "AE": 0.09, "US": 0.09, "ES": 0.04, "BE": 0.03, "LU": 0.02, "SG": 0.01,
}

_INDUSTRIES_BY_CATEGORY = {
    "supplier": ["hospitality", "luxury_real_estate", "private_aviation", "yachting",
                 "jewellery", "art_collections", "fine_dining", "logistics", "construction"],
    "advisory": ["advisory", "legal", "audit", "marketing"],
    "client": ["wealth_management", "family_office", "luxury_retail", "real_estate"],
    "financial": ["trade_finance", "asset_management", "insurance", "wealth_management"],
}


def _company_name(rng, category: str, country: str, used: set[str]) -> str:
    words = _CATEGORY_WORDS[category]
    for _ in range(200):
        name = (
            f"{_PREFIXES[rng.integers(0, len(_PREFIXES))]} "
            f"{words[rng.integers(0, len(words))]} "
            f"{_SUFFIXES[country][rng.integers(0, len(_SUFFIXES[country]))]}"
        )
        if name not in used:
            used.add(name)
            return name
    raise RuntimeError("Impossible de generer un nom de societe unique")


def build_entities() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construit `entities` et le registre `companies` des societes externes."""
    rng = make_rng("entities")
    rows: list[dict] = []

    for item in config.MORETTI_STRUCTURE:
        rows.append({
            "entity_id": item["entity_id"],
            "entity_name": item["entity_name"],
            "entity_type": item["entity_type"],
            "parent_entity_id": item["parent_entity_id"],
            "country": item["country"],
            "city": item["city"],
            "industry": item["industry"],
            "creation_date": item["creation_date"],
            "status": "active",
            "_category": "internal",
            "_headcount": item["headcount"],
            "_ownership_type": "private",
            "_risk_level": "low",
        })

    for item in config.SCENARIO_ENTITIES:
        rows.append({
            "entity_id": item["entity_id"],
            "entity_name": item["entity_name"],
            "entity_type": item["entity_type"],
            "parent_entity_id": item["parent_entity_id"],
            "country": item["country"],
            "city": item["city"],
            "industry": item["industry"],
            "creation_date": item["creation_date"],
            "status": "active",
            "_category": "scenario",
            "_headcount": 0,
            "_ownership_type": item["ownership_type"],
            "_risk_level": item["risk_level"],
        })

    used_names = {r["entity_name"] for r in rows}
    countries = list(_COUNTRY_WEIGHTS)
    weights = [_COUNTRY_WEIGHTS[c] for c in countries]

    index = config.FIRST_FREE_ENTITY_INDEX
    plan = [
        ("supplier", config.N_EXTERNAL_SUPPLIERS),
        ("advisory", config.N_EXTERNAL_ADVISORY),
        ("client", config.N_EXTERNAL_CLIENTS),
        ("financial", config.N_EXTERNAL_FINANCIAL),
    ]

    for category, count in plan:
        for _ in range(count):
            country = str(rng.choice(countries, p=weights))
            city = str(rng.choice(config.COUNTRIES[country]["cities"]))
            name = _company_name(rng, category, country, used_names)
            industry = str(rng.choice(_INDUSTRIES_BY_CATEGORY[category]))
            # Anciennete : la majorite des contreparties sont etablies, une
            # minorite est recente. Les societes recentes ne sont pas rares,
            # ce qui empeche d'en faire un critere de suspicion a soi seul.
            age_years = float(rng.gamma(shape=2.4, scale=4.0))
            creation = config.PERIOD_END - dt.timedelta(days=int(age_years * 365.25) + 30)
            creation = max(creation, config.HISTORY_START)

            risk = _risk_level(country, creation, industry)
            rows.append({
                "entity_id": entity_id(index),
                "entity_name": name,
                "entity_type": _CATEGORY_ENTITY_TYPE[category],
                "parent_entity_id": None,
                "country": country,
                "city": city,
                "industry": industry,
                "creation_date": creation,
                "status": "active" if rng.random() > 0.04 else "dormant",
                "_category": category,
                "_headcount": 0,
                "_ownership_type": str(rng.choice(
                    ["private", "family_office", "public", "trust"],
                    p=[0.62, 0.19, 0.12, 0.07])),
                "_risk_level": risk,
            })
            index += 1

    entities = pd.DataFrame(rows)

    external = entities[entities["_category"] != "internal"].copy()
    companies = pd.DataFrame({
        "company_id": [company_id(i + 1) for i in range(len(external))],
        "company_name": external["entity_name"].to_numpy(),
        "entity_id": external["entity_id"].to_numpy(),
        "country": external["country"].to_numpy(),
        "city": external["city"].to_numpy(),
        "industry": external["industry"].to_numpy(),
        "creation_date": external["creation_date"].to_numpy(),
        "ownership_type": external["_ownership_type"].to_numpy(),
        "risk_level": external["_risk_level"].to_numpy(),
        "status": external["status"].to_numpy(),
    })

    return entities, companies


def _risk_level(country: str, creation: dt.date, industry: str) -> str:
    """Score de risque du referentiel, calcule sur des criteres publics.

    Volontairement grossier : il reflete la juridiction, l'anciennete et le
    secteur, pas le comportement reel de la societe. Une societe du circuit
    peut donc etre notee `low` et une societe parfaitement legitime `high`.
    """
    score = 0
    if country in ("AE", "MC", "SG"):
        score += 2
    elif country in ("LU", "CH"):
        score += 1
    age_days = (config.PERIOD_END - creation).days
    if age_days < 730:
        score += 2
    elif age_days < 1825:
        score += 1
    if industry in ("trade_finance", "wealth_management", "asset_management"):
        score += 1
    return "high" if score >= 4 else ("medium" if score >= 2 else "low")


def build_relationships(entities: pd.DataFrame) -> pd.DataFrame:
    """Relations declarees dans le referentiel groupe.

    Ne contient que ce qu'une direction financiere documente reellement :
    la structure capitalistique et les relations commerciales contractualisees.
    Les liens reveles uniquement par les flux ne sont pas ici : c'est a
    l'analyse de graphe de les reconstruire.
    """
    rng = make_rng("relationships")
    rows: list[dict] = []
    idx = 1

    for _, row in entities[entities["parent_entity_id"].notna()].iterrows():
        rows.append({
            "relationship_id": f"REL-{idx:04d}",
            "source_entity_id": row["parent_entity_id"],
            "target_entity_id": row["entity_id"],
            "relationship_type": "subsidiary",
            "start_date": row["creation_date"],
            "end_date": None,
            "confidence_score": 1.0,
        })
        idx += 1
        rows.append({
            "relationship_id": f"REL-{idx:04d}",
            "source_entity_id": row["entity_id"],
            "target_entity_id": row["parent_entity_id"],
            "relationship_type": "parent",
            "start_date": row["creation_date"],
            "end_date": None,
            "confidence_score": 1.0,
        })
        idx += 1

    internal_ids = config.MORETTI_IDS
    type_by_category = {
        "supplier": "supplier",
        "advisory": "advisor",
        "client": "client",
        "financial": "intermediary",
    }

    for _, row in entities[entities["_category"].isin(type_by_category)].iterrows():
        n_links = int(rng.integers(1, 4))
        partners = rng.choice(internal_ids, size=min(n_links, len(internal_ids)), replace=False)
        for partner in partners:
            start = max(row["creation_date"], config.PERIOD_START - dt.timedelta(days=900))
            rows.append({
                "relationship_id": f"REL-{idx:04d}",
                "source_entity_id": partner,
                "target_entity_id": row["entity_id"],
                "relationship_type": type_by_category[row["_category"]],
                "start_date": start,
                "end_date": None,
                # Les relations externes sont saisies manuellement : la
                # fiabilite de la donnee n'est pas parfaite.
                "confidence_score": round(float(rng.uniform(0.62, 0.99)), 2),
            })
            idx += 1

    return pd.DataFrame(rows)
