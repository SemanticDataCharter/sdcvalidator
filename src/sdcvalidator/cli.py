#
# Copyright 2025 Semantic Data Charter Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
"""
CLI entry points for sdcvalidator.

Three commands:
- sdcvalidate: Validate XML against XSD schema
- sdcvalidator-xml2json: Convert XML to JSON
- sdcvalidator-json2xml: Convert JSON to XML
"""

import argparse
import json
import sys

from . import __version__


def validate_main():
    """
    CLI: Validate an XML file against an XSD schema.

    Exit codes:
        0 — valid
        1 — semantic errors only (Tier 2)
        2 — structural errors (Tier 1)
    """
    parser = argparse.ArgumentParser(
        prog='sdcvalidate',
        description='Validate an XML instance against an SDC4 XSD schema.',
    )
    parser.add_argument('schema', help='Path to the XSD schema file')
    parser.add_argument('xml', help='Path to the XML instance file')
    parser.add_argument(
        '--no-compliance-check',
        action='store_true',
        help='Skip SDC4 compliance check (no-xsd:extension rule)',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        dest='json_output',
        help='Output results as JSON',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    args = parser.parse_args()

    from .validator import SDC4Validator
    from .schema_checker import SDC4SchemaValidationError

    try:
        validator = SDC4Validator(
            args.schema,
            check_sdc4_compliance=not args.no_compliance_check,
        )
    except SDC4SchemaValidationError as e:
        if args.json_output:
            json.dump({'error': str(e), 'exit_code': 2}, sys.stdout, indent=2)
            print()
        else:
            print(f"Schema compliance error:\n{e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        if args.json_output:
            json.dump({'error': str(e), 'exit_code': 2}, sys.stdout, indent=2)
            print()
        else:
            print(f"Error loading schema: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        report = validator.validate_and_report(args.xml)
    except Exception as e:
        if args.json_output:
            json.dump({'error': str(e), 'exit_code': 2}, sys.stdout, indent=2)
            print()
        else:
            print(f"Error validating XML: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json_output:
        json.dump(report, sys.stdout, indent=2, default=str)
        print()
    else:
        if report['valid']:
            print("Valid.")
        else:
            print(f"Invalid: {report['error_count']} error(s)")
            if report['structural_error_count'] > 0:
                print(f"\n  Structural errors (Tier 1): {report['structural_error_count']}")
                for err in report['structural_errors']:
                    print(f"    - [{err['xpath']}] {err['reason']}")
            if report['semantic_error_count'] > 0:
                print(f"\n  Semantic errors (Tier 2): {report['semantic_error_count']}")
                for err in report['semantic_errors']:
                    print(f"    - [{err['xpath']}] {err['reason']}")

    if report['structural_error_count'] > 0:
        sys.exit(2)
    elif report['semantic_error_count'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def xml2json_main():
    """CLI: Convert XML to JSON."""
    parser = argparse.ArgumentParser(
        prog='sdcvalidator-xml2json',
        description='Convert an XML document to JSON using optional schema-aware conversion.',
    )
    parser.add_argument('xml', help='Path to the XML file')
    parser.add_argument(
        '--schema',
        help='Path to XSD schema for type-aware conversion',
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: stdout)',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    args = parser.parse_args()

    from .converters import xml_to_json

    try:
        result = xml_to_json(args.xml, schema_path=args.schema)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
            f.write('\n')
        print(f"Written to {args.output}")
    else:
        print(output)


def json2xml_main():
    """CLI: Convert JSON to XML."""
    parser = argparse.ArgumentParser(
        prog='sdcvalidator-json2xml',
        description='Convert JSON data to XML using an XSD schema.',
    )
    parser.add_argument('json_file', help='Path to the JSON file')
    parser.add_argument('schema', help='Path to XSD schema')
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output XML file path',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    args = parser.parse_args()

    from .converters import json_to_xml

    try:
        json_to_xml(args.json_file, args.schema, args.output)
        print(f"Written to {args.output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
