#!/usr/bin/env python3
"""Chaine complete : generation, validation, rapport qualite.

Usage :
    python scripts/generate_all.py
    python scripts/generate_all.py --check-reproducibility

L'option de reproductibilite regenere le dataset dans un repertoire temporaire
et compare les empreintes SHA-256 fichier par fichier.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args: list[str]) -> int:
    return subprocess.call([PYTHON, *args], cwd=ROOT)


def check_reproducibility() -> bool:
    print("\nControle de reproductibilite")
    print("-" * 66)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        code = run(["scripts/generate_data.py",
                    "--output", str(tmp_path / "generated"),
                    "--truth", str(tmp_path / "truth")])
        if code != 0:
            return False
        reference = ROOT / "data" / "generated"
        identical = True
        for path in sorted(reference.glob("*.csv")):
            other = tmp_path / "generated" / path.name
            same = other.exists() and sha256(path) == sha256(other)
            identical &= same
            print(f"  {path.name:<28s} {'identique' if same else 'DIFFERENT'}")
        return identical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-reproducibility", action="store_true")
    parser.add_argument("--skip-generation", action="store_true")
    args = parser.parse_args()

    if not args.skip_generation:
        if run(["scripts/generate_data.py"]) != 0:
            print("Echec de la generation.")
            return 1

    report_path = Path("docs/validation_report.txt")
    code = run(["scripts/validate_dataset.py", "--save", str(report_path)])
    if code != 0:
        print("Le dataset n'a pas passe la validation.")
        return 1

    if args.check_reproducibility and not check_reproducibility():
        print("\nLe dataset n'est pas reproductible a l'identique.")
        return 1

    print("\nChaine complete terminee.")
    print(f"  Donnees   : {ROOT / 'data' / 'generated'}")
    print(f"  Verite    : {ROOT / 'data' / 'truth' / 'case_truth.json'}")
    print(f"  Rapport   : {ROOT / report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
