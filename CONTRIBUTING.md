# Contributing to SDCvalidator

Thank you for your interest in contributing to SDCvalidator! We welcome contributions from the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

**In summary**:
- Be respectful and professional
- Welcome diverse perspectives
- Focus on constructive feedback
- Show empathy towards others

---

## How Can I Contribute?

### Reporting Bugs

**Before submitting a bug report**:
- Check existing [GitHub Issues](https://github.com/Axius-SDC/sdcvalidator/issues)
- Try the latest version from `main` branch
- Collect relevant information (Python version, OS, minimal reproduction case)

**Submitting a bug report**:
1. Use the bug report template
2. Provide clear title and description
3. Include minimal reproduction example
4. Specify your environment (Python version, OS, dependencies)
5. Include error messages and stack traces

### Suggesting Enhancements

We welcome enhancement proposals! Please:

1. **Open an issue** describing the enhancement
2. **Explain the use case** - Why is this needed?
3. **Propose a solution** - How should it work?
4. **Consider backward compatibility** - Will this break existing code?

### Contributing Code

**Areas where we welcome contributions**:
- Bug fixes
- New ExceptionalValue mapping rules
- Performance improvements
- Documentation improvements
- Test coverage improvements
- CLI enhancements
- Error message improvements

---

## Development Setup

### Prerequisites

- **Python 3.9+** (we support 3.9-3.14)
- **git**
- **pip** and **virtualenv** (or **conda**)

### Setup Steps

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/sdcvalidator.git
cd sdcvalidator

# 3. Add upstream remote
git remote add upstream https://github.com/Axius-SDC/sdcvalidator.git

# 4. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 5. Install in development mode with dev dependencies
pip install -e ".[dev]"

# 6. Verify installation
pytest tests/ -v
```

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Update your main branch
git checkout main
git merge upstream/main

# Push to your fork
git push origin main
```

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with these specifics:

- **Line length**: 120 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Single quotes for strings (unless double quotes avoid escaping)
- **Imports**: Sorted alphabetically, grouped by stdlib/external/local

### Type Hints

**Required** for all public APIs:

```python
from typing import Union, Optional
from pathlib import Path
from xml.etree import ElementTree

def validate_with_recovery(
    instance: Union[str, Path, ElementTree.Element],
    schema: Optional['Schema'] = None,
    **kwargs
) -> ElementTree.Element:
    """Validate instance and inject ExceptionalValues.

    Args:
        instance: XML instance to validate
        schema: Optional schema (uses instance's if not provided)
        **kwargs: Additional validation options

    Returns:
        Recovered ElementTree with ExceptionalValue elements

    Raises:
        ValueError: If instance is invalid format
        SchemaError: If schema is malformed
    """
    ...
```

### Docstrings

Use **Google-style** docstrings for all public functions and classes:

```python
def map_error_to_exceptional_value(error: ValidationError) -> ExceptionalValueType:
    """Map validation error to appropriate ExceptionalValue type.

    Applies classification rules based on error characteristics to determine
    which of the 15 ISO 21090 NULL Flavor types best represents the error.

    Args:
        error: Validation error from XML Schema validation

    Returns:
        ExceptionalValueType enum value (e.g., INV, OTH, NI)

    Examples:
        >>> error = ValidationError("Invalid integer value")
        >>> map_error_to_exceptional_value(error)
        ExceptionalValueType.INV
    """
    ...
```

### Naming Conventions

- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`
- **Modules**: `lowercase` (no underscores unless necessary)

### Code Organization

```python
# 1. Module docstring
"""Module for SDC4 ExceptionalValue recovery."""

# 2. Imports (sorted, grouped)
import sys
from pathlib import Path
from typing import Optional

from elementpath import XPath

from sdcvalidator.core import Schema
from sdcvalidator.sdc4.types import ExceptionalValueType

# 3. Constants
DEFAULT_NAMESPACE = "http://semanticdatacharter.org/ns/sdc4/"

# 4. Functions/Classes
class SDC4Validator:
    ...
```

---

## Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run specific module
pytest tests/sdc4/ -v

# Run with coverage
pytest --cov=sdcvalidator --cov-report=html

# Run specific test
pytest tests/sdc4/test_validator.py::test_exceptional_value_injection -v

# Run with verbose output
pytest -vv

# Stop at first failure
pytest -x
```

### Writing Tests

**Test structure**:

```python
import pytest
from sdcvalidator import SDC4Validator
from sdcvalidator.sdc4 import ExceptionalValueType

class TestExceptionalValueInjection:
    """Tests for ExceptionalValue injection during validation."""

    def test_invalid_integer_triggers_inv(self):
        """Invalid integer values should trigger INV ExceptionalValue."""
        # Arrange
        validator = SDC4Validator('tests/sdc4/schemas/test.xsd')

        # Act
        recovered = validator.validate_with_recovery(
            'tests/sdc4/instances/invalid_int.xml'
        )

        # Assert
        ev_elements = recovered.findall('.//{http://...}INV')
        assert len(ev_elements) == 1
        assert ev_elements[0].find('.//ev-name').text == 'Invalid'

    def test_missing_required_triggers_ni(self):
        """Missing required elements should trigger NI ExceptionalValue."""
        validator = SDC4Validator('tests/sdc4/schemas/test.xsd')
        recovered = validator.validate_with_recovery(
            'tests/sdc4/instances/missing_required.xml'
        )
        ev_elements = recovered.findall('.//{http://...}NI')
        assert len(ev_elements) == 1
```

### Test Coverage Requirements

- **Minimum**: 80% overall coverage
- **SDC4 module**: 90% coverage (critical functionality)
- **New code**: 100% coverage for new features/bug fixes

### Test Data

- Place test schemas in `tests/sdc4/schemas/`
- Place test instances in `tests/sdc4/instances/`
- Keep test files small and focused
- Name test files descriptively: `invalid_integer.xml`, `missing_required_element.xml`

---

## Pull Request Process

### Before Submitting

1. **Create a branch** from `main`
   ```bash
   git checkout -b fix/issue-123-invalid-mapping
   # or
   git checkout -b feature/add-new-exceptional-value
   ```

2. **Make your changes**
   - Follow coding standards
   - Add/update tests
   - Update documentation

3. **Run tests**
   ```bash
   pytest tests/ -v
   ```

4. **Run linters**
   ```bash
   flake8 sdcvalidator
   mypy sdcvalidator
   ```

5. **Update CHANGELOG.rst**
   - Add entry under "Unreleased" section
   - Use present tense: "Add", "Fix", "Update"
   - Reference issue number: `(#123)`

### Submitting Pull Request

1. **Push to your fork**
   ```bash
   git push origin fix/issue-123-invalid-mapping
   ```

2. **Open pull request** on GitHub
   - Use PR template
   - Reference related issues: "Closes #123"
   - Provide clear description of changes
   - Include before/after examples if applicable

3. **Wait for review**
   - Address reviewer feedback
   - Keep PR focused (one feature/fix per PR)
   - Be responsive to comments

### PR Review Criteria

Reviewers check for:

- ✅ Tests pass in CI
- ✅ Code follows style guide
- ✅ Test coverage maintained/improved
- ✅ Documentation updated
- ✅ No breaking changes (or clearly documented)
- ✅ CHANGELOG updated
- ✅ Commit messages are clear

### After Approval

- Maintainer will merge your PR
- Your contribution will be credited in CHANGELOG
- Thank you! 🎉

---

## Release Process

*(For maintainers)*

### Preparing a Release

1. **Update version** in `pyproject.toml`
   ```toml
   version = "4.1.0"
   ```

2. **Update CHANGELOG.rst**
   - Move "Unreleased" items to new version section
   - Add release date
   - Format: `v4.1.0 (2025-11-15)`

3. **Run full test suite**
   ```bash
   pytest tests/ -v --cov=sdcvalidator
   tox  # Test multiple Python versions
   ```

4. **Build package**
   ```bash
   python -m build
   ```

5. **Test installation**
   ```bash
   pip install dist/sdcvalidator-4.1.0.tar.gz
   ```

6. **Commit and tag**
   ```bash
   git add pyproject.toml CHANGELOG.rst
   git commit -m "Release v4.1.0"
   git tag v4.1.0
   git push origin main --tags
   ```

7. **Publish to PyPI**
   ```bash
   python -m twine upload dist/sdcvalidator-4.1.0*
   ```

8. **Create GitHub release**
   - Use tag `v4.1.0`
   - Copy CHANGELOG entries to release notes
   - Attach distribution files

---

## Documentation

### Where to Document

- **README.md** - User-facing quick start, API overview
- **doc/** - Comprehensive Sphinx documentation
  - `doc/usage.rst` - Usage guide
  - `doc/api.rst` - API reference
- **Docstrings** - Inline documentation for functions/classes
- **CLAUDE.md** - Developer/contributor guidance

### Building Documentation

```bash
cd doc
make html
# Open _build/html/index.html
```

### Documentation Style

- Use present tense: "Returns the validated tree"
- Include examples in docstrings
- Cross-reference related functions: `:func:`validate_with_recovery``
- Keep examples simple and self-contained

---

## Specific Contribution Areas

### Adding New ExceptionalValue Mapping Rules

1. **Identify error pattern**
   - What validation error should trigger this?
   - Which ExceptionalValue type is appropriate?

2. **Add mapping rule** in `sdcvalidator/sdc4/error_mapper.py`
   ```python
   def _is_confidential_data_error(error: ValidationError) -> bool:
       """Check if error relates to confidential data."""
       return 'confidential' in str(error.reason).lower()

   # Add to ErrorMapper._rules
   (self._is_confidential_data_error, ExceptionalValueType.MSK)
   ```

3. **Add test** in `tests/sdc4/test_error_mapper.py`
   ```python
   def test_confidential_data_mapped_to_msk(error_mapper):
       error = create_validation_error(reason="Confidential field")
       ev_type = error_mapper.map_error(error)
       assert ev_type == ExceptionalValueType.MSK
   ```

4. **Update documentation**
   - Add to README.md ExceptionalValue table
   - Document in `doc/usage.rst`

### Performance Optimization

1. **Profile first**
   ```bash
   python profiling/profile_decoder.py
   ```

2. **Identify bottleneck**
   - Is it validation? Recovery? XML parsing?

3. **Optimize**
   - Keep changes isolated
   - Don't break API
   - Measure improvement

4. **Add benchmark test**
   ```python
   def test_large_file_performance(benchmark):
       validator = SDC4Validator('schema.xsd')
       result = benchmark(validator.validate_with_recovery, 'large.xml')
   ```

### Bug Fixes

1. **Write failing test** first
   ```python
   def test_issue_123_invalid_xpath():
       """Test for issue #123: Invalid XPath in recovery."""
       validator = SDC4Validator('schema.xsd')
       # This should not raise XPathError
       recovered = validator.validate_with_recovery('instance.xml')
   ```

2. **Fix the bug**

3. **Verify** test now passes

4. **Submit PR** with test + fix

---

## Communication

### GitHub Issues

Use for:
- Bug reports
- Feature requests
- Questions about implementation

### GitHub Discussions

Use for:
- General questions
- Design discussions
- Best practices

### Email

For private matters: contact@axius-sdc.com

---

## Recognition

Contributors are recognized in:
- **CHANGELOG.rst** - Credited for contributions
- **README.md** - Contributors section
- **GitHub** - Contribution graph

---

## License

By contributing, you agree that your contributions will be licensed under the **MIT License**, the same license as this project.

**Copyright**:
- (c) 2025 Axius-SDC, Inc. (SDC4 integration)
- (c) 2016-2024 SISSA (core xmlschema)

---

## Getting Help

- **GitHub Issues** - https://github.com/Axius-SDC/sdcvalidator/issues
- **GitHub Discussions** - https://github.com/Axius-SDC/sdcvalidator/discussions
- **Email** - contact@axius-sdc.com
- **CLAUDE.md** - Developer guidance (this repo)

---

**Thank you for contributing to SDCvalidator!** Together we make SDC4 data quality tracking better for everyone. 🚀
