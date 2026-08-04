"""
reporting/spec_loader.py
─────────────────────────────────────────────────────────────────────────────
Loads a clause YAML spec by clause ID and returns the parsed dict.

Usage
─────
    from reporting.spec_loader import load_clause_spec

    spec = load_clause_spec("1.1.1")
    # spec["testcases"]["TC1_MUTUAL_AUTHENTICATION"]["steps"]  → list[str]

File naming convention
──────────────────────
    Clause "1.1.1"  →  clause_1_1_1.yaml
    Clause "2.3"    →  clause_2_3.yaml

Resolution order (first match wins)
────────────────────────────────────
    1. $TCAF_SPECS_DIR  environment variable (if set)
    2. <this file's parent>/specs/   →  reporting/specs/
    3. <repo root>/specs/            →  one level above reporting/
─────────────────────────────────────────────────────────────────────────────
"""

import os
import yaml


def _clause_to_filename(clause_id: str) -> str:
    """'1.1.1' → 'clause_1_1_1.yaml'"""
    return f"clause_{clause_id.replace('.', '_')}.yaml"


def _candidate_dirs() -> list[str]:
    candidates = []
    env = os.environ.get("TCAF_SPECS_DIR")
    if env:
        candidates.append(env)
    here      = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(here, "specs"))
    candidates.append(os.path.join(os.path.dirname(here), "specs"))
    return candidates


def load_clause_spec(clause_id: str) -> dict:
    """
    Return the parsed YAML dict for clause_id.

    Raises FileNotFoundError if no matching file is found.
    Raises ValueError if the file does not contain a top-level mapping.
    """
    filename = _clause_to_filename(clause_id)
    for directory in _candidate_dirs():
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                spec = yaml.safe_load(fh)
            if not isinstance(spec, dict):
                raise ValueError(
                    f"Spec file {path!r} must be a YAML mapping at the top level."
                )
            return spec

    searched = "\n  ".join(_candidate_dirs())
    raise FileNotFoundError(
        f"Clause spec '{filename}' not found in any of:\n  {searched}\n"
        f"Set $TCAF_SPECS_DIR or place the file under reporting/specs/."
    )