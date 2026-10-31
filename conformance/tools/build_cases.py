"""
Build the conformance cases: copy models and valid records, and derive invalid records from them.

Run once, from the repository root, when the corpus changes:

    python conformance/tools/build_cases.py /path/to/sdc-gdr2ubl/samples

The source is sdc-gdr2ubl's Halvorsen samples (Apache-2.0): published SDC4 business-document models
and real Governed Data Records written against them. Every mutation is deterministic (it changes the
first matching element in document order), so rebuilding from the same source gives the same files.
The expected results are not made here; ``expected.py`` asks sdcvalidator for them.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID_PER_MODEL = 2


def replace_first_value(text: str, tag: str, new_value: str):
    """The record with the first ``<tag>...</tag>``'s content replaced, or None if the tag is absent."""
    pattern = re.compile(rf'(<{tag}>)([^<]*)(</{tag}>)')
    if not pattern.search(text):
        return None
    return pattern.sub(lambda m: m.group(1) + new_value + m.group(3), text, count=1)


def first_component_span(text: str):
    """The start of the first ``<sdc4:ms-...>`` element's content (after its opening tag)."""
    m = re.search(r'<sdc4:ms-[a-z0-9]+>', text)
    return m.end() if m else None


def insert_unknown(text: str):
    at = first_component_span(text)
    return None if at is None else text[:at] + '<unexpected-element>x</unexpected-element>' + text[at:]


def remove_first_label(text: str):
    at = first_component_span(text)
    if at is None:
        return None
    m = re.compile(r'\s*<label>[^<]*</label>').search(text, at)
    return None if m is None else text[:m.start()] + text[m.end():]


def duplicate_first_label(text: str):
    at = first_component_span(text)
    if at is None:
        return None
    m = re.compile(r'<label>[^<]*</label>').search(text, at)
    return None if m is None else text[:m.end()] + m.group(0) + text[m.end():]


def two_errors(text: str):
    once = replace_first_value(text, 'xdquantity-value', 'abc')
    return None if once is None else replace_first_value(once, 'xdtemporal-date', '2026-13-45')


# name -> function(record text) -> mutated text or None (not applicable to this record)
MUTATIONS = {
    'm-quantity-type': lambda t: replace_first_value(t, 'xdquantity-value', 'abc'),
    'm-count-type': lambda t: replace_first_value(t, 'xdcount-value', '1.5'),
    'm-date': lambda t: replace_first_value(t, 'xdtemporal-date', '2026-13-45'),
    'm-datetime': lambda t: replace_first_value(t, 'xdtemporal-datetime', 'yesterday'),
    'm-time': lambda t: replace_first_value(t, 'xdtemporal-time', '25:61:00'),
    'm-token': lambda t: replace_first_value(t, 'xdtoken-value', 'not-a-listed-value'),
    'm-string-empty': lambda t: replace_first_value(t, 'xdstring-value', ''),
    'm-boolean': lambda t: replace_first_value(t, 'true-value', 'maybe')
    or replace_first_value(t, 'false-value', 'maybe'),
    'm-two-errors': two_errors,
    's-unknown-element': insert_unknown,
    's-missing-label': remove_first_label,
    's-duplicate-label': duplicate_first_label,
}


def ev_existing(xsd: Path, invalid_record: Path, out: Path):
    """A record that already carries an ExceptionalValue: sdcvalidator's recovery of an invalid one."""
    import xml.etree.ElementTree as ET
    sys.path.insert(0, str(ROOT.parent / 'src'))
    from sdcvalidator import SDC4Validator
    from sdcvalidator.xsd11_restriction import build_xsd11_schema
    reference = str(ROOT / 'reference' / 'sdc4.xsd')
    schema = build_xsd11_schema(str(xsd), uri_mapper=lambda u: reference if u.endswith('/ns/sdc4/sdc4.xsd') else u)
    ET.register_namespace('sdc4', 'https://semanticdatacharter.com/ns/sdc4/')
    ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    recovery = SDC4Validator(schema).recover(str(invalid_record))
    recovery.tree.write(out, encoding='utf-8', xml_declaration=True)


def main(samples: Path):
    for model_dir in sorted(p for p in samples.iterdir() if p.is_dir()):
        xsds = sorted(model_dir.glob('dm-*.xsd'))
        records = sorted((model_dir / 'records').glob('*.xml'))
        if len(xsds) != 1 or not records:
            continue
        name = model_dir.name
        (ROOT / 'models' / name).mkdir(parents=True, exist_ok=True)
        shutil.copy2(xsds[0], ROOT / 'models' / name / xsds[0].name)
        cases = ROOT / 'cases' / name
        cases.mkdir(parents=True, exist_ok=True)
        for n, record in enumerate(records[:VALID_PER_MODEL], start=1):
            shutil.copy2(record, cases / f'valid-{n}.xml')
        source = records[0].read_text(encoding='utf-8')
        for case, mutate in MUTATIONS.items():
            mutated = mutate(source)
            if mutated is not None and mutated != source:
                (cases / f'{case}.xml').write_text(mutated, encoding='utf-8')
        if (cases / 'm-quantity-type.xml').exists():
            ev_existing(ROOT / 'models' / name / xsds[0].name, cases / 'm-quantity-type.xml', cases / 'ev-existing.xml')
        print(name, len(list(cases.glob('*.xml'))), 'cases')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
