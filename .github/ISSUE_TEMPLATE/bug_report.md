---
name: Bug Report
about: Report a bug in SDCvalidator
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

**Clear and concise description of the bug**

## Environment

- **SDCvalidator version**: (e.g., 4.0.1)
- **Python version**: (e.g., 3.11.5)
- **Operating System**: (e.g., Ubuntu 22.04, Windows 11, macOS 14)
- **Installation method**: (e.g., pip, source)

## Category

- [ ] Validation error (incorrect validation result)
- [ ] ExceptionalValue injection issue
- [ ] Error mapping problem
- [ ] CLI issue
- [ ] Performance issue
- [ ] Installation/dependency issue
- [ ] Documentation issue
- [ ] Other (specify)

## Steps to Reproduce

```python
# Minimal code to reproduce the issue
from sdcvalidator import SDC4Validator

validator = SDC4Validator('schema.xsd')
# ... rest of reproduction code
```

1. Step 1
2. Step 2
3. Step 3

## Expected Behavior

What should happen:

## Actual Behavior

What actually happens:

## Error Output

<details>
<summary>Full error message and stack trace</summary>

```
Paste full error output here
```

</details>

## Additional Context

**Schema File** (if relevant):
<details>
<summary>schema.xsd</summary>

```xml
<!-- Paste schema here or attach file -->
```

</details>

**Instance File** (if relevant):
<details>
<summary>instance.xml</summary>

```xml
<!-- Paste instance here or attach file -->
```

</details>

**Other context**:
- Any workarounds you've found?
- Does this work in a different Python version?
- Related issues?

## Proposed Solution

If you have ideas for fixing this:
