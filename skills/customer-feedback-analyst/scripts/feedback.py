#!/usr/bin/env python3
"""Prepare feedback records and audit topic annotations. Standard library only."""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SENTIMENTS = {'positive', 'negative', 'mixed', 'neutral'}


def records_from_csv(path, id_column='id', text_column='text'):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError('CSV column names must be unique')
        if id_column not in fields or text_column not in fields:
            raise ValueError(f'CSV requires columns {id_column!r} and {text_column!r}')
        records, skipped, ids, fingerprints = [], [], set(), defaultdict(list)
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'Row {line}: column count differs from the header')
            key = row[id_column].strip()
            if not key or key in ids:
                raise ValueError(f'Row {line}: missing or repeated record id {key!r}')
            ids.add(key)
            text = row[text_column].strip()
            if not text:
                skipped.append({'id': key, 'row': line, 'reason': 'empty text'})
                continue
            record = {'id': key, 'text': text, 'source_row': line,
                      'fields': {k: v for k, v in row.items() if k not in (id_column, text_column)}}
            records.append(record)
            fingerprint = hashlib.sha256(' '.join(text.casefold().split()).encode()).hexdigest()
            fingerprints[fingerprint].append(key)
    return {'records': records, 'skipped': skipped,
            'duplicate_text_groups': [group for group in fingerprints.values() if len(group) > 1],
            'input_rows': len(ids)}


def summarize(prepared, annotations, topics):
    """Every eligible record needs an explicit reviewed entry, including no-topic records."""
    if not isinstance(topics, dict) or not topics or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v.strip() for k, v in topics.items()):
        raise ValueError('Topics must map non-empty topic ids to written definitions')
    records = {row['id']: row for row in prepared['records']}
    seen, counts, sentiments, evidence = set(), Counter(), defaultdict(Counter), defaultdict(list)
    for item in annotations:
        if not isinstance(item, dict):
            raise ValueError('Each annotation must be an object')
        key = item.get('id')
        if key not in records or key in seen:
            raise ValueError(f'Unknown or repeated annotation id: {key!r}')
        seen.add(key)
        labels = item.get('labels')
        if not isinstance(labels, list):
            raise ValueError(f'{key}: labels must be an array, possibly empty')
        assigned = set()
        for label in labels:
            if not isinstance(label, dict):
                raise ValueError(f'{key}: label must be an object')
            topic, sentiment, quote = label.get('topic'), label.get('sentiment'), label.get('quote')
            if topic not in topics or topic in assigned:
                raise ValueError(f'{key}: unknown or repeated topic {topic!r}')
            if sentiment not in SENTIMENTS:
                raise ValueError(f'{key}: unknown sentiment {sentiment!r}')
            if not isinstance(quote, str) or not quote.strip() or quote not in records[key]['text']:
                raise ValueError(f'{key}: quote must be a non-empty exact excerpt from the record')
            assigned.add(topic)
            counts[topic] += 1
            sentiments[topic][sentiment] += 1
            evidence[topic].append({'id': key, 'source_row': records[key]['source_row'],
                                    'quote': quote, 'sentiment': sentiment})
    missing = sorted(set(records) - seen)
    if missing:
        raise ValueError(f'Missing annotations for {len(missing)} records: {", ".join(missing[:8])}')
    denominator = len(records)
    return {'input_rows': prepared['input_rows'], 'eligible_records': denominator,
            'reviewed_records': len(seen), 'skipped': prepared['skipped'],
            'duplicate_text_groups': prepared['duplicate_text_groups'],
            'counting_rule': 'Distinct record ids per topic / all eligible records. A record may have multiple topics. Duplicate text is retained.',
            'topics': [{'topic': topic, 'definition': topics[topic], 'count': counts[topic],
                        'share_pct': round(100 * counts[topic] / denominator, 2) if denominator else None,
                        'sentiment_counts': dict(sentiments[topic]), 'evidence': evidence[topic]}
                       for topic in sorted(topics, key=lambda t: (-counts[t], t))]}


def load_annotations(path):
    items = []
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if line.strip():
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f'Annotation line {number}: {exc.msg}') from exc
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'summarize'])
    parser.add_argument('csv')
    parser.add_argument('--id-column', default='id')
    parser.add_argument('--text-column', default='text')
    parser.add_argument('--annotations')
    parser.add_argument('--topics')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        prepared = records_from_csv(args.csv, args.id_column, args.text_column)
        if args.command == 'summarize':
            if not args.annotations or not args.topics:
                raise ValueError('summarize requires --annotations and --topics')
            result = summarize(prepared, load_annotations(args.annotations),
                               json.loads(Path(args.topics).read_text(encoding='utf-8')))
        else:
            result = prepared
        output = Path(args.out)
        protected = {Path(p).resolve() for p in [args.csv, args.annotations, args.topics] if p}
        if output.resolve() in protected:
            raise ValueError('Output must not overwrite an input file')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Wrote {output}')
        return 0
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
