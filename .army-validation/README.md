# Army catalogue quality gate

Run locally with `python scripts/validate_armies.py`. GitHub Actions runs the
same check on pushes to main and pull requests.

## Currently automated
- XML parsing for .cat, .gst, .xml and compressed .catz/.gstz files
- JSON parsing for .json files
- Duplicate XML element IDs and invalid/negative XML constraint values
- Optional **exported roster** regressions in `.army-validation/cases.json`

## Exported roster case format
Create `.army-validation/cases.json` with an array like:

```json
[
  {
    "name": "Guardian with combat shield",
    "equipped": ["Combat Shield"],
    "active_rules": ["Armour Save 2+"],
    "expected_rules": ["Armour Save 2+"],
    "forbidden_rules": ["Unequipped weapon ability"],
    "expected_model_count": 1,
    "models": [{"name": "Guardian", "weapons": ["Standard weapon"]}]
  }
]
```

**Important:** The case must be generated from or manually verified against
an actual New Recruit export. Merely writing an expected result into
`active_rules` would make the test tautological; it is not proof of app
behaviour. Future work should add an export adapter and compare real output
against separate golden expectations for:

1. Each model owns its weapons (including models 2+).
2. Only equipped-weapon rules appear; model rules stay intact.
3. Gear-selected abilities and saves appear/disappear correctly.
4. Tough/Wounds are unchanged; redundant Tough(X) is not duplicated.
5. Unit-size limits, individual options, Hero/Epic Hero classifications.
6. No redundant rules/keywords in Force Organisation.

This first gate is intentionally **read-only**. It never rewrites catalogues.
