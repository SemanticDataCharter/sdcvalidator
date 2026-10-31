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
| `m-maxlength`, `m-mininclusive`, `m-maxinclusive` | A value that breaks a length or range facet |
| `m-pattern` | A value that breaks a pattern |
| `m-assertion` | A record that fails an XSD 1.1 assertion (the Torvale order model only) |
| `s-unknown-element`, `s-missing-label`, `s-duplicate-label` | Structural errors |
| `ev-existing` | A record that already carries an ExceptionalValue |

Each mutation changes the first matching element in document order, so the cases are reproducible
(`tools/build_cases.py`). The facet and assertion cases are found from the schema: the first value
(or child) the constraint applies to whose mutation gives exactly one error, from exactly that
constraint. A model that has no such value gets no such case, so the counts differ by model (151 cases
in all). The real records are large (up to about 150 KB), which makes the suite about 30 MB of plain
text; that is the price of testing against records as they are actually written.

## The ExceptionalValue codes expected (from 4.6.3)

| What failed | Code |
|---|---|
| A value not of its type at all (`abc` for a decimal) | `INV` |
| A pattern, length, range or digits facet; a built-in type's own range; a fixed value | `INV` |
| An assertion | `INV` |
| An enumeration | `OTH` |
| Character data where only elements are allowed | `NA` |
| Any error on a structural element (`label`, `vtb`, `vte`, ...) | none: it cannot be recovered |

sdcvalidator decides these from the constraint xmlschema reports as having failed, not from the
wording of its messages.

## Maintaining it

```bash
python conformance/tools/expected.py --check   # run in CI by tests/test_conformance.py
python conformance/tools/expected.py           # rewrite expected/ and manifest.json
python conformance/tools/build_cases.py /path/to/sdc-gdr2ubl/samples   # rebuild the cases
```

If `--check` fails, sdcvalidator's results changed. Regenerate only when the change is intended,
record it in the CHANGELOG, and tell the other implementations: every one of them must then meet
the new expectations before its next release.

## History

- **4.6.2** (2026-10-31): the suite's first release, 120 cases. It recorded sdcvalidator as it then
  was, which mapped every facet violation to `NI`: the mapper matched xmlschema's English messages,
  and their wording had changed.
- **4.6.3**: the mapper decides by the constraint instead; enumerations are `OTH`, the other facets,
  fixed values and assertions `INV`. 31 cases added for length, range, pattern and assertion
  failures, 151 in all.
