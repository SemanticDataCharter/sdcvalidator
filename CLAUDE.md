# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SDCvalidator** is a production-ready Python library for validating XML documents against SDC4 (Semantic Data Charter version 4) schemas with **automatic ExceptionalValue injection** for validation errors.

**Purpose**: Extends standard XML Schema 1.1 validation with the SDC4 "quarantine-and-tag" pattern, preserving invalid data while flagging errors with ISO 21090-based ExceptionalValue elements.

**Status**: Production/Stable (v4.0.1)

---

## Key Concepts

### The SDC4 ExceptionalValue Recovery Pattern

Unlike traditional validators that reject invalid documents, SDCvalidator:

1. **Preserves** invalid data in the XML instance
2. **Inserts** ExceptionalValue elements to flag errors
3. **Classifies** errors into 15 ISO 21090 NULL Flavor types
4. **Enables** downstream data quality tracking and forensic analysis

**Example**:

```xml
<!-- Invalid input -->
<AdultPopulation>
    <xdcount-value>not_a_number</xdcount-value>
</AdultPopulation>

<!-- After recovery -->
<AdultPopulation>
    <sdc4:INV>  <!-- ExceptionalValue inserted -->
        <sdc4:ev-name>Invalid</sdc4:ev-name>
        <!-- Validation error: not a valid value for type xs:integer -->
    </sdc4:INV>
    <xdcount-value>not_a_number</xdcount-value>  <!-- Preserved -->
</AdultPopulation>
```

### Relationship to SDC4 Ecosystem

SDCvalidator is part of the SDC4 ecosystem:

- **[SDCRM](https://github.com/SemanticDataCharter/SDCRM)** v4.0.0 - Reference model and schemas
- **[SDCStudio](https://github.com/AxiusSDC/SDCStudio)** v4.0.0 - Web application for model generation
- **[SDCvalidator](https://github.com/Axius-SDC/sdcvalidator)** v4.0.1 - This library
- **[Obsidian Template](https://github.com/SemanticDataCharter/SDCObsidianTemplate)** v4.0.0 - Markdown templates

**All use version 4.x.x** - The MAJOR version (4) represents SDC generation.

---

## Repository Structure

```
sdcvalidator/
├── sdcvalidator/           # Main package
│   ├── core/               # XML Schema 1.0/1.1 validation engine
│   ├── sdc4/               # SDC4-specific ExceptionalValue logic
│   ├── converters/         # XML ↔ Python/JSON conversion
│   ├── resources/          # XML resource loading
│   ├── xpath/              # XPath evaluation
│   ├── cli.py              # Command-line interface
│   └── __init__.py         # Public API
├── sdc4/                   # SDC4 reference schemas
│   ├── sdc4.xsd            # SDC4 XML Schema (from SDCRM)
│   ├── sdc4.owl            # SDC4 ontology
│   └── sdc4-meta.owl       # Meta ontology
├── tests/                  # Test suite
│   ├── sdc4/               # SDC4-specific tests
│   └── ...                 # Other test modules
├── doc/                    # Sphinx documentation
├── pyproject.toml          # Package metadata and dependencies
└── README.md               # User-facing documentation
```

---

## Core Architecture

### Inheritance from xmlschema

SDCvalidator is **based on [xmlschema](https://github.com/brunato/xmlschema)** by Davide Brunato and SISSA. The core validation engine and much of the architecture come from xmlschema.

**What we added**:
- `sdcvalidator.sdc4` module - ExceptionalValue injection and error mapping
- `SDC4Validator` high-level API
- ISO 21090 NULL Flavor classification
- Recovery and reporting workflows
- SDC4-specific CLI commands

**What we preserved**:
- Full XML Schema 1.0/1.1 validation
- XPath evaluation
- XML ↔ Python conversion
- Resource management

### Key Modules

**sdcvalidator.core** - XML Schema validation (from xmlschema)
- `sdcvalidator.core.validator` - Main validation logic
- `sdcvalidator.core.schema` - Schema parsing and representation
- `sdcvalidator.core.elements` - Element definitions

**sdcvalidator.sdc4** - SDC4-specific functionality
- `sdcvalidator.sdc4.validator` - SDC4Validator class
- `sdcvalidator.sdc4.error_mapper` - Error → ExceptionalValue mapping
- `sdcvalidator.sdc4.recovery` - XML tree modification for recovery
- `sdcvalidator.sdc4.exceptional_values` - ExceptionalValue type definitions

**sdcvalidator.converters** - Data conversion
- `sdcvalidator.converters.etree` - ElementTree converters
- `sdcvalidator.converters.dict` - Dictionary converters
- `sdcvalidator.converters.json` - JSON converters

---

## Development Setup

### Environment

```bash
# Clone repository
git clone https://github.com/Axius-SDC/sdcvalidator.git
cd sdcvalidator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run SDC4 tests only
pytest tests/sdc4/ -v

# Run with coverage
pytest --cov=sdcvalidator --cov-report=html

# Run specific test
pytest tests/sdc4/test_validator.py::test_exceptional_value_injection -v
```

### Running Linters

```bash
# Flake8 (code style)
flake8 sdcvalidator

# MyPy (type checking)
mypy sdcvalidator
```

### Building Documentation

```bash
cd doc
make html
# Open _build/html/index.html
```

---

## Coding Standards

### Python Style

- **PEP 8** - Follow Python style guide
- **Type hints** - Use type annotations for all public APIs
- **Docstrings** - Google-style docstrings for all public functions/classes

```python
def validate_with_recovery(
    instance: Union[str, Path, ElementTree.Element],
    schema: Optional[Schema] = None
) -> ElementTree.Element:
    """Validate XML instance and inject ExceptionalValues for errors.

    Args:
        instance: XML instance (file path, string, or ElementTree)
        schema: Optional schema to validate against

    Returns:
        Recovered ElementTree with ExceptionalValue elements inserted

    Raises:
        ValueError: If instance format is invalid
        SchemaError: If schema is malformed
    """
    ...
```

### ExceptionalValue Type Mapping

When adding new error mapping rules:

1. **Identify error type** - What kind of validation failure?
2. **Choose appropriate ExceptionalValue** - Which of 15 types fits best?
3. **Add to ErrorMapper** - Update mapping logic
4. **Add tests** - Cover new mapping in `tests/sdc4/`
5. **Document** - Update README with new mapping behavior

**Current mapping strategy**:
- **INV** (Invalid) - Type violations, pattern mismatches, format errors
- **OTH** (Other) - Enumeration violations, value not in allowed set
- **NI** (No Information) - Missing required elements
- **NA** (Not Applicable) - Unexpected content, extra elements
- **UNC** (Unencoded) - Encoding/character set errors
- *Others* - Specialized use cases (see `sdcvalidator/sdc4/error_mapper.py`)

---

## Testing Strategy

### Test Categories

1. **Core validation tests** (`tests/`) - XML Schema 1.0/1.1 compliance
2. **SDC4 tests** (`tests/sdc4/`) - ExceptionalValue injection and recovery
3. **Integration tests** - End-to-end workflows
4. **CLI tests** (`tests/test_cli.py`) - Command-line interface

### Writing SDC4 Tests

```python
import pytest
from sdcvalidator import SDC4Validator
from sdcvalidator.sdc4 import ExceptionalValueType

def test_invalid_integer_recovery():
    """Test that invalid integer values trigger INV ExceptionalValue."""
    validator = SDC4Validator('tests/sdc4/schemas/test_schema.xsd')

    # Validate with recovery
    recovered_tree = validator.validate_with_recovery(
        'tests/sdc4/instances/invalid_integer.xml'
    )

    # Check ExceptionalValue was inserted
    ev_elements = recovered_tree.findall('.//{http://...}INV')
    assert len(ev_elements) == 1
    assert ev_elements[0].find('.//ev-name').text == 'Invalid'
```

### Test Coverage Requirements

- **Minimum coverage**: 80% overall
- **SDC4 module**: 90% coverage (critical functionality)
- **Core validation**: Use existing xmlschema test suite

---

## Command-Line Interface

### CLI Commands

**sdcvalidate** - Validate with optional recovery
```bash
sdcvalidate instance.xml --schema schema.xsd --recover -o recovered.xml
```

**sdc-recover** - Recovery-focused command
```bash
sdc-recover instance.xml --schema schema.xsd -o recovered.xml --report
```

**sdcvalidator-xml2json** - XML to JSON conversion
```bash
sdcvalidator-xml2json instance.xml --schema schema.xsd -o output.json
```

**sdcvalidator-json2xml** - JSON to XML conversion
```bash
sdcvalidator-json2xml data.json --schema schema.xsd -o output.xml
```

### Adding CLI Commands

1. Add function to `sdcvalidator/cli.py`
2. Register in `pyproject.toml` under `[project.scripts]`
3. Add tests in `tests/test_cli.py`
4. Update README with usage

---

## Versioning Strategy

SDCvalidator follows **semantic versioning** aligned with SDC4 ecosystem:

**Format**: `MAJOR.MINOR.PATCH`

- **MAJOR** (4.x.x): Matches SDC generation (SDC4 = 4.x.x)
- **MINOR** (4.X.0): New features, backward-compatible
- **PATCH** (4.0.X): Bug fixes, documentation

**Current**: v4.0.1

**When to bump**:
- **MAJOR**: Breaking API changes, incompatible with SDC4 schemas (rare - would mean SDC5)
- **MINOR**: New ExceptionalValue types, new API methods, enhanced mappings
- **PATCH**: Bug fixes, documentation, performance improvements

---

## Release Process

### Preparing a Release

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.rst** with changes
3. **Run full test suite**: `pytest`
4. **Build package**: `python -m build`
5. **Test installation**: `pip install dist/sdcvalidator-X.Y.Z.tar.gz`
6. **Commit**: `git commit -m "Release vX.Y.Z"`
7. **Tag**: `git tag vX.Y.Z`
8. **Push**: `git push origin main --tags`

### Publishing to PyPI

```bash
# Build distribution
python -m build

# Upload to PyPI (requires credentials)
python -m twine upload dist/sdcvalidator-X.Y.Z*
```

---

## Dependencies

### Core Dependencies

- **elementpath** (>=5.0.1, <6.0.0) - XPath evaluation

### Optional Dependencies

- **jinja2** - Code generation (optional)
- **lxml** - Fast XML parsing (optional, uses stdlib ElementTree by default)

### Development Dependencies

- **pytest** - Testing framework
- **coverage** - Code coverage
- **mypy** - Type checking
- **flake8** - Linting
- **sphinx** - Documentation

---

## Integration with SDC4 Ecosystem

### SDCRM Repository

SDCvalidator includes SDC4 schemas from [SDCRM](https://github.com/SemanticDataCharter/SDCRM):

- `sdc4/sdc4.xsd` - Reference model schema
- `sdc4/sdc4.owl` - Ontology
- `sdc4/sdc4-meta.owl` - Meta ontology

**When SDCRM updates**:
1. Copy updated schemas to `sdc4/` directory
2. Test all SDC4 tests: `pytest tests/sdc4/ -v`
3. Update version if needed
4. Document changes in CHANGELOG.rst

### SDCStudio Integration

SDCStudio can use SDCvalidator programmatically:

```python
from sdcvalidator import SDC4Validator

validator = SDC4Validator('user_generated_schema.xsd')
recovered = validator.validate_with_recovery('user_data.xml')
report = validator.validate_and_report('user_data.xml')
```

---

## Common Development Tasks

### Adding a New ExceptionalValue Type

1. **Define constant** in `sdcvalidator/sdc4/exceptional_values.py`
2. **Add mapping rule** in `sdcvalidator/sdc4/error_mapper.py`
3. **Add test** in `tests/sdc4/test_error_mapper.py`
4. **Update README** with new type in table
5. **Update documentation** in `doc/`

### Fixing a Validation Bug

1. **Write failing test** in appropriate test file
2. **Debug** using `pytest -vv --pdb`
3. **Fix code** in relevant module
4. **Verify fix**: `pytest tests/ -v`
5. **Check coverage**: `pytest --cov=sdcvalidator`
6. **Submit PR** with test + fix

### Performance Optimization

1. **Profile** using `profiling/` scripts
2. **Identify bottlenecks** in validation or recovery
3. **Optimize** without changing API
4. **Benchmark** before/after
5. **Add regression test** to prevent slowdown

---

## Documentation

### Where Documentation Lives

- **README.md** - User-facing quick start and API overview
- **doc/** - Sphinx documentation (comprehensive)
  - `doc/intro.rst` - Introduction
  - `doc/usage.rst` - Usage guide
  - `doc/api.rst` - API reference
- **CLAUDE.md** (this file) - Developer guidance

### Building Docs Locally

```bash
cd doc
make html
# Open _build/html/index.html in browser
```

### Documentation Style

- **Clear examples** - Show working code
- **Type information** - Document all parameters and return types
- **Error cases** - Document what can go wrong
- **Links** - Cross-reference related functions/classes

---

## Credits and Attribution

**SDCvalidator** is based on [xmlschema](https://github.com/brunato/xmlschema) by:
- **Davide Brunato** (brunato@sissa.it)
- **SISSA** (International School for Advanced Studies)

**SDC4 integration** developed by:
- **Axius-SDC, Inc.**
- **Tim Cook** (contact@axius-sdc.com)

Always credit the xmlschema project when discussing the core validation engine.

---

## Important Notes

### What SDCvalidator Does

✅ Validates XML against XML Schema 1.0/1.1
✅ Injects ExceptionalValue elements for SDC4 data quality tracking
✅ Classifies errors using ISO 21090 NULL Flavor taxonomy
✅ Provides high-level SDC4-aware API
✅ Supports XML ↔ JSON ↔ Python dict conversion

### What SDCvalidator Does NOT Do

❌ Generate SDC4 schemas (use SDCStudio)
❌ Create SDC4 data models from scratch (use SDCStudio)
❌ Provide UI for validation (use SDCStudio)
❌ Modify or "fix" invalid data automatically (preserves for auditing)

### Schema Philosophy

Like SDCRM, we believe:
- **Schemas are normative** - XSD defines what's valid
- **Validation is strict** - Errors must be flagged
- **Data is preserved** - Invalid data quarantined, not deleted
- **Quality is explicit** - ExceptionalValues make quality measurable

---

## Getting Help

- **GitHub Issues** - https://github.com/Axius-SDC/sdcvalidator/issues
- **GitHub Discussions** - https://github.com/Axius-SDC/sdcvalidator/discussions
- **Email** - contact@axius-sdc.com

---

## License

**MIT License** - See LICENSE file

**Copyright**:
- (c) 2025 Axius-SDC, Inc. (SDC4 integration)
- (c) 2016-2024 SISSA (core xmlschema engine)

---

**Remember**: SDCvalidator enables data quality tracking through the SDC4 ExceptionalValue pattern. Invalid data is preserved and flagged, not rejected.
