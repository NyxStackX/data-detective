# DICTIONNAIRE DE DONNÉES - DATA DETECTIVE / CASE #001

Dataset synthétique généré par `scripts/generate_data.py` (seed `2026`).
Période couverte : **2024-01-01 → 2025-12-31**.

Toutes les entités, personnes, banques et sociétés sont fictives.

## Vue d'ensemble

| Table | Lignes | Clé primaire | Rôle |
|---|---:|---|---|
| `entities.csv` | 207 | `entity_id` | Référentiel central : filiales et contreparties |
| `employees.csv` | 478 | `employee_id` | Personnel du groupe |
| `accounts.csv` | 345 | `account_id` | Comptes bancaires |
| `transactions.csv` | 110 463 | `transaction_id` | Table centrale des mouvements |
| `investments.csv` | 180 | `investment_id` | Portefeuille d'investissements |
| `companies.csv` | 196 | `company_id` | Registre des sociétés externes |
| `company_officers.csv` | 292 | `officer_id` | Dirigeants déclarés des sociétés externes |
| `entity_relationships.csv` | 402 | `relationship_id` | Relations déclarées entre entités |
| `audit_logs.csv` | 70 076 | `log_id` | Journal d'activité applicative |

## Schéma relationnel

```text
                        ┌──────────────┐
                        │   entities   │◀──────────┐ parent_entity_id
                        └──────┬───────┘           │ (auto-référence)
                               │                   │
        ┌──────────────┬───────┼──────────┬────────┴────────┐
        │              │       │          │                 │
   ┌────▼─────┐  ┌─────▼────┐ ┌▼────────┐ ┌▼──────────────┐ ┌▼──────────────────┐
   │ accounts │  │ employees│ │companies│ │ investments   │ │entity_relationships│
   └────┬─────┘  └────┬─────┘ └────┬────┘ └───────────────┘ └───────────────────┘
        │             │            │
        │             │       ┌────▼─────────────┐
        │             │       │ company_officers │
        │             │       └──────────────────┘
        │             │
   ┌────▼─────────────▼────┐
   │     transactions      │
   └───────────┬───────────┘
               │ resource_id (quand resource_type = 'transaction')
        ┌──────▼──────┐
        │ audit_logs  │
        └─────────────┘
```

Une jointure supplémentaire, non matérialisée par une clé étrangère, relie
`company_officers` à `employees` sur le couple `(first_name, last_name)`.
C'est un rapprochement nominatif, donc imparfait par nature : il produit des
faux positifs qu'il faut écarter par d'autres critères.

---

## `entities.csv`

Référentiel de toutes les personnes morales du périmètre : sociétés du groupe
et contreparties externes.

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `entity_id` | string | Identifiant unique | `ENT-0004` | Format `ENT-nnnn`, unique | PK |
| `entity_name` | string | Raison sociale | `Moretti Hospitality Group SpA` | Unique | |
| `entity_type` | enum | Nature de l'entité | `subsidiary` | `holding`, `subsidiary`, `investment_company`, `supplier`, `partner`, `financial_entity` | |
| `parent_entity_id` | string | Société mère | `ENT-0001` | Vide pour les entités externes ; aucun cycle | FK → `entities.entity_id` |
| `country` | string | Code pays ISO-3166 alpha-2 | `IT` | 11 pays couverts | |
| `city` | string | Ville de rattachement | `Milan` | Cohérente avec `country` | |
| `industry` | string | Secteur d'activité | `hospitality` | | |
| `creation_date` | date | Date de constitution | `2011-09-14` | Antérieure à toute opération de l'entité | |
| `status` | enum | Statut courant | `active` | `active`, `dormant` | |

Le groupe Moretti occupe les identifiants `ENT-0001` à `ENT-0011`.

---

## `employees.csv`

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `employee_id` | string | Identifiant unique | `EMP-0004` | Format `EMP-nnnn` | PK |
| `first_name` | string | Prénom | `Julien` | | jointure nominative avec `company_officers` |
| `last_name` | string | Nom | `Vasseur` | | idem |
| `position` | string | Intitulé de poste | `Treasury Manager` | 22 intitulés | |
| `department` | string | Département | `Treasury` | | |
| `entity_id` | string | Entité de rattachement | `ENT-0002` | | FK → `entities.entity_id` |
| `country` | string | Pays de rattachement | `CH` | Aligné sur l'entité | |
| `hire_date` | date | Date d'entrée | `2017-06-05` | Postérieure à `entities.creation_date` | |
| `termination_date` | date | Date de sortie | `2022-11-30` | Vide si `status = active` ; postérieure à `hire_date` | |
| `authorization_level` | int | Niveau d'habilitation | `4` | 1 à 5 | Conditionne les seuils d'approbation |
| `status` | enum | Statut | `active` | `active`, `inactive` | |

**Niveaux d'habilitation** - 1 : administratif, 2 : opérationnel, 3 : encadrement,
4 : direction fonctionnelle, 5 : direction générale.

---

## `accounts.csv`

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `account_id` | string | Identifiant unique | `ACC-0112` | Format `ACC-nnnn` | PK |
| `entity_id` | string | Titulaire | `ENT-0004` | | FK → `entities.entity_id` |
| `bank_name` | string | Établissement (fictif) | `Banca Sorrentino` | Cohérent avec `country` | |
| `country` | string | Pays de domiciliation | `IT` | | |
| `city` | string | Ville | `Milan` | | |
| `currency` | enum | Devise du compte | `EUR` | `EUR`, `CHF`, `GBP`, `USD`, `AED` | Impose `transactions.currency` |
| `account_type` | enum | Usage | `operating` | `operating`, `treasury`, `payroll`, `investment`, `escrow`, `business`, `settlement` | |
| `opening_date` | date | Ouverture | `2019-03-08` | Antérieure à toute opération | |
| `closing_date` | date | Clôture | `2025-02-14` | Vide si `status = active` | |
| `status` | enum | Statut | `active` | `active`, `closed` | |

Aucune transaction n'existe avant l'ouverture ni après la clôture d'un compte.

---

## `transactions.csv`

Table centrale. 110 463 lignes, 15 colonnes, 17 Mo.

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `transaction_id` | string | Identifiant unique | `TRX-055224` | Attribué **après tri chronologique** : l'ordre des identifiants ne reflète pas l'ordre de génération | PK |
| `transaction_date` | date | Date de valeur | `2025-06-27` | Jour ouvré, dans la période | |
| `source_account_id` | string | Compte débité | `ACC-0087` | ≠ `destination_account_id` | FK → `accounts.account_id` |
| `destination_account_id` | string | Compte crédité | `ACC-0231` | | FK → `accounts.account_id` |
| `source_entity_id` | string | Entité émettrice | `ENT-0004` | Titulaire du compte source | FK → `entities.entity_id` |
| `destination_entity_id` | string | Entité destinataire | `ENT-0012` | | FK → `entities.entity_id` |
| `amount` | float | Montant en devise d'origine | `612 480.33` | > 0 | |
| `currency` | enum | Devise | `GBP` | Égale à la devise du compte source | |
| `amount_eur` | float | Contre-valeur en euros | `707 431.02` | Conversion au taux du mois | **Colonne d'analyse : toute comparaison de montants passe par elle** |
| `transaction_type` | enum | Nature | `service_payment` | 11 valeurs, voir ci-dessous | |
| `reference` | string | Référence bancaire | `2506-418203` | Format `AAMM-nnnnnn`, commun à toutes les opérations | |
| `description` | string | Libellé | `Brand valuation assignment` | Tiré de catalogues partagés entre opérations régulières et irrégulières | |
| `status` | enum | État | `completed` | `completed`, `pending`, `cancelled`, `failed` | |
| `authorized_by` | string | Approbateur | `EMP-0003` | `EMP-nnnn`, `SYSTEM_AUTO` (< 25 k€) ou `EXTERNAL` | FK → `employees.employee_id` |
| `created_by` | string | Saisie par | `EMP-0004` | Idem | FK → `employees.employee_id` |

**Valeurs de `transaction_type`** - `payment`, `service_payment`, `transfer`,
`internal_transfer`, `investment`, `acquisition`, `refund`, `dividend`, `loan`,
`repayment`, `salary`.

