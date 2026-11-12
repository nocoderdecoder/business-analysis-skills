#!/usr/bin/env python3
"""Recalculate explicit report claims against a CSV. Does not interpret prose."""
import argparse
import csv
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


class Uncheckable(ValueError):
    pass


def number(value):
    if isinstance(value, bool) or value is None:
        raise Uncheckable('A numeric value is required')
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise Uncheckable(f'Not a plain decimal number: {value!r}') from exc
    if not result.is_finite():
        raise Uncheckable('Non-finite numbers are not supported')
    return result


def load_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)):
            raise ValueError('CSV requires unique column names')
        rows = []
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'Row {line}: column count differs from the header')
            rows.append((line, row))
    return fields, rows


def select(fields, rows, selector):
    if not isinstance(selector, dict) or set(selector) - {'column', 'where'}:
        raise Uncheckable('Selector accepts column and optional where only')
    column, filters = selector.get('column'), selector.get('where', {})
    if column not in fields or not isinstance(filters, dict) or set(filters) - set(fields):
        raise Uncheckable('Unknown column or invalid filter')
    if any(not isinstance(value, str) for value in filters.values()):
        raise Uncheckable('Filter values must be strings matching the CSV exactly')
    matched = [(line, row) for line, row in rows if all(row[k] == v for k, v in filters.items())]
    if not matched:
        raise Uncheckable(f'No rows match {filters}')
    total = sum((number(row[column]) for _, row in matched), Decimal(0))
    return total, {'column': column, 'where': filters, 'source_rows': [line for line, _ in matched], 'sum': str(total)}


def divide(numerator, denominator):
    if denominator <= 0:
        raise Uncheckable('Denominator or baseline must be positive')
    return numerator / denominator


def evaluate(fields, rows, claim):
    if not isinstance(claim, dict):
        raise ValueError('Each claim must be an object')
    result = {'id': claim.get('id'), 'text': claim.get('text', ''), 'status': 'uncheckable'}
    evidence = []
    try:
        kind = claim.get('kind')
        keys = {'sum': ['value'], 'difference': ['current', 'baseline'],
                'growth_pct': ['current', 'baseline'], 'ratio_pct': ['numerator', 'denominator'],
                'pp_change': ['current_numerator', 'current_denominator', 'baseline_numerator', 'baseline_denominator']}
        if kind not in keys:
            raise Uncheckable(f'Unsupported calculation: {kind!r}')
        values = {}
        for key in keys[kind]:
            if key not in claim:
                raise Uncheckable(f'Missing selector: {key}')
            values[key], source = select(fields, rows, claim[key])
            evidence.append({'operand': key, **source})
        if kind == 'sum':
            calculated = values['value']
        elif kind == 'difference':
            calculated = values['current'] - values['baseline']
        elif kind == 'growth_pct':
            calculated = divide(values['current'] - values['baseline'], values['baseline']) * 100
        elif kind == 'ratio_pct':
            calculated = divide(values['numerator'], values['denominator']) * 100
        else:
            calculated = (divide(values['current_numerator'], values['current_denominator']) -
                          divide(values['baseline_numerator'], values['baseline_denominator'])) * 100
        reported, tolerance = number(claim.get('reported')), number(claim.get('tolerance', '0.01'))
        if tolerance < 0:
            raise Uncheckable('Tolerance must be non-negative')
        delta = reported - calculated
        result.update(status='match' if abs(delta) <= tolerance else 'mismatch',
                      reported=str(reported), calculated=str(calculated), difference=str(delta), tolerance=str(tolerance),
                      unit='percentage_points' if kind == 'pp_change' else 'percent' if kind in ('growth_pct', 'ratio_pct') else 'source_units')
    except Uncheckable as exc:
        result['reason'] = str(exc)
    result['evidence'] = evidence
    return result


def check(fields, rows, claims):
    if not isinstance(claims, list) or not claims:
        raise ValueError('Claims must be a non-empty array')
    ids = [claim.get('id') if isinstance(claim, dict) else None for claim in claims]
    if any(not isinstance(key, str) or not key.strip() for key in ids) or len(ids) != len(set(ids)):
        raise ValueError('Claims require unique non-empty string ids')
    results = [evaluate(fields, rows, claim) for claim in claims]
    return {'scope': 'Arithmetic on selected CSV rows. A match does not validate metric definitions, causality, or claims omitted from this file.',
            'counts': {status: sum(item['status'] == status for item in results) for status in ['match', 'mismatch', 'uncheckable']},
            'claims': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('claims')
    parser.add_argument('--out', required=True)
    parser.add_argument('--fail-on-findings', action='store_true')
    args = parser.parse_args()
    try:
        fields, rows = load_csv(args.csv)
        result = check(fields, rows, json.loads(Path(args.claims).read_text(encoding='utf-8')))
        output = Path(args.out)
        if output.resolve() in {Path(args.csv).resolve(), Path(args.claims).resolve()}:
            raise ValueError('Output must not overwrite an input file')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(f"Wrote {output}: {result['counts']}")
        return 1 if args.fail_on_findings and (result['counts']['mismatch'] or result['counts']['uncheckable']) else 0
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
