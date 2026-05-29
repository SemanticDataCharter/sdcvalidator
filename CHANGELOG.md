# Changelog

All notable changes to `sdcvalidator` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
semantic versioning.

## [4.3.0]

### Added
- **ExceptionalValue recovery** (the SDC4 "quarantine-and-tag" pattern). Semantic
  (Tier 2) validation errors on data-bearing elements are now recovered by
  inserting an ISO 21090 ExceptionalValue element instead of failing outright.
  This capability previously lived outside the open library; it is now part of
  FOSS `sdcvalidator` so every consumer and every generated application gets it.
  - `SDC4Validator.validate_with_recovery()` and `save_recovered_xml()`.
  - Module-level `validate_with_recovery(schema_path, xml_path, ...)` convenience function.
  - `ExceptionalValueType` and `EXCEPTIONAL_VALUE_TYPES` (the 16 ISO 21090 NULL Flavors).
  - `ErrorMapper` (maps a semantic error to an ExceptionalValue type) and
    `InstanceModifier` (inserts the EV element at the correct position).
  - `SDC4StructuralValidationError` raised on Tier 1 (structural) errors, which
    are never recovered.
  - `etree_tostring` re-exported from `xmlschema` for serializing recovered trees.
  - `SDC4Validator.iter_errors_with_mapping()`.

### Changed
- `SDC4Validator.validate_and_report()` now returns a **superset** report that
  keeps the existing `structural_errors`/`semantic_errors` breakdown and adds a
  flat `errors` list (with ExceptionalValue mapping) plus
  `exceptional_value_type_counts`. Existing keys are unchanged.
- `SDC4Validator.validate()`, `validate_structure()`, and `iter_errors()` now
  accept an `ElementTree.Element` or `xmlschema.XMLResource` in addition to a
  file path.
- Structural-vs-semantic tiering is now decided in one place: `ErrorMapper`
  delegates `is_structural_error()` to `ErrorClassifier`.

### Note
- This restores the `ExceptionalValueType` / `validate_with_recovery` /
  `etree_tostring` API that earlier consumers (including generated applications)
  import. The 4.1.0–4.2.1 line was structural-only; pin `>=4.3.0` to require the
  recovery capability.