**Règles d'approbation** (documentées, appliquées par le générateur) :

| Montant (EUR) | Approbateur |
|---|---|
| < 25 000 | `SYSTEM_AUTO` |
| 25 000 – 250 000 | Habilitation ≥ 3 de l'entité émettrice |
| 250 000 – 750 000 | Habilitation ≥ 4 de l'entité émettrice |
| 750 000 – 1 000 000 | Double signature, habilitation 5 |
| ≥ 1 000 000 | Group CFO (`EMP-0002`) dans 84 % des cas |

Le seuil de **750 000 EUR** est le seuil de double approbation. Il n'est
mentionné nulle part dans les données elles-mêmes : il se déduit de la
distribution des approbateurs.

**Répartition observée** - `completed` 108 466, `cancelled` 787, `pending` 742,
`failed` 468. Devises : EUR 61 499, GBP 22 256, USD 9 261, AED 8 847, CHF 8 600.

---

## `investments.csv`

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `investment_id` | string | Identifiant unique | `INV-0001` | | PK |
| `entity_id` | string | Entité investisseuse | `ENT-0009` | | FK → `entities.entity_id` |
| `investment_date` | date | Date d'engagement | `2024-02-15` | | |
| `target_entity_id` | string | Cible de l'investissement | `ENT-0014` | | FK → `entities.entity_id` |
| `amount` | float | Montant engagé | `126 469 801.38` | > 0 | |
| `currency` | enum | Devise | `AED` | | |
| `amount_eur` | float | Contre-valeur en euros | `31 200 000.00` | | |
| `sector` | string | Secteur | `luxury_real_estate` | 9 secteurs | |
| `expected_return` | float | Rendement attendu | `0.115` | Fraction annualisée | |
| `actual_return` | float | Rendement constaté | `0.042` | Peut être négatif | **Colonne clé de l'analyse de cohorte** |
| `maturity_date` | date | Échéance | `2029-02-15` | Postérieure à `investment_date` | |
| `status` | enum | Statut | `active` | `active`, `closed`, `impaired`, `written_off` | |

Statuts observés : `active` 152, `closed` 15, `impaired` 7, `written_off` 6.

---

## `companies.csv`

Registre externe des contreparties. Couvre toutes les entités non rattachées au
groupe.

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `company_id` | string | Identifiant unique | `CMP-0002` | | PK |
| `company_name` | string | Raison sociale | `Aurum Advisory Partners S.a r.l.` | | = `entities.entity_name` |
| `entity_id` | string | Correspondance référentiel | `ENT-0012` | | FK → `entities.entity_id` |
| `country`, `city`, `industry` | string | Implantation et secteur | `LU`, `Luxembourg`, `advisory` | | |
| `creation_date` | date | Constitution | `2023-03-09` | | |
| `ownership_type` | enum | Détention | `private` | `private`, `family_office`, `public`, `trust`, `joint_venture` | |
| `risk_level` | enum | Note de risque référentiel | `medium` | `low` 132, `medium` 61, `high` 3 | |
| `status` | enum | Statut | `active` | | |

**Attention à `risk_level`.** Il est calculé sur des critères publics -
juridiction, ancienneté, secteur - et reflète donc le profil administratif de la
société, pas son comportement. Une société parfaitement régulière peut y être
notée `high`, et l'inverse est également vrai. S'en servir comme filtre de
suspicion est une erreur méthodologique que le dataset sanctionne.

---

## `company_officers.csv`

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `officer_id` | string | Identifiant unique | `OFF-0001` | | PK |
| `company_id` | string | Société dirigée | `CMP-0002` | | FK → `companies.company_id` |
| `first_name`, `last_name` | string | Identité | `Karim`, `Ben Othman` | | jointure nominative avec `employees` |
| `role` | string | Fonction | `Managing Partner` | | |
| `appointment_date` | date | Nomination | `2023-03-09` | ≥ `companies.creation_date` | |
| `nationality` | string | Nationalité déclarée | `LU` | | |

