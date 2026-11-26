#!/usr/bin/env python3
"""Non-mutating catalogue checks. Run: python scripts/validate_armies.py"""
import argparse
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

XML_EXTENSIONS = {".cat", ".gst", ".xml"}
ZIP_EXTENSIONS = {".catz", ".gstz"}
IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build"}


def xml_issues(raw, label):
    issues = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        return [f"{label}: malformed XML: {exc}"]
    ids = [node.attrib["id"] for node in root.iter() if node.attrib.get("id")]
    for ident, number in Counter(ids).items():
        if number > 1:
            issues.append(f"{label}: duplicate element id {ident!r} ({number} occurrences)")
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] == "constraint":
            lo = node.get("value")
            if lo is not None:
                try:
                    if float(lo) < 0:
                        issues.append(f"{label}: negative constraint value {lo!r}")
                except ValueError:
                    issues.append(f"{label}: non-numeric constraint value {lo!r}")
    return issues


def inspect(path):
    issues = []
    ext = path.suffix.lower()
    if ext in XML_EXTENSIONS:
        issues.extend(xml_issues(path.read_bytes(), str(path)))
    elif ext == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, UnicodeError) as exc:
            issues.append(f"{path}: invalid JSON: {exc}")
    elif ext in ZIP_EXTENSIONS:
        try:
            with zipfile.ZipFile(path) as archive:
                members = [n for n in archive.namelist() if not n.endswith("/")]
                if not members:
                    issues.append(f"{path}: empty archive")
                for name in members:
                    if name.lower().endswith((".cat", ".gst", ".xml")):
                        issues.extend(xml_issues(archive.read(name), f"{path}!{name}"))
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            issues.append(f"{path}: invalid archive: {exc}")
    return issues


def check_loadout_cases(path):
    """Optional exported-roster regression contract.
    Each case has equipped, active_rules, absent_rules. No inference from unequipped profiles.
    """
    if not path.exists():
        return []
    problems = []
    try:
        cases = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cases, list):
            return [f"{path}: expected a list of regression cases"]
        for index, case in enumerate(cases, 1):
            name = case.get("name", f"case {index}")
            rules = set(case["active_rules"])
            for required in case.get("expected_rules", []):
                if required not in rules:
                    problems.append(f"{path}: {name}: missing equipped rule {required!r}")
            for forbidden in case.get("forbidden_rules", []):
                if forbidden in rules:
                    problems.append(f"{path}: {name}: unequipped/redundant rule {forbidden!r}")
            if len(case.get("active_rules", [])) != len(rules):
                problems.append(f"{path}: {name}: duplicate active rule")
            models = case.get("models", [])
            for model in models:
                if not model.get("weapons"):
                    problems.append(f"{path}: {name}: model {model.get('name', '?')} has no assigned weapons")
            if "expected_model_count" in case and len(models) != case["expected_model_count"]:
                problems.append(f"{path}: {name}: model count mismatch")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        problems.append(f"{path}: invalid regression case: {exc}")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--require-data", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    paths = sorted(p for p in root.rglob("*")
                   if p.is_file()
                   and not (set(p.relative_to(root).parts[:-1]) & IGNORED_DIRS)
                   and p.suffix.lower() in XML_EXTENSIONS | ZIP_EXTENSIONS | {".json"})
    # Allow the validator's own optional fixtures, but not lockfiles and generated dependency JSON.
    paths = [p for p in paths if p.name not in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}]
    problems = []
    for path in paths:
        problems.extend(inspect(path))
    cases_path = root / ".army-validation" / "cases.json"
    problems.extend(check_loadout_cases(cases_path))
    if not paths and args.require_data:
        problems.append("No catalogue/XML/JSON data files found")
    print(f"Scanned {len(paths)} catalogue/JSON files; {len(problems)} issue(s)")
    for issue in problems:
        print("ERROR:", issue)
    print("NOTE: Equipped-only rules, saves, Tough/Wounds, Hero categories and per-model loadouts "
          "require exported roster regression cases; structural checks alone do not prove them.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
