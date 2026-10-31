"""
Write, or check, the expected result of every conformance case, as sdcvalidator (the reference
implementation) gives it.

    python conformance/tools/expected.py          # rewrite conformance/expected/
    python conformance/tools/expected.py --check  # exit 1 if sdcvalidator no longer gives the committed results

Another implementation passes the suite when, for every case in ``manifest.json``, it gives the same
verdict, the same errors (path and tier; the ExceptionalValue code for semantic errors), the same
recovery outcome, and a recovered record whose canonical form (W3C C14N 2.0) is identical. Error
messages are not compared: they are xmlschema's wording, not part of the result.
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'src'))

import sdcvalidator  # noqa: E402
from sdcvalidator import SDC4Validator  # noqa: E402
from sdcvalidator.exceptions import SDC4StructuralValidationError, SDC4UnrecoverableError  # noqa: E402
from sdcvalidator.xsd11_restriction import build_xsd11_schema  # noqa: E402

REFERENCE_MODEL = ROOT / 'reference' / 'sdc4.xsd'
REFERENCE_MODEL_URL = 'https://semanticdatacharter.com/ns/sdc4/sdc4.xsd'


def local_reference_model(url: str) -> str:
    """Resolve the reference model's published URL to the copy in this suite, so it runs offline."""
    return str(REFERENCE_MODEL) if url == REFERENCE_MODEL_URL else url


def canonical(tree: ET.ElementTree) -> str:
    return ET.canonicalize(ET.tostring(tree.getroot(), encoding='unicode'), strip_text=False)


def result_for(validator: SDC4Validator, record: Path, case_id: str):
    """The comparable result for one record, and the recovered record's canonical text if one is produced."""
    result = validator.validate(str(record))
    out = {
        'valid': result.is_valid,
        'structural': sorted(e.path for e in result.structural_errors),
        'semantic': sorted(
            ({'path': e.path, 'ev': ev.code if (ev := validator.error_mapper.map_error(e)) else None}
             for e in result.semantic_errors),
            key=lambda e: (e['path'], e['ev'] or ''),
        ),
    }
    recovered_text = None
    try:
        recovery = validator.recover(str(record))
        out['recover'] = {
            'ok': recovery.ok,
            'recoveries': sorted(
                ({'path': r.path, 'code': r.code, 'inserted': r.inserted} for r in recovery.recoveries),
                key=lambda r: (r['path'], r['code']),
            ),
            'unrecoverable': sorted(e.path for e in recovery.unrecoverable),
        }
        if recovery.inserted:
            recovered_text = canonical(recovery.tree)
            out['recovered'] = f'expected/{case_id}.recovered.xml'
    except SDC4StructuralValidationError:
        out['recover'] = {'rejected': 'structural'}
    except SDC4UnrecoverableError:
        out['recover'] = {'rejected': 'unrecoverable'}
    return out, recovered_text


def main(check: bool) -> int:
    manifest = {'sdcvalidator': sdcvalidator.__version__, 'reference_model': 'reference/sdc4.xsd', 'cases': []}
    mismatches = []
    for model_dir in sorted((ROOT / 'models').iterdir()):
        xsd = next(model_dir.glob('dm-*.xsd'))
        validator = SDC4Validator(build_xsd11_schema(str(xsd), uri_mapper=local_reference_model))
        for record in sorted((ROOT / 'cases' / model_dir.name).glob('*.xml')):
            case_id = f'{model_dir.name}/{record.stem}'
            out, recovered_text = result_for(validator, record, case_id)
            entry = {
                'id': case_id,
                'model': str(xsd.relative_to(ROOT)),
                'record': str(record.relative_to(ROOT)),
                'expected': f'expected/{case_id}.json',
            }
            manifest['cases'].append(entry)
            expected_path = ROOT / entry['expected']
            text = json.dumps(out, indent=1, sort_keys=True) + '\n'
            if check:
                if not expected_path.exists() or expected_path.read_text() != text:
                    mismatches.append(case_id)
                elif recovered_text is not None and (
                    (ROOT / out['recovered']).read_text(encoding='utf-8') != recovered_text
                ):
                    mismatches.append(case_id + ' (recovered record)')
            else:
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                expected_path.write_text(text)
                if recovered_text is not None:
                    (ROOT / out['recovered']).write_text(recovered_text, encoding='utf-8')
    if check:
        for m in mismatches:
            print('changed:', m)
        print(f"{len(manifest['cases'])} cases, {len(mismatches)} changed")
        return 1 if mismatches else 0
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    print(f"{len(manifest['cases'])} cases written")
    return 0


if __name__ == '__main__':
    sys.exit(main('--check' in sys.argv))
