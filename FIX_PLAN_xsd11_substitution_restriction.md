# Fix Plan: XSD 1.1 substitution-group restriction (sdcvalidator + xmlschema)

Status: PLAN (2026-07-16). Do not implement until the gold-standard schema corpus
is on this machine and revalidated with Saxon EE + Xerces-J.

## Problem (confirmed against the spec)

SDC4 cluster schemas restrict `ClusterType` (content `label?, Item*`, where `Item`
is an **abstract substitution-group head**) to specific member refs
(`label?, ms-A?, ms-B?, ...`). This is **valid XSD 1.1**:

- XSD 1.1 Part 1 §3.9.6 has **no** "Particle Valid (Restriction)". The XSD 1.0
  particle machinery (`NameAndTypeOK`, `RecurseAsIfGroup`, `NSRecurseCheckCardinality`)
  is **removed** in XSD 1.1.
- XSD 1.1 §3.4.6.4 "Content Type Restricts (Complex Content)", clause 1: R restricts
  B iff *every sequence locally valid w.r.t. R is also locally valid w.r.t. B* (a
  subset-of-instances rule; no element-name match required).
- Particle validation: the actual element "is the same as or is in the substitution
  group of the [expected element declaration]". So `Item*` accepts `ms-A`/`ms-B`, and
  therefore R's instances ⊆ B's instances. Valid.

Saxon EE and Xerces-J accept it (Tim validated real SDC4 schemas with both). A real
gold-standard example: `~/GitHub/00_archive/SDC_PRJS/test_data3_sdc_project/sdc_project/
sdc4/mediafiles/dmlib/dm-rb46xg2fk464oqmlmyejpn2j.xsd` (9 specific `ms-` refs, 0
`ref="Item"`).

**xmlschema 4.3.1 is the defect.** It still applies the removed XSD-1.0 rules and
rejects the valid pattern with "the derived group is an illegal restriction",
raised at schema-compile time (XMLSchema11 construction). sdcvalidator is built on
xmlschema and inherits the false rejection, which blocks SDCStudio generation.

## Defect location (grounded)

- xmlschema: `xmlschema/validators/groups.py`
  - `XsdGroup.is_restriction()` (~L679) and `has_occurs_restriction()` (~L280/L1309):
    the XSD-1.0 Recurse-style particle check.
  - The element-level restriction check (the `NameAndTypeOK` equivalent) does NOT
    treat a substitution-group member as a valid restriction of its head element.
- sdcvalidator consumes xmlschema via `XMLSchema11(...)` in `src/sdcvalidator/
  validator.py`, `converters.py`, `schema_checker.py::validate_sdc4_schema_compliance`;
  error classification already exists in `src/sdcvalidator/error_classifier.py`.

## Options

### B' — sdcvalidator-level unblock (RECOMMENDED first; no xmlschema internals)
Build schemas with `validation='lax'` so the false-positive is collected, not raised,
then **filter the known substitution-group "illegal restriction" false positive** out
of the reported errors (classify it in `error_classifier.py`). Recognise it narrowly:
error is the group-restriction error AND the base term is a substitution-group head AND
the derived terms are members of that group; only then treat it as non-fatal.
- Pros: unblocks SDCStudio now; no dependency on xmlschema internals or upstream.
- Cons: relies on lax build; must VERIFY lax mode still yields a usable schema for
  instance validation of the affected clusters. Does not "enforce" that restriction
  in xmlschema (fine: it is valid, and Saxon/Xerces enforce it correctly).
- Risk control: the classifier must be narrow so genuinely-invalid restrictions still
  fail. Negative tests required.

### A — upstream fix + PR to xmlschema (durable, community)
Teach the element-level `is_restriction` that, when `other` is a substitution-group
head, a member element (substitutable for `other`, with a type validly derived as a
restriction and compatible occurrences) is a valid restriction, per §3.4.6.4.
- Pros: correct root fix; benefits everyone; removes B' eventually.
- Cons: upstream review/merge/release timeline; must not regress other cases.
- PR framing: "XSD 1.1 §3.9.6 defines complex-content restriction via §3.4.6.4
  (subset of locally-valid instances), not the removed XSD-1.0 particle rules;
  xmlschema still applies NameAndTypeOK and rejects valid substitution-group
  restrictions. Repro + fix + tests attached."

### B — vendored subclass/monkeypatch in sdcvalidator (bridge, only if B' insufficient)
Override the element `is_restriction` behavior when constructing `XMLSchema11`.
- Pros: enforces correctly without waiting for upstream.
- Cons: couples to xmlschema internals; fragile across versions. Prefer B' unless
  lax-mode instance validation proves inadequate.

## Recommended sequence
1. Land B' now (behind the gold-standard corpus as the test oracle) → SDCStudio
   unblocked; bump sdcvalidator patch version; SDCStudio/Sov floor to it.
2. Do A in parallel: fork xmlschema, fix, test, PR upstream with the §3.4.6.4 citation.
3. On upstream merge+release: drop B', pin `xmlschema>=<fixed>`, release sdcvalidator,
   bump SDCStudio/Sov floors, remove the classifier special-case.

## Test strategy (oracle = the gold-standard corpus, once on this machine)
- POSITIVE: every gold-standard SDC4 schema (Tim's backups + the archived
  `dm-rb46xg2fk464oqmlmyejpn2j.xsd`) MUST compile/validate under the fixed
  sdcvalidator. Cross-check they pass Saxon EE + Xerces-J.
- NEGATIVE (critical): schemas that SHOULD fail restriction must STILL fail —
  restricting to a NON-member element, or to a member whose type is not validly
  derived, or with incompatible occurrences. The fix must not become "accept any
  restriction".
- REGRESSION: xmlschema's own test suite (for A) and the W3C XSD 1.1 test suite if
  available; sdcvalidator unit tests for both the cluster-restriction accept case and
  the negative cases.

## Open questions for Tim
1. How to manage the gold-standard corpus (repo location, versioning) — decide before
   wiring it as the test oracle.
2. Scope of A: targeted substitution-group allowance (minimal, covers SDC) vs a fuller
   §3.4.6.4 subset implementation. Recommend targeted + spec-cited.
3. Whether B' lax-mode schemas are adequate for downstream instance validation of
   clusters, or B is required as the bridge.
