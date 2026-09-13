# PLAYBOOK D'ANALYSE - CASE #001

> **DOCUMENT INTERNE - RÉVÈLE LA SOLUTION.**
> À conserver hors du build public, au même titre que `data/truth/case_truth.json`.
> Ne jamais servir depuis un endpoint accessible au joueur, ne jamais inclure
> dans le bundle frontend.

Ce document recense les analyses qui permettent de reconstituer la vérité, avec
les requêtes testées sur le dataset généré (seed `2026`) et les résultats
obtenus. Il sert à trois choses : vérifier que le dataset reste résoluble après
chaque modification du générateur, calibrer le système d'indices de
l'application, et écrire les explications de fin de partie.

Toutes les requêtes SQL ci-dessous ont été exécutées sur les CSV chargés en
SQLite. Les équivalents Pandas figurent lorsqu'ils sont plus lisibles.

---

## Chemin de résolution

```text
Point d'entrée                 Découverte                      Conduit à
─────────────────────────────────────────────────────────────────────────────
Distribution des montants  →   bunching sous 750 k€        →   Aurum
Analyse temporelle         →   100 % en fin de trimestre   →   Aurum
Graphe des flux            →   composante fermée            →   Helvetia, Sentinel
Registre + RH              →   dirigeant = ex-salarié       →   Ben Othman
Cohorte d'investissement   →   rendement impossible         →   Crescent Marina
Journaux d'audit           →   séquence d'accès             →   Vasseur
```

Les quatre premiers chemins mènent au **mécanisme** (composantes B et C). Le
cinquième mène au **motif** (composante A). Le sixième mène à l'**auteur de
l'exécution**. Aucun ne suffit seul.

---

## EV-01 - Concentration des montants sous le seuil

**Idée.** Un seuil d'approbation crée une frontière de comportement. Si
quelqu'un veut éviter une seconde signature, ses montants s'accumulent juste
en dessous.

```sql
SELECT CAST(amount_eur / 25000 AS INT) * 25000 AS bucket, COUNT(*) AS n
FROM transactions
WHERE transaction_type = 'service_payment'
  AND status = 'completed'
  AND amount_eur BETWEEN 600000 AND 900000
GROUP BY bucket
ORDER BY bucket;
```

Résultat obtenu :

| Tranche | 600 k | 625 k | 650 k | 675 k | 700 k | 725 k | **750 k** | 775 k | 800 k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Opérations | 10 | 5 | 10 | 14 | 13 | 4 | 6 | 4 | 6 |

La bosse 675–725 k€ ressort nettement, et la densité s'effondre au passage de
750 000 €. Sur l'ensemble de la fenêtre ±12 % autour du seuil : **38 opérations
en dessous contre 17 au-dessus**, soit un rapport de 2,2.

Le pas suivant consiste à identifier qui est concerné :

```sql
SELECT e.entity_name, COUNT(*) AS n, ROUND(AVG(t.amount_eur)) AS moyenne,
       ROUND(MIN(t.amount_eur)) AS mini, ROUND(MAX(t.amount_eur)) AS maxi
FROM transactions t
JOIN entities e ON e.entity_id = t.destination_entity_id
WHERE t.transaction_type = 'service_payment' AND t.status = 'completed'
GROUP BY e.entity_name
HAVING n >= 8
ORDER BY moyenne DESC
LIMIT 5;
```

| Bénéficiaire | n | Moyenne | Min | Max |
|---|---:|---:|---:|---:|
| **Aurum Advisory Partners S.à r.l.** | 24 | 691 667 | 664 000 | 728 768 |
| Quernay Associates FZE | 87 | 445 955 | 27 779 | 2 236 218 |
| Kestrel Counsel Pte Ltd | 48 | 316 745 | 66 651 | 1 322 722 |
| Vionnaz Counsel SA | 36 | 314 087 | 51 202 | 1 045 581 |
| Falmere Analytics LLP | 27 | 310 478 | 21 929 | 1 094 212 |

C'est l'amplitude qui est décisive, pas la moyenne. Tous les prestataires
réels ont des montants étalés sur deux ordres de grandeur ; Aurum tient dans
une bande de 65 000 €, entièrement sous le seuil.

**Piège associé.** Ce même filtre écarte Isabelle Roche : elle signe 84 % des
opérations au-dessus de 1 M€ mais **aucun** des 24 paiements, précisément parce
qu'ils restent sous le seuil qui déclencherait sa signature.

---

## EV-02 - Concentration en fin de trimestre

```python
import pandas as pd, datetime as dt

tx = pd.read_csv("transactions.csv", parse_dates=["transaction_date"])

def days_to_quarter_end(d):
    q = (d.month - 1) // 3
    m, last = ((3, 31), (6, 30), (9, 30), (12, 31))[q]
    return (dt.date(d.year, m, last) - d.date()).days

svc = tx[(tx.transaction_type == "service_payment") & (tx.status == "completed")].copy()
svc["dqe"] = svc.transaction_date.map(days_to_quarter_end)

print(svc.groupby(svc.destination_entity_id == "ENT-0012")["dqe"].describe())
```

Les 24 paiements tombent tous entre J-8 et J-0 avant la clôture trimestrielle,
soit **100 %** contre **9,0 %** pour le reste de la population `service_payment`.
Aucun prestataire légitime ne présente ce profil.

Cette régularité a un corollaire utile : les paiements s'**arrêtent net après
le 30 septembre 2025**. Le dernier trimestre de la période est vide alors que
le rythme était strictement trimestriel depuis un an. Dans le canon, c'est la
mise en service du rapprochement bancaire automatique qui ferme le canal.

---

## EV-03 - La composante fermée du graphe

**Ratio sortant / entrant par contrepartie.** Une société qui reverse la
totalité de ce qu'elle reçoit n'a pas d'activité propre.

```sql
WITH flows AS (
  SELECT destination_entity_id AS eid, SUM(amount_eur) AS inflow, 0 AS outflow
  FROM transactions GROUP BY 1
  UNION ALL
  SELECT source_entity_id, 0, SUM(amount_eur) FROM transactions GROUP BY 1)
SELECT e.entity_name, ROUND(SUM(inflow)) AS inflow, ROUND(SUM(outflow)) AS outflow,
       ROUND(SUM(outflow) / NULLIF(SUM(inflow), 0), 3) AS ratio
FROM flows f JOIN entities e ON e.entity_id = f.eid
WHERE e.entity_type IN ('partner', 'financial_entity', 'supplier')
GROUP BY e.entity_name
HAVING SUM(inflow) > 3000000
ORDER BY ratio DESC
LIMIT 6;
```

| Contrepartie | Entrées | Sorties | Ratio |
|---|---:|---:|---:|
| **Aurum Advisory Partners S.à r.l.** | 16 600 000 | 16 600 000 | **1,000** |
| **Helvetia Trade Solutions AG** | 15 904 674 | 15 627 479 | **0,983** |
| Zephyr Yachting Services SAM | 6 800 000 | 2 889 706 | 0,425 |
| Lorval Logistics SAM | 5 174 350 | 194 679 | 0,038 |
| Perrine Industries LLP | 6 369 767 | 178 211 | 0,028 |

Les contreparties réelles conservent l'essentiel de ce qu'elles encaissent.
Aurum et Helvetia sont des points de passage.

**Le détail qui ferme la démonstration.** Les retours d'Helvetia vers Moretti
Capital Partners sont enregistrés en `repayment`, c'est-à-dire en
remboursements d'un prêt. Ce prêt n'existe pas :

```sql
SELECT e.entity_name, t.transaction_type, COUNT(*) AS n, ROUND(SUM(t.amount_eur)) AS total
FROM transactions t
JOIN entities e ON e.entity_id = t.source_entity_id
WHERE t.transaction_type IN ('loan', 'repayment')
  AND e.entity_type = 'financial_entity'
GROUP BY 1, 2;
```

| Entité | Type | n | Total |
|---|---|---:|---:|
| Helvetia Trade Solutions AG | `repayment` | 14 | 13 473 000 |

Aucune ligne `loan`. Quatorze remboursements pour 13,47 M€ sans le moindre
décaissement d'origine. C'est ici que se découvre la **composante B** : les
13,5 M€ ne sont pas perdus, ils sont revenus dans le groupe.

**Distinction avec FL-06.** La série de remboursements de Moretti USA vers
Genève, elle, est précédée d'un `loan` de 9,6 M€ daté du 9 janvier 2025. C'est
le test qui sépare le refinancement légitime du retour déguisé.

**Destination de la composante C.** Le reste des sorties d'Aurum - 3,1 M€ en
six virements libellés « Success fee » - part vers Sentinel Wealth Nominees
Pte Ltd, à Singapour, et ne revient pas.

---

## EV-04 - Rapprochement registre / fichier RH

