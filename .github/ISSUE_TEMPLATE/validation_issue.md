---
name: Validation Issue
about: Report incorrect validation behavior (false positive or false negative)
title: '[VALIDATION] '
labels: validation, bug
assignees: ''
---

## Validation Issue

**Is this a false positive (valid data rejected) or false negative (invalid data accepted)?**

- [ ] False positive - valid data is rejected
- [ ] False negative - invalid data is accepted
- [ ] Incorrect error message

## Model and Instance

**Model XSD**: (attach or paste the relevant schema section)

```xml
<!-- Relevant XSD here -->
```

**Instance XML**: (attach or paste the instance)

```xml
<!-- Instance XML here -->
```

## Expected Validation Result

- **Should validate**: yes / no
- **Expected errors**: (if should fail, what errors are expected)

## Actual Validation Result

- **Validates**: yes / no
- **Actual errors**:

```
Paste validation output here
```

## SDC Reference Model Type

Which RM type is involved?

- [ ] XdStringType
- [ ] XdOrdinalType
- [ ] XdQuantityType
- [ ] XdTemporalType
- [ ] XdBooleanType
- [ ] XdFileType
- [ ] XdLinkType
- [ ] ClusterType
- [ ] DMType
- [ ] AuditType
- [ ] AttestationType
- [ ] PartyType
- [ ] ParticipationType
- [ ] Other (specify)

## Environment

- **Python**: (e.g., 3.12.1)
- **sdcvalidator version**: (e.g., 4.0.0)

## Additional Context

Any other relevant information:
