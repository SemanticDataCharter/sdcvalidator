# Pull Request

## Description

**What does this PR do?**

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Test improvement

## Related Issues

**Closes #(issue number)**

**Related issues/PRs**: (link if applicable)

## Changes Made

**Summary of changes**:

1.
2.
3.

## Testing

### Test Coverage

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Test coverage maintained/improved: `pytest --cov=sdcvalidator`
- [ ] Added tests for new code
- [ ] Existing tests updated (if behavior changed)

### Linting

- [ ] Code passes flake8: `flake8 sdcvalidator`
- [ ] Code passes mypy: `mypy sdcvalidator`
- [ ] Code follows PEP 8 style guide

### Manual Testing

**How has this been manually tested?**

```python
# Example of manual test performed
from sdcvalidator import SDC4Validator

validator = SDC4Validator('tests/sdc4/schemas/test.xsd')
result = validator.validate_with_recovery('tests/sdc4/instances/test.xml')
# ... verification
```

### Test Environment

- **Python version**: (e.g., 3.11.5)
- **Operating System**: (e.g., Ubuntu 22.04)
- **Dependencies**: (any special dependencies?)

## Documentation

- [ ] Updated relevant documentation
- [ ] Updated docstrings (if API changed)
- [ ] Updated README.md (if user-facing change)
- [ ] Updated CHANGELOG.rst
- [ ] Updated doc/ (if significant feature)

## Checklist

- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md)
- [ ] I have read [CLAUDE.md](../CLAUDE.md) (for developers)
- [ ] My code follows the coding standards
- [ ] I have performed a self-review of my changes
- [ ] I have commented my code where needed
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] I have updated CHANGELOG.rst under "Unreleased"

## For New Features

- [ ] Added docstrings with examples
- [ ] Added usage example in README (if user-facing)
- [ ] Considered backward compatibility
- [ ] Considered performance implications

## For Bug Fixes

- [ ] Added regression test to prevent future recurrence
- [ ] Verified fix doesn't break existing functionality
- [ ] Root cause documented in commit message or PR description

## For ExceptionalValue Mapping Changes

- [ ] Mapping rule clearly documented
- [ ] Test cases cover all error patterns
- [ ] Updated ExceptionalValue table in README
- [ ] Verified against ISO 21090 NULL Flavor taxonomy

## Breaking Changes

**If this is a breaking change, explain**:

- What breaks?
- How should users update their code?
- Migration guide provided?

## Performance Impact

**If this affects performance**:

- [ ] Benchmarked before/after
- [ ] Performance improvement: X%
- [ ] Performance regression justified by: (explain)

## Screenshots (if applicable)

**Add screenshots to help explain changes (e.g., CLI output, error messages)**

## Additional Notes

**Any additional context or information for reviewers**:

---

## For Reviewers

**Areas that need special attention**:

**Questions for reviewers**:
