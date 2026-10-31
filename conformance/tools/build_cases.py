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


def _schema(xsd: Path):
    sys.path.insert(0, str(ROOT.parent / 'src'))
    from sdcvalidator.xsd11_restriction import build_xsd11_schema
    reference = str(ROOT / 'reference' / 'sdc4.xsd')
    return build_xsd11_schema(str(xsd), uri_mapper=lambda u: reference if u.endswith('/ns/sdc4/sdc4.xsd') else u)


def _facet(simple_type, name: str):
    """The value of a facet on a simple type or the nearest base type that declares it."""
    qname = '{http://www.w3.org/2001/XMLSchema}' + name
    t = simple_type
    while t is not None and hasattr(t, 'facets'):
        f = (t.facets or {}).get(qname)
        if f is not None:
            return f
        t = getattr(t, 'base_type', None)
    return None


def schema_cases(xsd: Path, record: Path) -> dict:
    """
    Cases a text substitution cannot make, because they depend on the schema: a value that breaks a
    length, range or pattern facet, and a record that fails an assertion. Each walks the record in
    document order, tries the first value (or child) the facet (or assertion) applies to, and keeps
    the first mutation that gives exactly one error, from exactly that constraint.
    """
    import xml.etree.ElementTree as ET
    from decimal import Decimal
    from xmlschema import XMLResource
    from xmlschema.validators import XsdAssert
    from xmlschema.validators import facets as F

    schema = _schema(xsd)
    ET.register_namespace('sdc4', 'https://semanticdatacharter.com/ns/sdc4/')
    ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

    def pairs():
        resource = XMLResource(str(record))
        out = []
        list(schema.iter_errors(resource, validation_hook=lambda e, x: out.append((e, x)) or False))
        return resource, out

    def simple(xsd_element):
        t = xsd_element.type
        return t if t.is_simple() else (t.content if t.has_simple_content() else None)

    def errors_of(root):
        return list(schema.iter_errors(ET.tostring(root, encoding='unicode')))

    def first(candidates, expected_class):
        """The first mutation, in document order, giving one error from ``expected_class``."""
        _, base = pairs()
        for index in range(len(base)):
            for mutate in candidates(base[index]):
                resource, ps = pairs()
                element, xsd_element = ps[index]
                if not mutate(element, xsd_element):
                    continue
                errors = errors_of(resource.root)
                if len(errors) == 1 and isinstance(errors[0].validator, expected_class):
                    return ET.tostring(resource.root, encoding='unicode')
        return None

    def set_text(value):
        def apply(element, xsd_element):
            if len(element):
                return False
            element.text = value
            return True
        return apply

    def length_over(pair):
        st = simple(pair[1])
        f = st is not None and _facet(st, 'maxLength')
        return [set_text('x' * (f.value + 1))] if f else []

    def length_under(pair):
        st = simple(pair[1])
        f = st is not None and _facet(st, 'minLength')
        return [set_text('x' * (f.value - 1))] if f and f.value >= 2 else []

    def above_max(pair):
        st = simple(pair[1])
        f = st is not None and _facet(st, 'maxInclusive')
        return [set_text(str(Decimal(str(f.value)) + 1))] if f else []

    def below_min(pair):
        st = simple(pair[1])
        f = st is not None and _facet(st, 'minInclusive')
        return [set_text(str(Decimal(str(f.value)) - 1))] if f else []

    def off_pattern(pair):
        st = simple(pair[1])
        return [set_text(v) for v in ('!!', 'x', '0', 'xx-')] if st is not None and _facet(st, 'pattern') else []

    def assertion_fails(pair):
        if not getattr(pair[1].type, 'assertions', None) or not len(pair[0]):
            return []

        def remove(i):
            def apply(element, xsd_element):
                kids = list(element)
                if i >= len(kids) or not kids[i].tag.rsplit('}', 1)[-1].startswith('ms-'):
                    return False
                element.remove(kids[i])
                return True
            return apply
        return [remove(i) for i in range(len(pair[0]))]

    found = {
        'm-maxlength': first(length_over, F.XsdMaxLengthFacet),
        'm-minlength': first(length_under, F.XsdMinLengthFacet),
        'm-maxinclusive': first(above_max, F.XsdMaxInclusiveFacet),
        'm-mininclusive': first(below_min, F.XsdMinInclusiveFacet),
        'm-pattern': first(off_pattern, F.XsdPatternFacets),
        'm-assertion': first(assertion_fails, XsdAssert),
    }
    return {name: '<?xml version="1.0" encoding="UTF-8"?>\n' + text for name, text in found.items() if text}


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
        for case, text in schema_cases(ROOT / 'models' / name / xsds[0].name, cases / 'valid-1.xml').items():
            (cases / f'{case}.xml').write_text(text, encoding='utf-8')
        if (cases / 'm-quantity-type.xml').exists():
            ev_existing(ROOT / 'models' / name / xsds[0].name, cases / 'm-quantity-type.xml', cases / 'ev-existing.xml')
        print(name, len(list(cases.glob('*.xml'))), 'cases')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
