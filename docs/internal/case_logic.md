# LOGIQUE DE L'ENQUÊTE - CASE #001

> **DOCUMENT INTERNE.** Décrit la solution. À garder hors du build public.
> Complément : `analysis_playbook.md` (les requêtes), `case_truth.json` (les
> identifiants exacts).

---

## 1. Le principe de conception

L'affaire est construite à l'envers : la vérité a été écrite d'abord, puis
traduite en flux financiers, puis noyée dans un socle légitime. Trois règles
ont guidé l'encodage.

**Aucune anomalie n'est visible à l'échelle d'une transaction.** Chacune des
64 opérations du circuit est, prise isolément, parfaitement banale : un montant
plausible, un libellé courant, un approbateur habilité, une date ouvrée, une
devise cohérente. L'anomalie n'existe qu'au niveau de la *série* - sa
distribution, son calendrier, sa topologie.

**Chaque indice est indépendant des autres.** Six chemins d'analyse distincts
mènent au circuit, sur cinq tables différentes. Aucun n'est nécessaire, aucun
ne suffit. Un joueur qui ne pense jamais à l'analyse de graphe peut arriver au
même endroit par la distribution des montants ou par les journaux d'audit.

**Le raisonnement attendu est un raisonnement de convergence.** L'objectif
pédagogique n'est pas de trouver « la » transaction coupable, mais de
comprendre qu'une conviction en analyse de données se construit par
recoupement de signaux faibles indépendants.

---

## 2. La vérité en une page

**47,8 M€ ne sont pas 47,8 M€ volés.** Le montant recouvre trois mécanismes
distincts, portés par deux personnes aux motivations opposées.

| | Montant | Nature | Auteur |
|---|---:|---|---|
| **A** | 31,2 M€ | Perte réelle sur un investissement, dissimulée | Philippe Dautray |
| **B** | 13,5 M€ | Flux circulaires - sortis puis revenus dans le groupe | Philippe Dautray |
| **C** | 3,1 M€ | Détournement personnel | Julien Vasseur |

**Chronologie.**

Février à juillet 2024, Moretti Middle East engage 31,2 M€ en trois tranches
dans Crescent Marina Development, un projet résidentiel de Dubaï. Le
17 septembre 2024, le permis est suspendu et le partenaire local se retire : la
participation ne vaut plus rien.

Philippe Dautray, directeur des investissements, ne peut pas laisser
comptabiliser cette perte. Un refinancement est en cours de négociation, et son
covenant porte sur le rendement moyen du portefeuille. Le 21 octobre 2024 à
21 h 47, il saisit un rendement de **+4,2 %** sur la ligne et la reclasse en
actif long terme. Adrian Moretti approuve le lendemain matin, sans avoir
consulté les pièces sources. Le refinancement est signé onze jours plus tard.

Tenir la dissimulation dans la durée suppose de faire circuler de la trésorerie.
Dautray met en place un canal de facturation de prestations immatérielles vers
**Aurum Advisory Partners**, une société luxembourgeoise dirigée par Karim Ben
Othman, ancien cadre de Moretti Capital Partners parti en novembre 2022. De
décembre 2024 à septembre 2025, trois filiales versent **24 paiements** à Aurum,
tous compris entre 664 000 et 728 768 €, tous dans les cinq derniers jours
ouvrés d'un trimestre. Total : 16,6 M€.

Aurum reverse la totalité. 13,5 M€ transitent par **Helvetia Trade Solutions**,
à Zoug, et reviennent chez Moretti Capital Partners sous l'apparence de
remboursements d'une facilité structurée - une facilité qui n'a jamais été
décaissée. C'est la composante B : l'argent est encore dans le groupe.

Julien Vasseur, trésorier adjoint, exécute ces paiements. Il comprend le
mécanisme et l'exploite : 3,1 M€ partent d'Aurum en six « honoraires de succès »
vers **Sentinel Wealth Nominees**, à Singapour, et ne reviennent pas. C'est la
composante C, et c'est le seul vol du dossier.

Les paiements cessent net après le 30 septembre 2025, à la mise en service du
rapprochement bancaire automatique. C'est cette rupture qui déclenche l'alerte
en octobre.

