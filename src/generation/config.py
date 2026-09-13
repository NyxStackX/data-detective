"""Configuration centrale du générateur de données DATA DETECTIVE.

Tous les paramètres structurants du dataset sont regroupes ici afin que la
generation soit entierement pilotee par ce module et reproductible a l'identique.
"""

from __future__ import annotations

import datetime as dt
from typing import Final

# --------------------------------------------------------------------------
# Reproductibilite
# --------------------------------------------------------------------------

SEED: Final[int] = 2026

# --------------------------------------------------------------------------
# Periode couverte par le dataset
# --------------------------------------------------------------------------

PERIOD_START: Final[dt.date] = dt.date(2024, 1, 1)
PERIOD_END: Final[dt.date] = dt.date(2025, 12, 31)

# Dates anterieures autorisees pour les referentiels (creation de societes,
# ouverture de comptes, embauches). Aucune transaction n'existe avant PERIOD_START.
HISTORY_START: Final[dt.date] = dt.date(2006, 1, 1)

# --------------------------------------------------------------------------
# Referentiel geographique
# --------------------------------------------------------------------------

COUNTRIES: Final[dict[str, dict]] = {
    "FR": {"name": "France", "currency": "EUR", "cities": ["Paris", "Lyon", "Bordeaux"]},
    "CH": {"name": "Suisse", "currency": "CHF", "cities": ["Geneve", "Zurich", "Zoug"]},
    "GB": {"name": "Royaume-Uni", "currency": "GBP", "cities": ["Londres", "Manchester"]},
    "IT": {"name": "Italie", "currency": "EUR", "cities": ["Milan", "Rome", "Florence"]},
    "MC": {"name": "Monaco", "currency": "EUR", "cities": ["Monaco"]},
    "AE": {"name": "Emirats arabes unis", "currency": "AED", "cities": ["Dubai", "Abu Dhabi"]},
    "US": {"name": "Etats-Unis", "currency": "USD", "cities": ["New York", "Miami"]},
    "LU": {"name": "Luxembourg", "currency": "EUR", "cities": ["Luxembourg"]},
    "SG": {"name": "Singapour", "currency": "USD", "cities": ["Singapour"]},
    "BE": {"name": "Belgique", "currency": "EUR", "cities": ["Bruxelles", "Anvers"]},
    "ES": {"name": "Espagne", "currency": "EUR", "cities": ["Madrid", "Barcelone"]},
}

# Taux de reference au 01/01/2024 : 1 unite de devise = X EUR.
# Une derive mensuelle deterministe est appliquee dans fx.py.
FX_BASE: Final[dict[str, float]] = {
    "EUR": 1.0,
    "CHF": 1.0640,
    "GBP": 1.1550,
    "USD": 0.9060,
    "AED": 0.2467,
}

FX_MONTHLY_VOLATILITY: Final[dict[str, float]] = {
    "EUR": 0.0,
    "CHF": 0.009,
    "GBP": 0.011,
    "USD": 0.013,
    "AED": 0.013,
}

# --------------------------------------------------------------------------
# Banques fictives
# --------------------------------------------------------------------------

BANKS: Final[dict[str, list[str]]] = {
    "FR": ["Banque Lauriston", "Rivage Prive SA", "Credit Valmont"],
    "CH": ["Zurichsee Privatbank AG", "Alpenrand Bank AG", "Banque Chablais SA"],
    "GB": ["Northgate Merchant Bank", "Kingsway Private Bank"],
    "IT": ["Banca Sorrentino", "Istituto Vallenari SpA"],
    "MC": ["Banque de Roquebrune", "Compagnie Monegasque Verdier"],
    "AE": ["Gulf Meridian Bank PJSC", "Al Sadara Commercial Bank"],
    "US": ["Hudson Line Trust", "Ardent Federal Bank"],
    "LU": ["Fiduciaire Ardenne SA", "Banque Verlaine"],
    "SG": ["Southbay Private Trust"],
    "BE": ["Banque du Meuse SA"],
    "ES": ["Banco Altamar"],
}

# --------------------------------------------------------------------------
# Structure du groupe Moretti
# entity_id figes : ils sont references par le scenario.
# --------------------------------------------------------------------------

