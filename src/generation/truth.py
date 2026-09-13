"""Construction de la verite de reference de CASE #001.

`case_truth.json` est un artefact de developpement. Il sert a verifier que le
dataset porte effectivement la solution et a evaluer la conclusion du joueur
cote serveur. Il ne doit jamais transiter par un endpoint de lecture ni etre
embarque dans le bundle frontend.
"""

from __future__ import annotations

import pandas as pd

from . import config
from .scenario import (AMOUNT_A, AMOUNT_B, AMOUNT_C, AURUM, AL_REEM, CAPITAL_PARTNERS,
                       COLLAPSE_DATE, CRESCENT, FALSIFIED_RETURN, HELVETIA, HOSPITALITY,
                       MAISON, MARINE, MIDDLE_EAST, REAL_ESTATE, RECLASSIFICATION_DATE,
                       REFINANCING_DATE, SENTINEL, TOTAL_CASE, USA, ZEPHYR)

CIRCUIT_TAGS = ("A_investment_leg", "BC_circuit_inflow", "B_circuit_return", "C_diversion")
FALSE_LEAD_TAGS = ("false_lead_al_reem", "false_lead_zephyr",
                   "false_lead_erp_migration", "false_lead_us_repayments")


def _ids(transactions: pd.DataFrame, tag: str) -> list[str]:
    return transactions.loc[transactions["_tag"] == tag, "transaction_id"].tolist()


