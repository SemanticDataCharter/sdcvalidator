#
# Copyright 2026 Semantic Data Charter Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
"""
4.6.0: recovery keeps the ExceptionalValues a record already carries, reports
what it covered as data, and never skips an error it cannot cover.

Before 4.6.0, `validate_with_recovery` removed every ExceptionalValue in the
record first (so a refusal written where the record was made was lost whenever
another value failed) and logged and skipped an error no ExceptionalValue maps
to (so the record came back "recovered" with an invalid value nobody marked).
"""
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from sdcvalidator import (SDC4UnrecoverableError, SDC4Validator, Recovery, RecoveryResult)

SCHEMA = Path(__file__).parent / "test_data" / "dm-jsi5yxnvzsmsisgn2bvelkni.xsd"
SDC4 = "https://semanticdatacharter.com/ns/sdc4/"
ASKR = '<sdc4:ASKR><ev-name>Asked and Refused</ev-name></sdc4:ASKR>'


def record(count="5", ev="", units_label="Adult Population_units"):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<sdc4:dm-jsi5yxnvzsmsisgn2bvelkni xmlns:sdc4="{SDC4}">
    <dm-label>StatePopulation</dm-label>
    <dm-language>en-US</dm-language>
    <dm-encoding>utf-8</dm-encoding>
    <sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
        <label>StatePopulation Data Cluster</label>
        <sdc4:ms-ahfdavxt7dpx960rqi1qtb0l>
            <sdc4:ms-q1ey1sf5otsa97e76kb06hco>
                <label>Adult Population</label>
                {ev}
                <xdcount-value>{count}</xdcount-value>
                <xdcount-units>
                    <label>{units_label}</label>
                    <xdstring-value>people</xdstring-value>
                </xdcount-units>
            </sdc4:ms-q1ey1sf5otsa97e76kb06hco>
        </sdc4:ms-ahfdavxt7dpx960rqi1qtb0l>
    </sdc4:ms-wnpz4qyrk369gnsivfsmysdf>
</sdc4:dm-jsi5yxnvzsmsisgn2bvelkni>
'''


@pytest.fixture(scope="module")
def validator():
    if not SCHEMA.exists():
        pytest.skip("SDC4 example schema not found")
    return SDC4Validator(SCHEMA, validation="lax")


def element(xml):
    return ET.fromstring(xml)


def evs(tree):
    comp = next(e for e in tree.getroot().iter() if e.tag == f"{{{SDC4}}}ms-q1ey1sf5otsa97e76kb06hco")
    return [c.tag.split("}")[1] for c in comp if c.tag.startswith(f"{{{SDC4}}}")]


def test_recover_reports_what_it_covered_as_data(validator):
    r = validator.recover(element(record(count="not_a_number")))
    assert isinstance(r, RecoveryResult) and r.ok
    (rec,) = r.recoveries
    assert isinstance(rec, Recovery)
    assert (rec.code, rec.name, rec.inserted) == ("INV", "Invalid", True)
    assert "not_a_number" in rec.reason and rec.path.endswith("xdcount-value")
    assert evs(r.tree) == ["INV"]


def test_a_valid_record_has_nothing_to_recover(validator):
    r = validator.recover(element(record()))
    assert r.ok and r.recoveries == [] and evs(r.tree) == []


def test_an_exceptional_value_written_at_the_source_is_kept(validator):
    tree = validator.validate_with_recovery(element(record(ev=ASKR)), save=False)
    assert evs(tree) == ["ASKR"]


def test_one_already_covering_a_bad_value_is_kept_and_nothing_is_added(validator):
    r = validator.recover(element(record(count="not_a_number", ev=ASKR)))
    (rec,) = r.recoveries
    assert (rec.code, rec.inserted) == ("ASKR", False)
    assert evs(r.tree) == ["ASKR"], "one ExceptionalValue per value"


def test_removing_existing_ones_is_still_available_when_asked(validator):
    r = validator.recover(element(record(count="not_a_number", ev=ASKR)), remove_existing_ev=True)
    assert evs(r.tree) == ["INV"] and r.recoveries[0].inserted


def test_an_error_nothing_covers_is_returned_not_skipped(validator):
    r = validator.recover(element(record(units_label="Count Units")))
    assert not r.ok and len(r.unrecoverable) == 1
    assert "fixed value" in r.unrecoverable[0].reason


def test_validate_with_recovery_raises_rather_than_return_an_unmarked_invalid_value(validator):
    with pytest.raises(SDC4UnrecoverableError) as exc:
        validator.validate_with_recovery(element(record(units_label="Count Units")), save=False)
    assert exc.value.error_count == 1 and "fixed value" in str(exc.value)


def test_the_source_is_never_mutated(validator):
    root = element(record(count="not_a_number", ev=ASKR))
    before = ET.tostring(root)
    validator.recover(root)
    assert ET.tostring(root) == before
