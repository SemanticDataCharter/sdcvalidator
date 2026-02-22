# sdcvalidator

**SDC4 structural validator** — a thin wrapper over [xmlschema](https://pypi.org/project/xmlschema/) with two-tier error classification.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## What it does

- Validates XML instances against SDC4 XSD schemas
- Classifies errors into **structural** (Tier 1: reject) vs **semantic** (Tier 2: report)
- Checks SDC4 schema compliance (no `xsd:extension` — only `xsd:restriction`)
- Converts between XML and JSON using schema-aware conversion

## Install

```bash
pip install sdcvalidator
```

Or from source:

```bash
git clone https://github.com/SemanticDataCharter/sdcvalidator.git
cd sdcvalidator
pip install -e .
```

## Python API

```python
from sdcvalidator import SDC4Validator, ErrorTier

# Validate an XML instance
validator = SDC4Validator("my_schema.xsd")
result = validator.validate("my_instance.xml")

if result.is_valid:
    print("Valid!")
else:
    for err in result.structural_errors:
        print(f"STRUCTURAL: {err.reason}")
    for err in result.semantic_errors:
        print(f"SEMANTIC: {err.reason}")
```

### Schema compliance checking

```python
from sdcvalidator import validate_sdc4_schema_compliance, assert_sdc4_schema_compliance

# Check if a schema uses xsd:extension (not allowed in SDC4)
is_valid, errors = validate_sdc4_schema_compliance("schema.xsd")

# Or raise an exception
assert_sdc4_schema_compliance("schema.xsd")
```

### Error classification

```python
from sdcvalidator import ErrorClassifier, ErrorTier

classifier = ErrorClassifier()
tier = classifier.classify(some_xmlschema_error)
# ErrorTier.STRUCTURAL or ErrorTier.SEMANTIC
```

### XML/JSON conversion

```python
from sdcvalidator.converters import xml_to_json, json_to_xml

# XML -> JSON (schema-aware)
data = xml_to_json("instance.xml", schema_path="schema.xsd")

# JSON -> XML
json_to_xml(data, "schema.xsd", "output.xml")
```

## CLI

### `sdcvalidate` — Validate XML against schema

```bash
# Basic validation
sdcvalidate schema.xsd instance.xml

# JSON output
sdcvalidate schema.xsd instance.xml --json

# Skip SDC4 compliance check
sdcvalidate --no-compliance-check schema.xsd instance.xml
```

Exit codes: `0` valid, `1` semantic errors only, `2` structural errors.

### `sdcvalidator-xml2json` — Convert XML to JSON

```bash
sdcvalidator-xml2json instance.xml --schema schema.xsd
sdcvalidator-xml2json instance.xml -o output.json
```

### `sdcvalidator-json2xml` — Convert JSON to XML

```bash
sdcvalidator-json2xml data.json schema.xsd -o output.xml
```

## Two-Tier Error Classification

| Tier | Type | Examples | Action |
|------|------|----------|--------|
| 1 | Structural | Unknown elements, cardinality violations, wrong nesting | **Reject** |
| 2 | Semantic | Type errors, pattern violations, enumeration mismatches | **Report** |

## SDC4 Schema Compliance

SDC4 data models must use `xsd:restriction` only — never `xsd:extension`. This enforces separation of structure (reference model) and semantics (data models), guaranteeing global interoperability.

The validator checks this by default and rejects schemas that violate this principle.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Links

- [Semantic Data Charter](https://semanticdatacharter.com)
- [SDC4 Reference Model](https://semanticdatacharter.com/ns/sdc4/)
- [xmlschema](https://pypi.org/project/xmlschema/)