def build_case_truth(seed: dict, transactions: pd.DataFrame,
                     investments: pd.DataFrame) -> dict:
    inflow_ids = _ids(transactions, "BC_circuit_inflow")
    circuit_ids = [tid for tag in CIRCUIT_TAGS for tid in _ids(transactions, tag)]
    false_lead_ids = {tag: _ids(transactions, tag) for tag in FALSE_LEAD_TAGS}

    completed = transactions[transactions["status"] == "completed"]
    total_volume = float(completed["amount_eur"].sum())
    circuit_volume = float(
        transactions.loc[transactions["transaction_id"].isin(circuit_ids), "amount_eur"].sum()
    )

    inflow = transactions[transactions["_tag"] == "BC_circuit_inflow"]

    return {
        "case_id": "CASE-001",
        "case_name": "THE MISSING FORTUNE",
        "seed": config.SEED,
        "period": {"start": config.PERIOD_START.isoformat(),
                   "end": config.PERIOD_END.isoformat()},
        "final_amount_eur": TOTAL_CASE,
        "total_amount_eur": TOTAL_CASE,
        "dual_approval_threshold_eur": config.DUAL_APPROVAL_THRESHOLD_EUR,
        "cfo_approval_threshold_eur": config.CFO_APPROVAL_THRESHOLD_EUR,

        "true_cause": (
            "Les 47,8 M EUR ne correspondent pas a un vol unique mais a trois mecanismes "
            "distincts portes par deux personnes aux motivations opposees. Une perte "
            "d'investissement reelle de 31,2 M EUR sur le projet Crescent Marina a ete "
            "dissimulee par la falsification du rendement de la ligne, afin de preserver un "
            "covenant de rendement dans une negociation de refinancement. Pour faire tenir la "
            "dissimulation dans la duree, un circuit de facturation de prestations "
            "immaterielles a ete mis en place via Aurum Advisory Partners : 13,5 M EUR sont "
            "sortis du groupe puis y sont revenus sous l'apparence de remboursements d'une "
            "facilite structuree. Le tresorier adjoint, qui executait ces paiements, a "
            "exploite le canal a son profit et detourne 3,1 M EUR via des honoraires de "
            "succes verses a une structure de nominees a Singapour. La perte nette reelle "
            "est de 34,3 M EUR : 13,5 M EUR sont encore dans le groupe."
        ),

        "components": {
            "A_concealed_investment_loss": {
                "amount_eur": AMOUNT_A,
                "recoverable": False,
                "summary": "Perte reelle sur Crescent Marina, masquee par un rendement falsifie.",
            },
            "B_circular_replenishment": {
                "amount_eur": AMOUNT_B,
                "recoverable": True,
                "summary": ("Sortis via Aurum et Helvetia puis revenus chez Moretti Capital "
                            "Partners. Cle de la resolution complete."),
            },
            "C_personal_diversion": {
                "amount_eur": AMOUNT_C,
                "recoverable": False,
                "summary": "Detournement personnel via des honoraires de succes.",
            },
        },

        "involved_entities": [
            {"entity_id": CRESCENT, "role": "projet d'investissement effondre"},
            {"entity_id": MIDDLE_EAST, "role": "vehicule d'investissement du groupe"},
            {"entity_id": CAPITAL_PARTNERS, "role": "porteur de la ligne falsifiee, "
                                                    "destinataire des retours"},
            {"entity_id": AURUM, "role": "societe de facade du circuit"},
            {"entity_id": HELVETIA, "role": "relais de second saut"},
            {"entity_id": SENTINEL, "role": "destination du detournement"},
            {"entity_id": HOSPITALITY, "role": "filiale payeuse (9 paiements)"},
            {"entity_id": REAL_ESTATE, "role": "filiale payeuse (8 paiements)"},
            {"entity_id": MAISON, "role": "filiale payeuse (7 paiements)"},
        ],

        "involved_employees": [
            {"employee_id": "EMP-0003", "name": "Philippe Dautray",
             "role": "auteur de la dissimulation (composantes A et B)",
             "motive": "eviter la comptabilisation d'une perte compromettant le refinancement"},
            {"employee_id": "EMP-0004", "name": "Julien Vasseur",
             "role": "auteur du detournement (composante C)",
             "motive": "enrichissement personnel, en exploitant un canal cree par un autre"},
            {"employee_id": "EMP-0006", "name": "Karim Ben Othman",
             "role": "complice externe, dirigeant d'Aurum Advisory Partners",
             "motive": "ancien cadre du groupe, sorti en novembre 2022"},
            {"employee_id": "EMP-0001", "name": "Adrian Moretti",
             "role": "approbateur trompe - defaillance de gouvernance, pas de fraude",
             "motive": "a approuve un reclassement sur dossier falsifie, onze jours avant "
                       "la signature du refinancement"},
        ],

        "not_involved": [
            {"employee_id": "EMP-0002", "name": "Isabelle Roche",
             "why_suspicious": "signataire de toutes les operations superieures a 1 M EUR",
             "why_cleared": "regle de gouvernance automatique ; n'a signe aucun des "
                            "24 paiements du circuit, tous inferieurs au seuil"},
            {"employee_id": "EMP-0005", "name": "Elena Marchetti",
             "why_suspicious": "taux d'annulation anormal sur son perimetre",
             "why_cleared": "migration ERP de mars a juillet 2024 ; chaque annulation est "
                            "suivie d'une operation identique"},
            {"entity_id": ZEPHYR, "name": "Zephyr Yachting Services SAM",
             "why_suspicious": "societe recente, juridiction monegasque, 6,8 M EUR recus",
             "why_cleared": "refit documente, jalons de chantier, sorties diversifiees"},
        ],

        "money_flow": [
            {"step": 1, "date": "2024-02-15",
             "description": "Allocation de 31,2 M EUR de Geneve vers Dubai, en trois tranches",
             "amount_eur": AMOUNT_A},
            {"step": 2, "date": COLLAPSE_DATE.isoformat(),
             "description": "Suspension du permis, retrait du partenaire local : la ligne "
                            "perd sa valeur",
             "amount_eur": AMOUNT_A},
            {"step": 3, "date": RECLASSIFICATION_DATE.isoformat(),
             "description": f"Rendement saisi a {FALSIFIED_RETURN:+.1%} et reclassement en "
                            f"actif long terme, approuve par le dirigeant",
             "amount_eur": 0.0},
            {"step": 4, "date": REFINANCING_DATE.isoformat(),
             "description": "Signature du refinancement dont le covenant portait sur le "
                            "rendement moyen du portefeuille",
             "amount_eur": 0.0},
            {"step": 5, "date": "2024-12-20",
             "description": "Debut des 24 paiements de prestations immaterielles vers Aurum",
             "amount_eur": AMOUNT_B + AMOUNT_C},
            {"step": 6, "date": "2025-01-14",
             "description": "Reversements Aurum vers Helvetia Trade Solutions",
             "amount_eur": AMOUNT_B},
            {"step": 7, "date": "2025-01-22",
             "description": "Retours vers Moretti Capital Partners sous l'apparence de "
                            "remboursements d'une facilite jamais decaissee",
             "amount_eur": AMOUNT_B},
            {"step": 8, "date": "2025-02-06",
             "description": "Honoraires de succes vers Sentinel Wealth Nominees, Singapour",
             "amount_eur": AMOUNT_C},
            {"step": 9, "date": "2025-09-30",
             "description": "Arret net des paiements : mise en service du rapprochement "
                            "bancaire automatique",
             "amount_eur": 0.0},
        ],

        "suspicious_transactions": {
            "all_circuit": circuit_ids,
            "investment_leg": _ids(transactions, "A_investment_leg"),
            "circuit_inflow": inflow_ids,
            "circuit_return": _ids(transactions, "B_circuit_return"),
            "diversion": _ids(transactions, "C_diversion"),
        },

        "key_evidence": [
            {
                "id": "EV-01",
                "title": "Concentration des montants juste sous le seuil de double approbation",
                "table": "transactions",
                "technique": "histogramme des montants et test de bunching autour du seuil",
                "query_hint": ("filtrer transaction_type = 'service_payment', tracer la "
                               "distribution de amount_eur par tranches de 25 000 autour de "
                               "750 000"),
                "expected_finding": (
                    f"les 24 paiements vers {AURUM} sont tous compris entre "
                    f"{inflow['amount_eur'].min():,.0f} et {inflow['amount_eur'].max():,.0f} EUR, "
                    f"soit sous le seuil de {config.DUAL_APPROVAL_THRESHOLD_EUR:,.0f} EUR"),
            },
            {
                "id": "EV-02",
                "title": "Concentration systematique en fin de trimestre",
                "table": "transactions",
                "technique": "distribution du nombre de jours separant la date de la cloture",
                "query_hint": ("calculer days_to_quarter_end par destination_entity_id et "
                               "comparer a la distribution globale"),
                "expected_finding": ("100 % des paiements du circuit tombent dans les cinq "
                                     "derniers jours ouvres du trimestre, contre environ 14 % "
                                     "attendus"),
            },
            {
                "id": "EV-03",
                "title": "Composante de graphe quasi fermee",
                "table": "transactions + entities",
                "technique": "analyse de reseau, degre entrant et sortant par contrepartie",
                "query_hint": ("construire le graphe des flux externes, compter les "
                               "contreparties distinctes en entree et en sortie d'Aurum, puis "
                               "suivre le second saut"),
                "expected_finding": (
                    f"{AURUM} n'a que trois sources de revenus, toutes internes au groupe, et "
                    f"reverse la totalite vers {HELVETIA} et {SENTINEL} ; les retours de "
                    f"{HELVETIA} vers {CAPITAL_PARTNERS} sont enregistres en remboursements "
                    f"alors qu'aucun decaissement de pret correspondant n'existe"),
            },
            {
                "id": "EV-04",
                "title": "Lien nominatif entre le dirigeant d'Aurum et l'historique RH",
                "table": "company_officers + employees",
                "technique": "rapprochement nominatif et coherence des dates",
                "query_hint": ("joindre company_officers et employees sur first_name et "
                               "last_name, puis comparer termination_date et creation_date"),
                "expected_finding": ("Karim Ben Othman quitte Moretti Capital Partners en "
                                     "novembre 2022 et cree Aurum Advisory Partners en "
                                     "mars 2023"),
            },
            {
                "id": "EV-05",
                "title": "Rendement incompatible avec la cohorte sectorielle",
                "table": "investments",
                "technique": "z-score du rendement realise dans la cohorte secteur x pays x annee",
                "query_hint": ("comparer actual_return des investissements "
                               "sector='luxury_real_estate' et pays AE sur 2024"),
                "expected_finding": (
                    f"la ligne Crescent Marina affiche {FALSIFIED_RETURN:+.1%} alors que les "
                    f"huit lignes comparables sont comprises entre -35 % et -16 %"),
            },
            {
                "id": "EV-06",
                "title": "Sequence d'acces precedant chaque paiement",
                "table": "audit_logs + transactions",
                "technique": "correlation temporelle croisee entre acces et paiements",
                "query_hint": ("isoler les logs run_reconciliation entre 23h et 02h dont "
                               "ip_region differe du pays de rattachement, puis mesurer le "
                               "delai jusqu'au paiement suivant vers Aurum"),
                "expected_finding": ("21 des 24 paiements sont precedes de 24 a 48 heures d'un "
                                     "acces nocturne de EMP-0004 depuis la region AE, alors "
                                     "qu'il est rattache a Geneve"),
            },
        ],

        "false_leads": [
            {"id": "FL-01", "label": "Acquisition hoteliere d'Abu Dhabi",
             "amount_eur": 12_400_000.0, "entity_id": AL_REEM,
             "why_it_attracts": "montant eleve, destination emiratie, proximite temporelle",
             "how_to_dismiss": "ligne d'investissement correspondante, acompte anterieur, "
                               "rendement conforme a sa cohorte, actif toujours detenu",
             "transaction_ids": false_lead_ids["false_lead_al_reem"]},
            {"id": "FL-02", "label": "Le Group CFO signataire universel",
             "employee_id": "EMP-0002",
             "why_it_attracts": "presente sur toutes les operations majeures",
             "how_to_dismiss": "sa signature est une regle automatique au-dela de 1 M EUR ; "
                               "aucun paiement du circuit n'atteint ce seuil",
             "transaction_ids": []},
            {"id": "FL-03", "label": "Zephyr Yachting Services",
             "amount_eur": 6_800_000.0, "entity_id": ZEPHYR,
             "why_it_attracts": "societe creee en janvier 2024, juridiction monegasque, "
                                "risk_level eleve dans le referentiel",
             "how_to_dismiss": "jalons de chantier reguliers, sorties diversifiees vers des "
                               "sous-traitants, dirigeant sans lien avec le groupe",
             "transaction_ids": false_lead_ids["false_lead_zephyr"]},
            {"id": "FL-04", "label": "Pointes saisonnieres d'aout et de decembre",
             "why_it_attracts": "pics de volume marques sur plusieurs filiales",
             "how_to_dismiss": "les pics sont identiques en 2024 et en 2025 et suivent "
                               "l'activite hoteliere et joailliere",
             "transaction_ids": []},
            {"id": "FL-05", "label": "Annulations en serie a Milan",
             "entity_id": HOSPITALITY,
             "why_it_attracts": "taux d'annulation tres superieur au reste du groupe",
             "how_to_dismiss": "migration ERP de mars a juillet 2024 ; chaque annulation est "
                               "suivie d'une operation identique de montant egal",
             "transaction_ids": false_lead_ids["false_lead_erp_migration"]},
            {"id": "FL-06", "label": "Remboursements en cascade de l'entite americaine",
             "entity_id": USA,
             "why_it_attracts": "sequence dense de remboursements vers Geneve en 2025",
             "how_to_dismiss": "le decaissement initial de la facilite figure dans les "
                               "donnees, contrairement aux retours du circuit",
             "transaction_ids": false_lead_ids["false_lead_us_repayments"]},
        ],

        "hypotheses": [
            {"id": "H01", "label": "Erreur comptable", "verdict": "false",
             "note": "la falsification est datee, tracee et approuvee"},
            {"id": "H02", "label": "Fraude interne", "verdict": "partially_true",
             "note": "exacte pour 3,1 M EUR, soit 6,5 % du montant"},
            {"id": "H03", "label": "Detournement via une filiale", "verdict": "misleading",
             "note": "les filiales sont le canal, pas le beneficiaire"},
            {"id": "H04", "label": "Investissement dissimulant une perte", "verdict": "true",
             "note": "composante majeure : 31,2 M EUR"},
            {"id": "H05", "label": "Serie de transactions coordonnees", "verdict": "true",
             "note": "mecanisme d'execution : 24 paiements structures"},
            {"id": "H06", "label": "Intervention d'une societe externe", "verdict": "true",
             "note": "Aurum Advisory Partners et Helvetia Trade Solutions"},
        ],

        "scoring_key": {
            "optimal": {"hypotheses": ["H04", "H05", "H06", "H02"],
                        "requires": ["identification du circuit Aurum",
                                     "identification de la perte dissimulee",
                                     "recuperation des 13,5 M EUR",
                                     "distinction des deux auteurs"],
                        "score_range": [90, 100]},
            "acceptable": {"hypotheses": ["H02", "H06"],
                           "requires": ["identification du circuit Aurum"],
                           "score_range": [60, 80]},
            "weak": {"hypotheses": ["H01"], "requires": [], "score_range": [0, 45]},
        },

        "statistics": {
            "transactions_total": int(len(transactions)),
            "circuit_transactions": len(circuit_ids),
            "circuit_volume_eur": round(circuit_volume, 2),
            "circuit_share_of_count": len(circuit_ids) / len(transactions),
            "circuit_share_of_volume": circuit_volume / total_volume if total_volume else 0.0,
            "false_lead_transactions": sum(len(v) for v in false_lead_ids.values()),
            "total_volume_eur": round(total_volume, 2),
        },
    }
