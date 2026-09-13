"""Generation des employes du groupe et des dirigeants de societes externes.

Les personnes cles de l'enquete sont figees en tete de table, mais rien ne les
distingue structurellement des autres : meme format, meme plage de niveaux
d'autorisation, meme distribution de departements.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from . import config
from .utils import make_rng, employee_id, officer_id

# Personnes figees. Leur presence ici tient a leur role dans le scenario,
# mais aucune colonne ne le signale.
KEY_PEOPLE: list[dict] = [
    {
        "employee_id": "EMP-0001", "first_name": "Adrian", "last_name": "Moretti",
        "position": "Chief Executive Officer", "department": "Executive",
        "entity_id": "ENT-0001", "country": "FR",
        "hire_date": dt.date(2006, 4, 18), "authorization_level": 5, "status": "active",
        "termination_date": None,
    },
    {
        "employee_id": "EMP-0002", "first_name": "Isabelle", "last_name": "Roche",
        "position": "Chief Financial Officer", "department": "Finance",
        "entity_id": "ENT-0001", "country": "FR",
        "hire_date": dt.date(2013, 9, 2), "authorization_level": 5, "status": "active",
        "termination_date": None,
    },
    {
        "employee_id": "EMP-0003", "first_name": "Philippe", "last_name": "Dautray",
        "position": "Investment Director", "department": "Investments",
        "entity_id": "ENT-0002", "country": "CH",
        "hire_date": dt.date(2014, 1, 13), "authorization_level": 4, "status": "active",
        "termination_date": None,
    },
    {
        "employee_id": "EMP-0004", "first_name": "Julien", "last_name": "Vasseur",
        "position": "Treasury Manager", "department": "Treasury",
        "entity_id": "ENT-0002", "country": "CH",
        "hire_date": dt.date(2017, 6, 5), "authorization_level": 4, "status": "active",
        "termination_date": None,
    },
    {
        "employee_id": "EMP-0005", "first_name": "Elena", "last_name": "Marchetti",
        "position": "Financial Director", "department": "Finance",
        "entity_id": "ENT-0004", "country": "IT",
        "hire_date": dt.date(2015, 3, 16), "authorization_level": 4, "status": "active",
        "termination_date": None,
    },
    {
        "employee_id": "EMP-0006", "first_name": "Karim", "last_name": "Ben Othman",
        "position": "Investment Director", "department": "Investments",
        "entity_id": "ENT-0002", "country": "CH",
        "hire_date": dt.date(2016, 5, 2), "authorization_level": 4, "status": "inactive",
        "termination_date": dt.date(2022, 11, 30),
    },
    {
        "employee_id": "EMP-0007", "first_name": "Nadine", "last_name": "Kaufmann",
        "position": "Compliance Officer", "department": "Compliance",
        "entity_id": "ENT-0002", "country": "CH",
        "hire_date": dt.date(2019, 10, 7), "authorization_level": 4, "status": "active",
        "termination_date": None,
    },
    {
        "employee_id": "EMP-0008", "first_name": "Eleanor", "last_name": "Hallwood",
        "position": "Internal Auditor", "department": "Audit",
        "entity_id": "ENT-0001", "country": "GB",
        "hire_date": dt.date(2021, 4, 12), "authorization_level": 4, "status": "active",
        "termination_date": None,
    },
]


def build_employees(entities: pd.DataFrame) -> pd.DataFrame:
    rng = make_rng("employees")
    rows: list[dict] = list(KEY_PEOPLE)

    positions = [p[0] for p in config.POSITIONS]
    departments = {p[0]: p[1] for p in config.POSITIONS}
    levels = {p[0]: p[2] for p in config.POSITIONS}
    weights = [p[3] for p in config.POSITIONS]
    total = sum(weights)
    weights = [w / total for w in weights]

    # Les postes de direction sont deja pourvus par les personnes figees.
    taken_unique = {
        ("ENT-0001", "Chief Executive Officer"),
        ("ENT-0001", "Chief Financial Officer"),
    }

    index = len(rows) + 1
    internal = entities[entities["_category"] == "internal"]

    for _, ent in internal.iterrows():
        already = sum(1 for r in rows if r["entity_id"] == ent["entity_id"])
        target = int(ent["_headcount"]) - already
        country = ent["country"]
        for _ in range(max(target, 0)):
            position = str(rng.choice(positions, p=weights))
            if position in ("Chief Executive Officer", "Chief Financial Officer"):
                key = (ent["entity_id"], position)
                if key in taken_unique:
                    position = "Financial Director"
                else:
                    taken_unique.add(key)

            # L'anciennete est bornee par la creation de l'entite.
            max_days = (config.PERIOD_END - ent["creation_date"]).days
            tenure_days = int(min(rng.exponential(1500), max_days - 30))
            hire = config.PERIOD_END - dt.timedelta(days=max(tenure_days, 30))

            # 7 % de sorties, reparties sur toute la periode : le depart d'un
            # collaborateur n'est pas en soi un evenement remarquable.
            if rng.random() < 0.07:
                status = "inactive"
                span = (config.PERIOD_END - hire).days
                termination = hire + dt.timedelta(days=int(rng.integers(200, max(span, 260))))
                termination = min(termination, config.PERIOD_END)
            else:
                status = "active"
                termination = None

            nationality = country if rng.random() < 0.78 else str(
                rng.choice(list(config.FIRST_NAMES))
            )
            first = str(rng.choice(config.FIRST_NAMES[nationality]))
            last = str(rng.choice(config.LAST_NAMES[nationality]))

            rows.append({
                "employee_id": employee_id(index),
                "first_name": first,
                "last_name": last,
                "position": position,
                "department": departments[position],
                "entity_id": ent["entity_id"],
                "country": country,
                "hire_date": hire,
                "authorization_level": levels[position],
                "status": status,
                "termination_date": termination,
            })
            index += 1

    return pd.DataFrame(rows)


# Dirigeants figes des societes du scenario.
KEY_OFFICERS: list[dict] = [
    {
        "company_entity_id": "ENT-0012", "first_name": "Karim", "last_name": "Ben Othman",
        "role": "Managing Partner", "appointment_date": dt.date(2023, 3, 9), "nationality": "LU",
    },
    {
        "company_entity_id": "ENT-0013", "first_name": "Dominik", "last_name": "Hodel",
        "role": "Director", "appointment_date": dt.date(2019, 4, 16), "nationality": "CH",
    },
    {
        "company_entity_id": "ENT-0015", "first_name": "Raphael", "last_name": "Roquevaire",
        "role": "Managing Director", "appointment_date": dt.date(2024, 1, 22), "nationality": "MC",
    },
    {
        "company_entity_id": "ENT-0017", "first_name": "Nadiah", "last_name": "Yeo",
        "role": "Nominee Director", "appointment_date": dt.date(2022, 11, 28), "nationality": "SG",
    },
    {
        "company_entity_id": "ENT-0014", "first_name": "Faisal", "last_name": "Al Zaabi",
        "role": "General Manager", "appointment_date": dt.date(2021, 8, 2), "nationality": "AE",
    },
    {
        "company_entity_id": "ENT-0016", "first_name": "Noura", "last_name": "Kassab",
        "role": "Chief Executive Officer", "appointment_date": dt.date(2017, 6, 11),
        "nationality": "AE",
    },
]

_OFFICER_ROLES = ["Managing Director", "Director", "Partner", "Chief Executive Officer",
                  "General Manager", "Board Member"]


def build_officers(entities: pd.DataFrame, companies: pd.DataFrame,
                   employees: pd.DataFrame) -> pd.DataFrame:
    """Dirigeants declares des societes externes.

    Sert de point de jonction entre le registre societes et l'historique RH :
    un rapprochement nominatif entre cette table et `employees` est l'une des
    analyses prevues. Des homonymies partielles sont introduites volontairement
    pour qu'un rapprochement naif sur le seul nom de famille produise des
    faux positifs.
    """
    rng = make_rng("officers")
    by_entity = dict(zip(companies["entity_id"], companies["company_id"]))
    rows: list[dict] = []
    index = 1

    for item in KEY_OFFICERS:
        rows.append({
            "officer_id": officer_id(index),
            "company_id": by_entity[item["company_entity_id"]],
            "first_name": item["first_name"],
            "last_name": item["last_name"],
            "role": item["role"],
            "appointment_date": item["appointment_date"],
            "nationality": item["nationality"],
        })
        index += 1

    scenario_ids = {i["entity_id"] for i in config.SCENARIO_ENTITIES}
    # Reservoir d'identites de collaborateurs : utilise pour fabriquer quelques
    # homonymies completes, sans aucun lien reel avec la societe concernee.
    staff_identities = employees[["first_name", "last_name"]].drop_duplicates(
        ).to_records(index=False).tolist()

    for _, comp in companies.iterrows():
        if comp["entity_id"] in scenario_ids:
            continue
        for _ in range(int(rng.integers(1, 3))):
            nationality = comp["country"]
            if rng.random() < 0.13:
                # Homonymie fortuite : quelques dirigeants portent le nom d'un
                # collaborateur du groupe sans avoir le moindre lien avec lui.
                # Un rapprochement nominatif naif les remonte tous.
                first, last = staff_identities[int(rng.integers(0, len(staff_identities)))]
                first, last = str(first), str(last)
            else:
                first = str(rng.choice(config.OFFICER_FIRST_NAMES[nationality]))
                last = str(rng.choice(config.OFFICER_LAST_NAMES[nationality]))
            appointment = comp["creation_date"]
            if rng.random() < 0.4:
                appointment = appointment + dt.timedelta(days=int(rng.integers(120, 2200)))
                appointment = min(appointment, config.PERIOD_END)
            rows.append({
                "officer_id": officer_id(index),
                "company_id": comp["company_id"],
                "first_name": first,
                "last_name": last,
                "role": str(rng.choice(_OFFICER_ROLES)),
                "appointment_date": appointment,
                "nationality": nationality,
            })
            index += 1

    return pd.DataFrame(rows)
