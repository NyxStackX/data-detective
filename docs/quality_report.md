# RAPPORT DE QUALITÉ - DATASET CASE #001

Généré avec `SEED = 2026`, période 2024-01-01 → 2025-12-31.
Validation complète : **PASS** (45 contrôles, 0 échec).

---

## 1. Volumétrie

| Table | Lignes | Colonnes | Taille |
|---|---:|---:|---:|
| `transactions.csv` | 110 463 | 15 | 17,15 Mo |
| `audit_logs.csv` | 70 076 | 9 | 6,25 Mo |
| `employees.csv` | 478 | 11 | 40 Ko |
| `entity_relationships.csv` | 402 | 7 | 21 Ko |
| `accounts.csv` | 345 | 10 | 32 Ko |
| `company_officers.csv` | 292 | 7 | 20 Ko |
| `entities.csv` | 207 | 9 | 20 Ko |
| `companies.csv` | 196 | 10 | 19 Ko |
| `investments.csv` | 180 | 12 | 21 Ko |
| **Total** | **182 639** | | **23,6 Mo** |

L'objectif du cahier des charges était de 100 000 à 500 000 transactions. Le
dataset se place volontairement en bas de fourchette : 110 000 lignes suffisent
à noyer le circuit (0,058 % des opérations) tout en gardant des temps de requête
confortables en SQLite comme en Pandas, et un dépôt Git raisonnable. Le volume
se règle dans `src/generation/config.py` et `transactions.py` si un chargement
PostgreSQL plus lourd devient utile.

## 2. Couverture

- **11 pays** : FR, CH, GB, IT, MC, AE, US, LU, SG, BE, ES
- **5 devises** : EUR (61 499 opérations), GBP (22 256), USD (9 261), AED (8 847), CHF (8 600)
- **511 jours ouvrés** couverts sur 522 possibles, **aucune opération le week-end**
- **3 798 à 5 169** transactions par mois, moyenne 4 603
- **329 comptes sur 345** mouvementés ; les 16 restants sont des comptes clôturés ou dormants
- **249 collaborateurs** apparaissent en `created_by`, **92 entités** émettrices, **194** destinataires
- Volume financier total : **5,39 Md€** (opérations `completed`)
- Montants de 108 € à 12 500 000 €, médiane 13 816 €

## 3. Contrôles d'intégrité

Tous exécutés par `scripts/validate_dataset.py`.

| Domaine | Contrôle | Résultat |
|---|---|---|
| Clés | Unicité des 9 clés primaires | PASS |
| Intégrité | 17 relations de clé étrangère | PASS |
| Intégrité | Montants strictement positifs | PASS |
| Intégrité | Compte source ≠ compte destination | PASS |
| Dates | Transactions dans la période | PASS |
| Dates | Comptes ouverts à la date d'opération | PASS |
| Dates | Embauches postérieures à la création de l'entité | PASS |
| Dates | Sorties postérieures aux embauches | PASS |
| Dates | Journaux dans la période | PASS |
| Devises | Devise conforme au compte source | PASS |
| Devises | Conversion EUR cohérente | PASS |
| Cohérence | Statut RH cohérent avec la date de sortie | PASS |
| Cohérence | Niveaux d'habilitation dans [1,5] | PASS |
| Cohérence | Absence de cycle capitalistique | PASS |
| Étanchéité | Absence de colonne révélatrice | PASS |
| Étanchéité | Libellés du circuit non distinctifs | PASS |

Les valeurs `SYSTEM_AUTO` et `EXTERNAL` dans `created_by` / `authorized_by` sont
des acteurs conventionnels documentés, pas des clés étrangères orphelines :
`SYSTEM_AUTO` pour les opérations sous le seuil d'approbation automatique,
`EXTERNAL` pour les mouvements entre deux contreparties hors groupe.

## 4. Réalisme statistique

**Loi de Benford.** Distribution du premier chiffre significatif de `amount_eur`
comparée à la loi théorique :

| Chiffre | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Observé | 29,86 % | 16,71 % | 12,20 % | 9,84 % | 8,08 % | 6,94 % | 6,05 % | 5,52 % | 4,80 % |
| Théorique | 30,10 % | 17,61 % | 12,49 % | 9,69 % | 7,92 % | 6,69 % | 5,80 % | 5,12 % | 4,58 % |

Écart absolu moyen : **0,0032**, soit une conformité étroite. Les montants sont
tirés de lois log-normales par relation commerciale, ce qui produit la
distribution attendue sans avoir à la forcer.

Conséquence à connaître : **une analyse de Benford sur l'ensemble du dataset ne
détecte pas le circuit.** 64 opérations sur 110 463 ne déplacent pas la
distribution. C'est le comportement réel de ce test, souvent surestimé. Appliqué
à la seule population `service_payment`, il devient exploitable.

**Saisonnalité.** Indice mensuel du nombre d'opérations, base 100 :

| J | F | M | A | M | J | J | A | S | O | N | D |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 88 | 89 | 96 | 101 | 110 | 108 | 104 | 100 | 101 | 100 | 94 | 109 |