```sql
SELECT o.first_name, o.last_name, c.company_name, emp.status, emp.termination_date,
       emp.entity_id, c.creation_date
FROM company_officers o
JOIN companies c ON c.company_id = o.company_id
JOIN employees emp ON emp.first_name = o.first_name AND emp.last_name = o.last_name
WHERE emp.status = 'inactive'
  AND c.entity_id IN (SELECT DISTINCT destination_entity_id FROM transactions);
```

La jointure brute sur le nom donne **77 correspondances** : ce sont très
majoritairement des homonymies. Le filtre sur les ex-salariés en retient
**cinq**. La discrimination finale se fait sur la chronologie et l'entité
d'origine :

| Dirigeant | Société | Sortie du groupe | Création société | Entité d'origine |
|---|---|---|---|---|
| **Karim Ben Othman** | **Aurum Advisory Partners** | 2022-11-30 | 2023-03-09 | **ENT-0002** |
| Andrin Zellweger | Nordheim Atelier SA | 2025-01-08 | bien antérieure | ENT-0002 |
| Chiara Ferraris | Westbourne Ventures SA | 2022-12-10 | bien antérieure | ENT-0004 |
| Marc Vinci | Sablon Investments DMCC | 2025-10-09 | bien antérieure | ENT-0011 |
| Marc Roquevaire | Vionnaz Trust SARL | 2020-07-26 | bien antérieure | ENT-0007 |

Seul Ben Othman présente la séquence complète : départ du groupe, puis création
d'une société **quatre mois plus tard**, société qui devient ensuite un
bénéficiaire majeur. Il venait de Moretti Capital Partners - la même entité que
Dautray et Vasseur.

**Méthodologie à retenir.** Un rapprochement nominatif ne prouve rien par
lui-même. C'est la conjonction nom + statut + chronologie + flux qui constitue
l'indice.

---

## EV-05 - Rendement incompatible avec la cohorte

```sql
SELECT i.investment_id, i.investment_date, ROUND(i.amount_eur) AS montant,
       i.expected_return, i.actual_return, i.status
FROM investments i
JOIN entities e ON e.entity_id = i.target_entity_id
WHERE i.sector = 'luxury_real_estate'
  AND e.country = 'AE'
  AND i.investment_date >= '2023-10-01'
ORDER BY i.actual_return DESC;
```

| Investissement | Date | Montant | Rendement réalisé | Statut |
|---|---|---:|---:|---|
| **INV-0001 (Crescent Marina)** | 2024-02-15 | **31 200 000** | **+4,2 %** | `active` |
| INV-0009 | 2023-11-14 | 8 300 000 | −16,3 % | `impaired` |
| INV-0004 | 2024-04-17 | 7 200 000 | −18,7 % | `impaired` |
| INV-0006 | 2024-06-11 | 5 950 000 | −20,8 % | `impaired` |
| INV-0008 | 2024-09-30 | 6 100 000 | −22,6 % | `impaired` |
| INV-0002 | 2024-01-22 | 4 800 000 | −24,4 % | `impaired` |
| INV-0007 | 2024-08-05 | 1 900 000 | −27,9 % | `impaired` |
| INV-0003 | 2024-03-08 | 2 650 000 | −30,1 % | `impaired` |
| INV-0005 | 2024-05-29 | 3 400 000 | −35,2 % | `written_off` |

Le marché a subi un retournement généralisé au second semestre 2024. Toutes les
lignes comparables sont dépréciées. Une seule affiche un rendement positif, et
c'est la plus grosse du lot - **z-score de 4,6** par rapport à ses huit
comparables.

Le journal d'audit date la saisie : `EMP-0003` modifie `INV-0001` le
**21 octobre 2024 à 21 h 47**, exporte un rapport dans la foulée, et
`EMP-0001` approuve le reclassement le lendemain matin. Le refinancement est
signé onze jours plus tard.

```sql
SELECT * FROM audit_logs
WHERE resource_id = 'INV-0001' ORDER BY timestamp;
```

À noter : aucun `view_report` au nom d'`EMP-0001` sur cette ressource avant
son approbation. Le dirigeant a validé sans consulter les pièces - faute de
gouvernance, pas fraude.

---

## EV-06 - Séquence d'accès précédant les paiements

```sql
SELECT l.employee_id, e.last_name, COUNT(*) AS n
FROM audit_logs l
JOIN employees e ON e.employee_id = l.employee_id
WHERE CAST(strftime('%H', l.timestamp) AS INT) IN (23, 0, 1, 2)
  AND l.ip_region IS NOT NULL
  AND l.ip_region <> e.country
GROUP BY 1, 2
ORDER BY n DESC
LIMIT 6;
```

