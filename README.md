# DATA DETECTIVE - Dataset CASE #001

Dataset synthétique pour l'enquête financière **THE MISSING FORTUNE**.
Généré, validé et reproductible avec `SEED = 2026`.

Toutes les entités, personnes, banques et sociétés sont fictives.

## Contenu

```text
data/
├── generated/                  9 CSV, 182 639 lignes, 23,6 Mo
│   ├── entities.csv
│   ├── employees.csv
│   ├── accounts.csv
│   ├── transactions.csv        110 463 lignes - table centrale
│   ├── investments.csv
│   ├── companies.csv
│   ├── company_officers.csv
│   ├── entity_relationships.csv
│   └── audit_logs.csv
├── raw/                        vide - emplacement des sources externes
├── processed/                  vide - emplacement des jeux dérivés
└── truth/
    └── case_truth.json         ⚠ SOLUTION - jamais exposée au joueur

scripts/
├── generate_data.py            génération complète
├── validate_dataset.py         validation technique et validation de l'enquête
└── generate_all.py             chaîne complète + contrôle de reproductibilité

src/generation/
├── config.py                   seed, période, référentiels, seuils, catalogues
├── utils.py                    calendrier ouvré, change, identifiants
├── entities.py                 entités, registre sociétés, relations
├── people.py                   employés et dirigeants
├── accounts.py                 comptes bancaires
├── transactions.py             socle de transactions légitimes
├── scenario.py                 ⚠ circuit de l'affaire et fausses pistes
├── investments.py              portefeuille et cohorte de comparaison
├── audit.py                    journaux d'audit
└── truth.py                    ⚠ construction de case_truth.json

docs/
├── data_dictionary.md          chaque table, chaque colonne
├── quality_report.md           volumétrie, contrôles, statistiques, limites
├── validation_report.txt       sortie de la dernière validation
└── internal/                   ⚠ RÉVÈLE LA SOLUTION
    ├── case_logic.md           logique de l'enquête
    └── analysis_playbook.md    requêtes de résolution et résultats attendus
```

## Fichiers à ne jamais exposer

`data/truth/case_truth.json`, `docs/internal/`, et `src/generation/scenario.py`
et `truth.py` si le dépôt du générateur est public. Le reste peut être servi
librement : les CSV ne contiennent aucune information qui désigne la solution.

Ajout recommandé au `.gitignore` du build front :

```gitignore
data/truth/
docs/internal/
```

## Prise en main

```bash
# Régénérer, valider et vérifier la reproductibilité
python scripts/generate_all.py --check-reproducibility

# Générer seulement
python scripts/generate_data.py

# Valider un dataset existant
python scripts/validate_dataset.py --save docs/validation_report.txt
```

Dépendances : Python 3.11+, `pandas`, `numpy`. Génération complète en environ
huit secondes.

## Chargement

```python
import pandas as pd

tx = pd.read_csv("data/generated/transactions.csv", parse_dates=["transaction_date"])
```

```bash
# SQLite
python - <<'EOF'
import pandas as pd, sqlite3, pathlib
con = sqlite3.connect("case001.db")
for path in pathlib.Path("data/generated").glob("*.csv"):
    pd.read_csv(path).to_sql(path.stem, con, index=False, if_exists="replace")
EOF
```

Pour PostgreSQL, `\copy` fonctionne directement sur les CSV : ils sont en UTF-8,
séparateur virgule, en-tête sur la première ligne, dates au format ISO.

## Ce qu'il faut savoir avant d'analyser

- **`amount_eur` est la colonne de comparaison.** `amount` est exprimé dans la
  devise du compte source. Toute analyse de distribution ou de seuil qui
  utilise `amount` produira des résultats faux - c'est délibéré.
- **`risk_level` dans `companies` n'est pas un score de suspicion.** Il est
  calculé sur la juridiction, l'ancienneté et le secteur. S'en servir comme
  filtre mène droit à une fausse piste.
- **`entity_relationships` est incomplète par construction.** Elle ne contient
  que les liens déclarés au référentiel. Les liens qui n'existent que dans les
  flux doivent être reconstruits depuis `transactions`.
- **Aucune colonne indicatrice.** Ni `is_suspicious`, ni score, ni libellé
  révélateur. La suspicion se calcule.

## Garanties de validation

La dernière exécution de `validate_dataset.py` passe 45 contrôles sans échec :
intégrité référentielle sur 17 relations, cohérence des dates, des devises et
des statuts, étanchéité de la solution, et - surtout - un contrôle chiffré par
indice de l'enquête. Si une modification du générateur rend l'un des six indices
indétectable, la validation échoue, même quand toutes les clés étrangères
restent valides.

Détail des chiffres dans `docs/quality_report.md`.
