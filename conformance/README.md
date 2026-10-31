# SDC4 validation conformance suite

sdcvalidator is the reference implementation of SDC4 validation. This suite is what any other
implementation (in TypeScript, Java, or anything else) must reproduce to call its results the same.
Without it, "validated" could mean different things in different languages.

## What is compared

For each case in `manifest.json`: a published SDC4 model (`models/`), a record (`cases/`), and the
expected result (`expected/<case>.json`). An implementation conforms when, for every case, it gives:

- `valid`: the same verdict;
- `structural`: the same structural (Tier 1) errors, by path;
- `semantic`: the same semantic (Tier 2) errors, by path, each with the same ISO 21090 ExceptionalValue
  code (`INV`, `NI`, ...);
- `recover`: the same recovery outcome. Either `{"rejected": "structural"}` (a structural error stops
  recovery), or `ok`, the values covered (path, code, and whether the ExceptionalValue was inserted
  now or was already in the record) and the errors no ExceptionalValue covers;
- `recovered` (when recovery inserted anything): a recovered record whose W3C Canonical XML 2.0 form is
  identical to the file named.

Paths are the element paths sdcvalidator reports: Clark notation (`/{namespace}local/...`), without
position indexes, so lists are compared as sorted lists. Error messages are **not** compared: they
are the wording of the XML Schema library underneath, not part of the result.

Every model's XSD includes the reference model from
`https://semanticdatacharter.com/ns/sdc4/sdc4.xsd`. `reference/sdc4.xsd` is a byte-identical copy
(checked 2026-10-31), so the suite runs offline: resolve that URL to the local file.

## The cases

Eight published business-document models (Order, Order Response, Despatch Advice, Receipt Advice,
Invoice, Credit Note, Remittance Advice, and a second supplier's Order), with real Governed Data
Records from [sdc-gdr2ubl](https://github.com/SemanticDataCharter/sdc-gdr2ubl)'s samples (Apache-2.0).
For each model:

| Case | What it is |
|---|---|
| `valid-1`, `valid-2` | Real records, unchanged |
| `m-quantity-type`, `m-count-type` | A decimal or integer value that is not one |
| `m-date`, `m-datetime`, `m-time` | A temporal value that is not one |
| `m-token`, `m-boolean` | A value outside its enumeration |
| `m-string-empty` | An empty string where a pattern requires content |
| `m-two-errors` | Two semantic errors in one record |
| `s-unknown-element`, `s-missing-label`, `s-duplicate-label` | Structural errors |
| `ev-existing` | A record that already carries an ExceptionalValue |

Each mutation changes the first matching element in document order, so the cases are reproducible
(`tools/build_cases.py`). The real records are large (up to about 150 KB), which makes the suite about
30 MB of plain text; that is the price of testing against records as they are actually written.

## Maintaining it

```bash
python conformance/tools/expected.py --check   # run in CI by tests/test_conformance.py
python conformance/tools/expected.py           # rewrite expected/ and manifest.json
python conformance/tools/build_cases.py /path/to/sdc-gdr2ubl/samples   # rebuild the cases
```

If `--check` fails, sdcvalidator's results changed. Regenerate only when the change is intended,
record it in the CHANGELOG, and tell the other implementations: every one of them must then meet
the new expectations before its next release.

## Known behaviour recorded as it is (2026-10-31)

The suite records what sdcvalidator does today, including two mappings that differ from its own rule
table: a value outside an enumeration (`m-token`, `m-boolean`) is covered with `NI`, not `OTH`, and a
pattern violation (`m-string-empty`) with `NI`, not `INV`. The XML Schema library now words these
errors as "value must be one of [...]" and "value doesn't match any pattern of [...]", which the
mapper's phrases no longer match. Correcting the mapper will change these expectations, deliberately.
