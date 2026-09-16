# Changelog

All notable changes to `sdcvalidator` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
semantic versioning.

## [Unreleased]

## [4.5.1] - 2026-09-16

### Fixed

- **★ Instances that fill a type through `xsi:type` now validate.** Every
  input was normalised into a stdlib ElementTree, which resolves prefixes to
  Clark notation and discards the declarations. A prefixed QName appearing as
  content, which is what `xsi:type="sdc4:XdOrdinalType"` is, could then not be
  resolved and xmlschema raised `XMLSchemaKeyError` instead of validating. The
  SDC4 reference model declares `sdc4:XdOrdinal` and its siblings abstract, so
  every reference-model-valid instance that carries a workflow state failed.
  The prefix map is now read from a path or an `XMLResource` source and handed
  to xmlschema. A bare `ET.Element` has already lost its declarations; pass the
  path or an `XMLResource` for such instances.

### Changed

- **Package metadata corrected following a public footprint review (8 September 2026).**
  - PyPI author changed from "Semantic Data Charter Foundation" to **Axius SDC, Inc.**
    No such foundation exists as a legal entity, and a for-profit publishing under a
    Foundation byline reads as open-source-washing in procurement review.
  - `Development Status` classifier raised from `4 - Beta` to
    `5 - Production/Stable`, resolving a contradiction with the README, which
    said "Production-ready." Both statements were public.

  Neither change affects the API or behaviour. Both appear on PyPI at the next release.

## [4.5.0] - 2026-08-13

### Added

- **`sdcvalidator` console-script entry point** mapping to the MCP server
  (`sdcvalidator.mcp_server:main`), so `uvx sdcvalidator` launches the stdio MCP
  server directly. The existing `sdcvalidator-mcp` entry point is retained.
- **MCP registry publishing metadata.** Added a `server.json` (official MCP
  registry format, schema `2025-12-11`) and an `mcp-name` ownership marker in the
  README so the package can be published to the official MCP registry.

## [4.4.1]

### Changed
- `build_xsd11_schema(source, validation='strict', **kwargs)` now forwards extra
  keyword arguments (`uri_mapper`, `base_url`, `locations`, ...) to `XMLSchema11`,
  making it a true drop-in for the `XMLSchema11(...)` constructor. This lets
  consumers (SDCStudio, the VaaS resolver) that pass `uri_mapper`/`base_url`
  replace their direct `XMLSchema11(...)` builds with `build_xsd11_schema(...)`.

### Added
- `build_xsd11_schema` and `is_substitution_group_restriction_false_positive` are
  now exported from the package top level (`from sdcvalidator import ...`), not
  only from the `sdcvalidator.xsd11_restriction` submodule.

## [4.4.0]

### Added
- **XSD 1.1 substitution-group restriction support.** SDC4 data models restrict a
  content model that references an abstract substitution-group head (`sdc4:Item`)
  down to the specific member elements a model defines (for example a cluster's
  `label?, Item*` restricted to `label?, ms-A?, ms-B?`). This is valid under
  [XSD 1.1 Part 1 §3.4.6.4](https://www.w3.org/TR/xmlschema11-1/#derivation-ok-restriction),
  which replaced the removed XSD 1.0 particle name-matching rule (`NameAndTypeOK`),
  and is accepted by the Apache Xerces-J XML Schema 1.1 reference build. `xmlschema`
  still applies the removed rule and rejects the construct at build time; this
  release recognises that specific false positive so valid schemas build.
  - `build_xsd11_schema(source, validation='strict')` — builds strict as before,
    and only when a build fails solely on this false positive does it return a lax
    build. Any genuine error stays fatal; `lax`/`skip` pass through unchanged.
  - `is_substitution_group_restriction_false_positive(error)` — a structural
    (not message-only) recogniser: every element in the derived content model must
    either match a base element by name or be a member of a substitution group
    whose head is in the base content model, with compatible occurrences.
  - See `SDCRM/docs/VALIDATORS.md` for the specification citations and processor
    behaviour.

### Changed
- `SDC4Validator` and the `converters` helpers now build schemas through
  `build_xsd11_schema` instead of calling `XMLSchema11` directly.

### Note
- Strict validation is preserved for every case except this one valid construct:
  restricting to a non-member element, or widening occurrences, remains fatal, and
  a lax-built schema still enforces the restriction during instance validation
  (valid members accepted, non-members rejected). Behaviour matches the Xerces-J
  1.1 reference implementation.

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