MORETTI_STRUCTURE: Final[list[dict]] = [
    {
        "entity_id": "ENT-0001",
        "entity_name": "Moretti Holding SAS",
        "entity_type": "holding",
        "parent_entity_id": None,
        "country": "FR",
        "city": "Paris",
        "industry": "holding",
        "creation_date": dt.date(2006, 4, 18),
        "headcount": 42,
    },
    {
        "entity_id": "ENT-0002",
        "entity_name": "Moretti Capital Partners SA",
        "entity_type": "investment_company",
        "parent_entity_id": "ENT-0001",
        "country": "CH",
        "city": "Geneve",
        "industry": "investments",
        "creation_date": dt.date(2009, 2, 3),
        "headcount": 38,
    },
    {
        "entity_id": "ENT-0003",
        "entity_name": "Moretti Real Estate Ltd",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0001",
        "country": "GB",
        "city": "Londres",
        "industry": "luxury_real_estate",
        "creation_date": dt.date(2010, 6, 21),
        "headcount": 64,
    },
    {
        "entity_id": "ENT-0004",
        "entity_name": "Moretti Hospitality Group SpA",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0001",
        "country": "IT",
        "city": "Milan",
        "industry": "hospitality",
        "creation_date": dt.date(2011, 9, 14),
        "headcount": 96,
    },
    {
        "entity_id": "ENT-0005",
        "entity_name": "Moretti Maison SA",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0001",
        "country": "FR",
        "city": "Paris",
        "industry": "jewellery",
        "creation_date": dt.date(2012, 3, 8),
        "headcount": 58,
    },
    {
        "entity_id": "ENT-0006",
        "entity_name": "Moretti Aviation SAM",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0001",
        "country": "MC",
        "city": "Monaco",
        "industry": "private_aviation",
        "creation_date": dt.date(2014, 1, 27),
        "headcount": 31,
    },
    {
        "entity_id": "ENT-0007",
        "entity_name": "Moretti Marine Services SAM",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0001",
        "country": "MC",
        "city": "Monaco",
        "industry": "yachting",
        "creation_date": dt.date(2015, 5, 12),
        "headcount": 27,
    },
    {
        "entity_id": "ENT-0008",
        "entity_name": "Moretti Art & Collections Ltd",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0001",
        "country": "GB",
        "city": "Londres",
        "industry": "art_collections",
        "creation_date": dt.date(2016, 11, 3),
        "headcount": 19,
    },
    {
        "entity_id": "ENT-0009",
        "entity_name": "Moretti Middle East DMCC",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0002",
        "country": "AE",
        "city": "Dubai",
        "industry": "luxury_real_estate",
        "creation_date": dt.date(2018, 2, 19),
        "headcount": 23,
    },
    {
        "entity_id": "ENT-0010",
        "entity_name": "Moretti USA Inc",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0001",
        "country": "US",
        "city": "New York",
        "industry": "luxury_real_estate",
        "creation_date": dt.date(2019, 7, 30),
        "headcount": 44,
    },
    {
        "entity_id": "ENT-0011",
        "entity_name": "Moretti Gastronomie SAS",
        "entity_type": "subsidiary",
        "parent_entity_id": "ENT-0004",
        "country": "FR",
        "city": "Paris",
        "industry": "fine_dining",
        "creation_date": dt.date(2020, 10, 5),
        "headcount": 36,
    },
]

MORETTI_IDS: Final[list[str]] = [e["entity_id"] for e in MORETTI_STRUCTURE]

# Entites externes figees, referencees nommement par le scenario.
SCENARIO_ENTITIES: Final[list[dict]] = [
    {
        "entity_id": "ENT-0012",
        "entity_name": "Aurum Advisory Partners S.a r.l.",
        "entity_type": "partner",
        "parent_entity_id": None,
        "country": "LU",
        "city": "Luxembourg",
        "industry": "advisory",
        "creation_date": dt.date(2023, 3, 9),
        "ownership_type": "private",
        "risk_level": "medium",
    },
    {
        "entity_id": "ENT-0013",
        "entity_name": "Helvetia Trade Solutions AG",
        "entity_type": "financial_entity",
        "parent_entity_id": None,
        "country": "CH",
        "city": "Zoug",
        "industry": "trade_finance",
        "creation_date": dt.date(2019, 4, 16),
        "ownership_type": "private",
        "risk_level": "medium",
    },
    {
        "entity_id": "ENT-0014",
        "entity_name": "Crescent Marina Development LLC",
        "entity_type": "investment_company",
        "parent_entity_id": None,
        "country": "AE",
        "city": "Dubai",
        "industry": "luxury_real_estate",
        "creation_date": dt.date(2021, 8, 2),
        "ownership_type": "joint_venture",
        "risk_level": "medium",
    },
    {
        "entity_id": "ENT-0015",
        "entity_name": "Zephyr Yachting Services SAM",
        "entity_type": "supplier",
        "parent_entity_id": None,
        "country": "MC",
        "city": "Monaco",
        "industry": "yachting",
        "creation_date": dt.date(2024, 1, 22),
        "ownership_type": "private",
        "risk_level": "high",
    },
    {
        "entity_id": "ENT-0016",
        "entity_name": "Al Reem Hospitality Holding LLC",
        "entity_type": "partner",
        "parent_entity_id": None,
        "country": "AE",
        "city": "Abu Dhabi",
        "industry": "hospitality",
        "creation_date": dt.date(2017, 6, 11),
        "ownership_type": "private",
        "risk_level": "low",
    },
    {
        "entity_id": "ENT-0017",
        "entity_name": "Sentinel Wealth Nominees Pte Ltd",
        "entity_type": "financial_entity",
        "parent_entity_id": None,
        "country": "SG",
        "city": "Singapour",
        "industry": "wealth_management",
        "creation_date": dt.date(2022, 11, 28),
        "ownership_type": "trust",
        "risk_level": "medium",
    },
]

FIRST_FREE_ENTITY_INDEX: Final[int] = 18

# --------------------------------------------------------------------------
# Volumetrie cible
# --------------------------------------------------------------------------

N_EXTERNAL_SUPPLIERS: Final[int] = 92
N_EXTERNAL_ADVISORY: Final[int] = 34
N_EXTERNAL_CLIENTS: Final[int] = 52
N_EXTERNAL_FINANCIAL: Final[int] = 12

N_INVESTMENTS: Final[int] = 180
N_AUDIT_NOISE_LOGS: Final[int] = 52_000

# --------------------------------------------------------------------------
# Seuils de gouvernance interne (publics, documentes dans le data dictionary)
# --------------------------------------------------------------------------

# Au-dela de ce montant en EUR, une seconde signature de niveau 5 est requise.
DUAL_APPROVAL_THRESHOLD_EUR: Final[float] = 750_000.0
# Au-dela de ce montant, l'approbation remonte au Group CFO.
CFO_APPROVAL_THRESHOLD_EUR: Final[float] = 1_000_000.0
# En deca de ce montant, la transaction est validee automatiquement.
AUTO_APPROVAL_THRESHOLD_EUR: Final[float] = 25_000.0

# --------------------------------------------------------------------------
# Catalogues de libelles
# --------------------------------------------------------------------------

TRANSACTION_TYPES: Final[list[str]] = [
    "transfer",
    "payment",
    "investment",
    "refund",
    "acquisition",
    "internal_transfer",
    "service_payment",
    "dividend",
    "loan",
    "repayment",
    "salary",
]

# Libelles utilises indifferemment par les prestations d'advisory legitimes
# et par le circuit du scenario : aucune signature textuelle exploitable.
ADVISORY_DESCRIPTIONS: Final[list[str]] = [
    "Strategic advisory services",
    "Market study - regional positioning",
    "Brand valuation assignment",
    "Portfolio review - quarterly",
    "Corporate structuring advisory",
    "Transaction support services",
    "Sector benchmark study",
    "Asset valuation report",
    "Advisory retainer",
    "Commercial due diligence",
    "Operational review",
    "Strategic positioning study",
]

SUPPLIER_DESCRIPTIONS: Final[dict[str, list[str]]] = {
    "hospitality": [
        "Linen and housekeeping supplies",
        "Food and beverage restocking",
        "Property maintenance contract",
        "Spa equipment servicing",
        "Guest amenities order",
    ],
    "luxury_real_estate": [
        "Construction milestone payment",
        "Architectural services",
        "Property management fee",
        "Facade renovation works",
        "Technical survey",
    ],
    "private_aviation": [
        "Aircraft maintenance check",
        "Fuel supply contract",
        "Crew training programme",
        "Hangar lease payment",
        "Avionics upgrade",
    ],
    "yachting": [
        "Hull maintenance works",
        "Marina berth fees",
        "Engine servicing",
        "Interior refit works",
        "Navigation systems upgrade",
    ],
    "jewellery": [
        "Precious stones acquisition",
        "Goldsmithing subcontracting",
        "Packaging and presentation cases",
        "Workshop tooling",
        "Certification services",
    ],
    "art_collections": [
        "Artwork acquisition",
        "Restoration works",
        "Secure transport and crating",
        "Insurance premium - collection",
        "Exhibition setup",
    ],
    "fine_dining": [
        "Fresh produce supply",
        "Wine cellar acquisition",
        "Kitchen equipment servicing",
        "Tableware order",
        "Seasonal menu sourcing",
    ],
    "investments": [
        "Custody fees",
        "Fund administration fees",
        "Research subscription",
        "Regulatory filing fees",
        "Market data licence",
    ],
    "holding": [
        "Group insurance premium",
        "Legal services",
        "Audit fees",
        "IT infrastructure licence",
        "Corporate travel",
    ],
}

CLIENT_DESCRIPTIONS: Final[list[str]] = [
    "Residence sale - final settlement",
    "Suite booking - corporate account",
    "Charter contract settlement",
    "Commission on private sale",
    "Event hosting - full package",
    "Lease income - quarterly",
    "Collection piece - settlement",
    "Membership renewal",
]

AUDIT_ACTIONS: Final[list[str]] = [
    "login",
    "logout",
    "view_transaction",
    "view_account",
    "view_report",
    "export_data",
    "download_document",
    "run_reconciliation",
    "modify_record",
    "failed_login",
    "approve_transaction",
]

IP_REGIONS: Final[list[str]] = ["FR", "CH", "GB", "IT", "MC", "AE", "US", "LU", "SG", "BE", "ES"]

# --------------------------------------------------------------------------
# Catalogues onomastiques (noms entierement fictifs)
# --------------------------------------------------------------------------

FIRST_NAMES: Final[dict[str, list[str]]] = {
    "FR": ["Camille", "Julien", "Elodie", "Antoine", "Margaux", "Hugo", "Sabine", "Thibault",
           "Laure", "Vincent", "Noemie", "Gregoire", "Clemence", "Baptiste", "Isabelle", "Olivier"],
    "CH": ["Nadine", "Lukas", "Sandrine", "Matthias", "Corinne", "Rafael", "Jasmin", "Andrin",
           "Philippe", "Miriam", "Dominik", "Valerie"],
    "GB": ["Eleanor", "Nathan", "Imogen", "Callum", "Harriet", "Dominic", "Rosalind", "Theo",
           "Beatrice", "Gareth", "Miranda", "Julian"],
    "IT": ["Elena", "Matteo", "Chiara", "Lorenzo", "Giulia", "Davide", "Federica", "Stefano",
           "Alessia", "Riccardo", "Martina", "Tommaso"],
    "MC": ["Alexia", "Raphael", "Sophie", "Marc", "Helene", "Bastien"],
    "AE": ["Layla", "Omar", "Sana", "Tarek", "Noura", "Rashid", "Hana", "Faisal"],
    "US": ["Megan", "Brandon", "Sierra", "Cole", "Danielle", "Trevor", "Paige", "Marcus",
           "Vanessa", "Grant"],
    "LU": ["Anouk", "Pierre", "Nina", "Georges"],
    "SG": ["Wei", "Amirah", "Jun", "Serene"],
    "BE": ["Maud", "Jasper", "Lore", "Sander"],
    "ES": ["Nuria", "Alvaro", "Paula", "Ignacio"],
}

LAST_NAMES: Final[dict[str, list[str]]] = {
    "FR": ["Vasseur", "Dautray", "Roche", "Lemaitre", "Brochard", "Fontanel", "Delaunay",
           "Perrin-Gaultier", "Mesnil", "Aubertin", "Chevalier", "Riviere", "Thibaud", "Nourry"],
    "CH": ["Kaufmann", "Brunner", "Sidler", "Zellweger", "Marguerat", "Hodel", "Wyss", "Bregy"],
    "GB": ["Hallwood", "Ashcombe", "Pryce", "Ledbury", "Marchant", "Whitlock", "Cavendish-Orme",
           "Renshaw", "Barlowe"],
    "IT": ["Marchetti", "Sorrentino", "Vallenari", "Bosetti", "Ferraris", "Danieli", "Trevisan",
           "Lombardi-Rossi"],
    "MC": ["Roquevaire", "Amadei", "Grimaldo-Serres", "Vinci"],
    "AE": ["Al Nuaimi", "Bensalem", "Al Hattawi", "Kassab", "Al Zaabi", "Haddad"],
    "US": ["Whitaker", "Delgado", "Kearns", "Brightwell", "Ostrander", "Vance", "Salinas"],
    "LU": ["Ben Othman", "Wagener", "Schiltz", "Muller-Deltgen"],
    "SG": ["Tan", "Rahim", "Cheong", "Lim"],
    "BE": ["Vanderplas", "Coppens", "Dewael"],
    "ES": ["Arrieta", "Moliner", "Cabrero"],
}

# --------------------------------------------------------------------------
# Postes et departements
# --------------------------------------------------------------------------

POSITIONS: Final[list[tuple[str, str, int, float]]] = [
    # (position, department, authorization_level, poids de tirage)
    ("Chief Executive Officer", "Executive", 5, 0.004),
    ("Chief Financial Officer", "Finance", 5, 0.006),
    ("Managing Director", "Executive", 5, 0.012),
    ("Financial Director", "Finance", 4, 0.022),
    ("Investment Director", "Investments", 4, 0.018),
    ("Treasury Manager", "Treasury", 4, 0.026),
    ("Compliance Officer", "Compliance", 4, 0.030),
    ("Internal Auditor", "Audit", 4, 0.022),
    ("Account Manager", "Finance", 3, 0.070),
    ("Financial Analyst", "Finance", 3, 0.085),
    ("Investment Analyst", "Investments", 3, 0.048),
    ("Treasury Analyst", "Treasury", 3, 0.042),
    ("Operations Manager", "Operations", 3, 0.070),
    ("Legal Counsel", "Legal", 3, 0.030),
    ("Procurement Manager", "Procurement", 3, 0.042),
    ("Accountant", "Finance", 2, 0.110),
    ("Operations Coordinator", "Operations", 2, 0.095),
    ("Sales Manager", "Commercial", 2, 0.070),
    ("Marketing Manager", "Marketing", 2, 0.040),
    ("HR Manager", "Human Resources", 2, 0.028),
    ("Executive Assistant", "Executive", 2, 0.038),
    ("Administrative Assistant", "Operations", 1, 0.092),
]


# Patronymes reserves aux dirigeants de societes externes. Les pools sont
# distincts de ceux du personnel interne : une homonymie entre les deux tables
# doit rester un evenement rare, sinon le rapprochement nominatif produit trop
# de faux positifs pour etre exploitable.
OFFICER_FIRST_NAMES: Final[dict[str, list[str]]] = {
    "FR": ["Aurelien", "Segolene", "Xavier", "Maelle", "Fabrice", "Oriane", "Ludovic"],
    "CH": ["Reto", "Barbara", "Silvan", "Katrin", "Urs", "Franziska"],
    "GB": ["Nigel", "Fiona", "Crispin", "Tamsin", "Rupert", "Verity"],
    "IT": ["Gianluca", "Ornella", "Emanuele", "Rosaria", "Corrado", "Simona"],
    "MC": ["Ludivine", "Aurelio", "Cyrielle", "Pascal"],
    "AE": ["Yasmin", "Khalid", "Dalia", "Zayd", "Imane", "Nabil"],
    "US": ["Chad", "Heather", "Dwight", "Lorraine", "Chip", "Bonnie"],
    "LU": ["Mathis", "Soraya", "Jean-Luc", "Elke"],
    "SG": ["Kiat", "Nadiah", "Boon", "Shu"],
    "BE": ["Wouter", "Griet", "Thibaut", "Annelies"],
    "ES": ["Santiago", "Rocio", "Joaquin", "Mireia"],
}

OFFICER_LAST_NAMES: Final[dict[str, list[str]]] = {
    "FR": ["Boucherand", "Villeprieux", "Nadaud", "Ferrandin", "Quesnoy", "Lassalle-Mire"],
    "CH": ["Aeschlimann", "Rothenbuhler", "Steinegger", "Vonlanthen", "Perriard"],
    "GB": ["Fothergill", "Strathmore", "Bexley-Hunt", "Ormerod", "Trelawney"],
    "IT": ["Giannotti", "Malvezzi", "Ruggieri", "Castelnuovo", "Peraino"],
    "MC": ["Balestrieri", "Fontvieille", "Larvotto-Rey"],
    "AE": ["Al Marzouqi", "Fakhouri", "Al Shamsi", "Darwiche"],
    "US": ["Hollingsworth", "Rutkowski", "Pemberton", "Castellano", "Wiggins"],
    "LU": ["Kirsch", "Reuland", "Thommes"],
    "SG": ["Ng", "Shanmugam", "Yeo"],
    "BE": ["Verstraeten", "Lambrechts", "Peeters-Dhont"],
    "ES": ["Balaguer", "Quintanilla", "Ferreiro"],
}