Les profils sont propres à chaque secteur - pointe estivale pour le yachting et
l'hôtellerie, pointe de décembre pour la joaillerie et la restauration - et
**stables entre 2024 et 2025**. C'est ce qui permet d'écarter la fausse piste
FL-04 : un pic reproduit à l'identique d'une année sur l'autre est une
habitude, pas un événement.

**Distribution des statuts.** `completed` 98,2 %, `cancelled` 0,71 %,
`pending` 0,67 %, `failed` 0,42 %. Les `pending` sont concentrés sur les deux
dernières semaines de la période, ce qui correspond au délai normal de
dénouement à la date d'extraction.

## 5. Détectabilité de l'enquête

Chaque indice du canon fait l'objet d'un contrôle chiffré. Si l'un cesse d'être
détectable, la validation échoue même avec une intégrité référentielle parfaite.

| Indice | Mesure | Valeur obtenue |
|---|---|---|
| EV-01 | Rapport sous/sur seuil de 750 k€ | 38 vs 17 (×2,2) |
| EV-01 | Paiements du circuit au-dessus du seuil | 0 sur 24 |
| EV-02 | Part en fin de trimestre | circuit 100 % vs socle 9,0 % |
| EV-03 | Contreparties distinctes en amont d'Aurum | 3 |
| EV-03 | Écart entrées / sorties Aurum | < 1 000 € sur 16,6 M€ |
| EV-03 | Remboursements sans décaissement d'origine | 14 pour 0 |
| EV-04 | Rapprochements nominatifs bruts | 77, dont 1 concluant |
| EV-05 | z-score du rendement Crescent Marina | 4,6 sur 8 comparables |
| EV-06 | Accès nocturnes hors zone de EMP-0004 | 21, corrélés à 21 des 24 paiements |
| EV-06 | Autres profils comparables | 4 employés au-dessus de 8 accès |

**Discrétion du circuit.** Le plus gros des 24 paiements se classe **488ᵉ** sur
110 463 en tri décroissant sur `amount_eur`. Aucun ne figure dans le top 300.
Le circuit représente 0,058 % du nombre d'opérations et 2,0 % du volume - cette
dernière part étant portée à 96 % par l'investissement initial de 31,2 M€, qui
est une opération légitime dans sa forme.

**Fausses pistes.** 442 transactions y sont rattachées, soit sept fois plus que
la vraie piste. Chacune est réfutable par un critère précis, documenté dans
`case_truth.json`.

## 6. Reproductibilité

`python scripts/generate_all.py --check-reproducibility` régénère l'ensemble
dans un répertoire temporaire et compare les empreintes SHA-256. Les **9 fichiers
CSV sont identiques au bit près**.

Chaque module de génération utilise un flux aléatoire nommé, dérivé de la seed
par hachage. Modifier la volumétrie d'une table ne décale donc pas les tirages
des autres : les identifiants et les personnages clés restent stables entre deux
évolutions du générateur.

## 7. Limites connues

**Ce que le dataset ne modélise pas.**

- Pas de soldes de comptes. Les transactions ne sont pas contraintes par une
  trésorerie disponible ; un compte peut « émettre » plus qu'il n'a reçu. Une
  analyse de solde cumulé donnerait des valeurs négatives sans signification.
- Pas de TVA, pas de frais bancaires, pas d'écritures de contrepartie
  comptable. Le dataset est un journal de flux, pas une comptabilité en partie
  double.
- Les taux de change sont mensuels, pas quotidiens. `amount_eur` est donc exact
  au mois, pas au jour.
- Les salaires sont agrégés en un lot mensuel par entité. Il n'y a pas de
  bulletin individuel, et donc pas d'analyse de rémunération possible.
- Les logs d'audit ne couvrent que 18 001 approbations sur les opérations au-delà
  du seuil automatique, échantillonnées. Une jointure exhaustive
  `transactions × audit_logs` sur les approbations trouvera des trous.

**Points de fragilité assumés.**

- `risk_level` ne compte que 3 sociétés en `high`. Un joueur qui filtre sur ce
  champ tombe immédiatement sur Zephyr, la fausse piste FL-03. C'est
  intentionnel - le champ est un piège méthodologique - mais l'échantillon est
  étroit.
- Les 24 paiements partagent le même couple `created_by` / `authorized_by`. Un
  `GROUP BY created_by, authorized_by` sur les `service_payment` remonte le
  circuit d'un coup. Le bruit existe : Vasseur a saisi plusieurs milliers
  d'opérations légitimes et Dautray en a approuvé autant, donc le couple ne
  ressort pas d'un tri par volume - mais c'est le raccourci le plus court du
  dataset. À surveiller si le niveau de difficulté doit monter.
- Le rythme strictement trimestriel du circuit est régulier au point qu'une
  simple analyse de périodicité le trouve. C'est cohérent avec le motif
  narratif - un habillage de clôture - mais c'est un signal fort.

**Prochaine évolution utile.** Introduire deux ou trois prestataires de conseil
légitimes ayant eux aussi un profil de facturation régulier et concentré en fin
de trimestre, afin que EV-02 ne désigne pas Aurum à lui seul.