| Employé | Nom | Accès nocturnes hors zone |
|---|---|---:|
| **EMP-0004** | **Vasseur** | **21** |
| EMP-0277 | Mesnil | 15 |
| EMP-0126 | Renshaw | 14 |
| EMP-0429 | Brightwell | 14 |
| EMP-0387 | Kassab | 10 |

Le classement seul ne prouve rien : quatre autres collaborateurs sont dans le
même ordre de grandeur, pour des raisons de déplacement parfaitement banales.
Ce qui distingue Vasseur est la **corrélation temporelle** :

```python
import pandas as pd

logs = pd.read_csv("audit_logs.csv", parse_dates=["timestamp"])
tx = pd.read_csv("transactions.csv", parse_dates=["transaction_date"])

night = logs[(logs.employee_id == "EMP-0004")
             & logs.timestamp.dt.hour.isin([23, 0, 1, 2])
             & (logs.ip_region == "AE")]
payments = tx[tx.destination_entity_id == "ENT-0012"].transaction_date

for d in payments:
    lead = (d - night.timestamp).dt.days
    print(d.date(), ((lead >= 1) & (lead <= 2)).sum())
```

**21 des 24 paiements** sont précédés de 24 à 48 heures d'un accès de
rapprochement bancaire nocturne depuis les Émirats, alors que Vasseur est
rattaché à Genève. Aucun des autres profils nocturnes ne présente de
corrélation avec une série de paiements.

Vasseur est par ailleurs `created_by` des 24 paiements, et Dautray
`authorized_by` des 24 - mais ce critère seul ne suffit pas : Vasseur a saisi
plusieurs milliers d'opérations légitimes au titre de la centralisation de
trésorerie, et Dautray en a approuvé autant.

---

## Reconstitution du montant

```python
inflow = tx[tx.destination_entity_id == "ENT-0012"].amount_eur.sum()   # 16 600 000
loss   = inv.loc[inv.investment_id == "INV-0001", "amount_eur"].iloc[0]  # 31 200 000
print(loss + inflow)   # 47 800 000
```

| Composante | Montant | Récupérable | Nature |
|---|---:|---|---|
| A - perte dissimulée sur Crescent Marina | 31 200 000 € | non | perte réelle |
| B - flux circulaires revenus dans le groupe | 13 500 000 € | **oui** | comblement |
| C - détournement personnel vers Singapour | 3 100 000 € | non | vol |
| **Total** | **47 800 000 €** | | |

**Perte nette réelle : 34,3 M€.** L'analyste qui s'arrête à « 47,8 M€ ont
disparu » rate le point le plus important du dossier.

---

## Fausses pistes et critère d'élimination

| Id | Piste | Ce qui attire | Ce qui l'élimine |
|---|---|---|---|
| FL-01 | Acquisition d'Abu Dhabi, 12,4 M€ | montant, destination, période | ligne `investments` correspondante, acompte antérieur, actif toujours détenu, rendement conforme |
| FL-02 | Le CFO signe tout | omniprésence sur les grosses opérations | règle automatique au-dessus de 1 M€ ; zéro paiement du circuit |
| FL-03 | Zephyr Yachting, 6,8 M€ | société créée en 2024, Monaco, `risk_level = high` | jalons de chantier réguliers, sorties diversifiées (ratio 0,425), dirigeant sans lien RH |
| FL-04 | Pics d'août et décembre | volumes anormalement élevés | identiques en 2024 et 2025, alignés sur l'activité hôtelière et joaillière |
| FL-05 | Annulations de Milan | taux 3,08 % contre 0,71 % pour le groupe | migration ERP mars–juillet 2024 ; chaque annulation suivie d'une opération identique |
| FL-06 | Remboursements de Moretti USA | série dense vers Genève | le `loan` initial de 9,6 M€ existe dans les données |

---

## Contrôle de non-régression

Après toute modification du générateur :

```bash
python scripts/generate_all.py --check-reproducibility
```

`validate_dataset.py` reprend chacun des six indices sous forme de contrôle
chiffré. Si l'un d'eux cesse d'être détectable, la validation échoue, même
lorsque l'intégrité référentielle reste parfaite. C'est le garde-fou principal
du projet : un dataset cohérent mais insoluble est un dataset cassé.