Le rapprochement `company_officers × employees` sur `(first_name, last_name)`
produit **77 correspondances brutes**, dont l'écrasante majorité sont des
homonymies sans signification. Le tri passe par des critères additionnels :
société effectivement payée par le groupe, statut de l'employé, cohérence des
dates, entité de rattachement.

---

## `entity_relationships.csv`

Relations **déclarées** dans le référentiel groupe - c'est-à-dire ce qu'une
direction financière documente formellement.

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `relationship_id` | string | Identifiant unique | `REL-0042` | | PK |
| `source_entity_id` | string | Origine du lien | `ENT-0004` | | FK → `entities.entity_id` |
| `target_entity_id` | string | Cible du lien | `ENT-0012` | | FK → `entities.entity_id` |
| `relationship_type` | enum | Nature | `advisor` | `subsidiary`, `parent`, `supplier`, `client`, `advisor`, `intermediary`, `investor`, `shareholder`, `partner` | |
| `start_date` | date | Début | `2023-06-01` | | |
| `end_date` | date | Fin | vide | Vide si relation en cours | |
| `confidence_score` | float | Fiabilité de la saisie | `0.87` | 1.0 pour les liens capitalistiques, 0.62–0.99 pour les liens commerciaux saisis manuellement | |

**Cette table est incomplète par construction.** Les liens qui n'apparaissent
que dans les flux financiers n'y figurent pas : les reconstituer à partir de
`transactions` est précisément l'objet de l'analyse de réseau.

---

## `audit_logs.csv`

| Colonne | Type | Description | Exemple | Contraintes | Relation |
|---|---|---|---|---|---|
| `log_id` | string | Identifiant unique | `LOG-041882` | Ordonné par `timestamp` | PK |
| `employee_id` | string | Auteur | `EMP-0004` | | FK → `employees.employee_id` |
| `timestamp` | datetime | Horodatage | `2025-06-25 01:14:38` | Dans la période | |
| `action` | enum | Action | `run_reconciliation` | 11 valeurs | |
| `resource_type` | enum | Type de ressource | `account` | `transaction`, `account`, `investment`, `report`, `entity`, `employee` | |
| `resource_id` | string | Ressource visée | `ACC-0087` | Résolvable quand `resource_type = 'transaction'` | FK conditionnelle |
| `entity_id` | string | Entité concernée | `ENT-0002` | | FK → `entities.entity_id` |
| `result` | enum | Issue | `success` | `success`, `failure`, `denied` | |
| `ip_region` | string | Région de connexion | `AE` | Code pays ; **différente du pays de rattachement dans 14 % des cas** | |

Répartition des actions : `approve_transaction` 18 001, `login` 10 426,
`view_transaction` 9 290, `logout` 8 796, `view_report` 6 283, `view_account`
5 204, `download_document` 3 131, `run_reconciliation` 2 708, `export_data`
2 588, `modify_record` 2 075, `failed_login` 1 574.

**Deux pièges volontaires.** Les profils conformité et audit génèrent
structurellement trois à quatre fois plus de consultations que les autres :
c'est leur métier. Et les connexions tardives depuis une région étrangère
existent pour de nombreux collaborateurs - déplacements, décalage horaire,
astreintes de clôture. Ni l'horaire ni la région ne sont discriminants pris
isolément.

---

## Conventions transverses

- **Aucune colonne indicatrice.** Le dataset ne contient ni `is_suspicious`, ni
  `is_fraud`, ni score de risque comportemental. La suspicion se calcule.
- **Les libellés ne trahissent rien.** Les descriptions des opérations
  irrégulières sont tirées du même catalogue que celles des opérations
  régulières. Un contrôle automatisé vérifie qu'aucun libellé n'est exclusif au
  circuit.
- **Les identifiants ne trahissent rien.** `transaction_id` est attribué après
  tri chronologique global, indépendamment de l'ordre de génération interne.
- **Devises.** `amount` est exprimé dans la devise du compte source ;
  `amount_eur` applique le taux du mois de l'opération. Toute comparaison de
  montants entre pays doit se faire sur `amount_eur`.
- **Seed.** `SEED = 2026`, défini dans `src/generation/config.py`. La
  régénération produit des fichiers identiques au bit près, vérifié par
  `scripts/generate_all.py --check-reproducibility`.