**Perte nette réelle : 34,3 M€.** L'analyste qui conclut à 47,8 M€ disparus a
raté le point le plus important : 13,5 M€ sont récupérables.

---

## 3. Où chaque élément est encodé

| Élément de vérité | Table | Encodage |
|---|---|---|
| L'investissement | `transactions` | 3 tranches Genève → Dubaï, 3 appels de fonds Dubaï → Crescent |
| La perte | `investments` | `INV-0001`, rendement `+0.042` contre −16 % à −35 % pour ses 8 comparables |
| La falsification | `audit_logs` | `modify_record` sur `INV-0001`, 21/10/2024 21 h 47, par `EMP-0003` |
| La défaillance de gouvernance | `audit_logs` | `approve_transaction` par `EMP-0001` sans `view_report` préalable |
| Le circuit | `transactions` | 24 `service_payment` vers `ENT-0012`, sous le seuil, en fin de trimestre |
| Le retour | `transactions` | 14 `repayment` de `ENT-0013` vers `ENT-0002` sans `loan` d'origine |
| Le détournement | `transactions` | 6 `transfer` de `ENT-0012` vers `ENT-0017` |
| Le complice | `company_officers` + `employees` | même couple prénom/nom, sortie 11/2022, société créée 03/2023 |
| L'exécutant | `audit_logs` | 21 accès nocturnes depuis AE, 24 à 48 h avant chaque paiement |

---

## 4. Ce qui a été fait pour que ce ne soit pas trop facile

**Le bruit est calibré, pas décoratif.** Chaque signal du circuit a un
équivalent légitime dans le dataset, en quantité suffisante pour qu'un filtre
naïf produise des faux positifs :

- 14 paiements légitimes tombent aussi dans la bande 660–750 k€
- 9 % des paiements de conseil légitimes tombent en fin de trimestre
- 77 rapprochements nominatifs entre dirigeants et salariés, dont 5 ex-salariés
- 4 collaborateurs cumulent 9 à 15 accès nocturnes hors zone, sans rien à se
  reprocher
- Helvetia Trade Solutions a une clientèle réelle : 70 opérations sans lien
  avec l'affaire
- Le référentiel classe Aurum en `risk_level = medium`, parmi 61 autres

**Les fausses pistes sont dimensionnées pour attirer.** 442 transactions leur
sont rattachées, sept fois le volume de la vraie piste. La plus grosse - une
acquisition hôtelière de 12,4 M€ à Abu Dhabi - est quatre fois plus visible en
montant que n'importe quel paiement du circuit.

**Rien ne trahit l'ordre de fabrication.** Les `transaction_id` sont attribués
après tri chronologique global. Les libellés du circuit sont tirés du même
catalogue que les paiements de conseil ordinaires, et un contrôle automatisé
vérifie qu'aucun libellé ne lui est exclusif. Les références bancaires suivent
un format unique. Aucune colonne ne porte de jugement.

---

## 5. Les hypothèses proposées au joueur

| Id | Hypothèse | Verdict | Commentaire |
|---|---|---|---|
| H01 | Erreur comptable | faux | la falsification est datée, tracée, approuvée |
| H02 | Fraude interne | partiellement vrai | exact pour 3,1 M€, soit 6,5 % du montant |
| H03 | Détournement via une filiale | trompeur | les filiales sont le canal, pas le bénéficiaire |
| H04 | Investissement dissimulant une perte | vrai | composante majeure, 31,2 M€ |
| H05 | Série de transactions coordonnées | vrai | mécanisme d'exécution |
| H06 | Intervention d'une société externe | vrai | Aurum et Helvetia |

La combinaison optimale est **H04 + H05 + H06 + H02**, assortie de la
récupération des 13,5 M€ et de la distinction entre les deux auteurs. Le barème
complet figure dans `case_truth.json`, clé `scoring_key`.

**Le cas d'Adrian Moretti n'est jamais tranché par l'application.** Les données
établissent qu'il a approuvé un reclassement sur dossier falsifié sans consulter
les pièces. Elles n'établissent pas s'il savait. C'est un choix de conception :
l'enquête livre des faits, pas un verdict moral, et le joueur reste libre de son
appréciation.
