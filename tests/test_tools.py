import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

feedback = module('feedback', 'skills/customer-feedback-analyst/scripts/feedback.py')
checker = module('checker', 'skills/business-report-checker/scripts/check_report.py')

class FeedbackTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'examples/feedback'
        self.prepared = feedback.records_from_csv(base / 'reviews.csv')
        self.labels = feedback.load_annotations(base / 'annotations.jsonl')
        self.topics = json.loads((base / 'topics.json').read_text())

    def test_counts_and_denominator(self):
        result = feedback.summarize(self.prepared, self.labels, self.topics)
        self.assertEqual(result['eligible_records'], 11)
        self.assertEqual(result['topics'][0]['topic'], 'delivery')
        self.assertEqual(result['topics'][0]['count'], 6)
        self.assertEqual(result['topics'][0]['share_pct'], 54.55)
        self.assertEqual(result['topics'][0]['sentiment_counts'], {'negative': 2, 'positive': 4})

    def test_duplicate_text_retained_and_flagged(self):
        self.assertEqual(self.prepared['duplicate_text_groups'], [['r08', 'r09']])
        self.assertEqual(self.prepared['input_rows'], 12)
        self.assertEqual(self.prepared['skipped'][0]['id'], 'r11')

    def test_missing_annotation_fails(self):
        with self.assertRaisesRegex(ValueError, 'Missing annotations'):
            feedback.summarize(self.prepared, self.labels[:-1], self.topics)

    def test_invented_quote_fails(self):
        self.labels[0]['labels'][0]['quote'] = 'Everyone loves this product'
        with self.assertRaisesRegex(ValueError, 'exact excerpt'):
            feedback.summarize(self.prepared, self.labels, self.topics)

    def test_unknown_record_fails(self):
        self.labels[0]['id'] = 'nonexistent'
        with self.assertRaisesRegex(ValueError, 'Unknown or repeated'):
            feedback.summarize(self.prepared, self.labels, self.topics)

    def test_duplicate_label_fails(self):
        self.labels[0]['labels'].append(copy.deepcopy(self.labels[0]['labels'][0]))
        with self.assertRaisesRegex(ValueError, 'unknown or repeated topic'):
            feedback.summarize(self.prepared, self.labels, self.topics)

    def test_duplicate_annotation_fails(self):
        self.labels.append(self.labels[0])
        with self.assertRaisesRegex(ValueError, 'Unknown or repeated'):
            feedback.summarize(self.prepared, self.labels, self.topics)

    def test_unknown_topic_fails(self):
        self.labels[0]['labels'][0]['topic'] = 'unlisted'
        with self.assertRaisesRegex(ValueError, 'unknown or repeated topic'):
            feedback.summarize(self.prepared, self.labels, self.topics)

    def test_bad_sentiment_fails(self):
        self.labels[0]['labels'][0]['sentiment'] = 'excellent'
        with self.assertRaisesRegex(ValueError, 'unknown sentiment'):
            feedback.summarize(self.prepared, self.labels, self.topics)

    def test_duplicate_id_and_ragged_csv_fail(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'input.csv'
            for text in ['id,text\nr1,good\nr1,bad\n','id,text\nr1,good,extra\n','id,text\nr1\n','id,text,text\nr1,a,b\n']:
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    feedback.records_from_csv(path)

    def test_all_empty_has_no_misleading_zero_rate(self):
        prepared = {'records': [], 'input_rows': 1, 'skipped': [{'id': 'blank'}], 'duplicate_text_groups': []}
        result = feedback.summarize(prepared, [], {'delivery': 'Delivery timing'})
        self.assertIsNone(result['topics'][0]['share_pct'])

class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.fields, self.rows = checker.load_csv(ROOT / 'examples/report-check/sales.csv')
        self.claims = json.loads((ROOT / 'examples/report-check/claims.json').read_text())

    def test_fixture_findings(self):
        result = checker.check(self.fields, self.rows, self.claims)
        self.assertEqual(result['counts'], {'match': 1, 'mismatch': 3, 'uncheckable': 1})
        self.assertEqual(result['claims'][1]['calculated'], '20.0')

    def test_weighted_ratio(self):
        result = checker.evaluate(self.fields, self.rows, self.claims[2])
        self.assertAlmostEqual(float(result['calculated']), 400 / 6000 * 100)
        self.assertEqual(result['evidence'][0]['source_rows'], [4, 5])

    def test_percentage_points(self):
        result = checker.evaluate(self.fields, self.rows, self.claims[3])
        self.assertAlmostEqual(float(result['calculated']), 2/3)
        self.assertEqual(result['unit'], 'percentage_points')

    def test_missing_period_uncheckable(self):
        result = checker.evaluate(self.fields, self.rows, self.claims[-1])
        self.assertEqual(result['status'], 'uncheckable')
        self.assertIn('No rows', result['reason'])

    def test_zero_and_negative_baselines(self):
        for value in ['0', '-4']:
            rows = [(2, {'period': 'old', 'value': value}), (3, {'period': 'new', 'value': '5'})]
            claim = {'id': 'x', 'kind': 'growth_pct', 'reported': 25, 'baseline': {'column': 'value', 'where': {'period': 'old'}}, 'current': {'column': 'value', 'where': {'period': 'new'}}}
            with self.subTest(value=value):
                self.assertEqual(checker.evaluate(['period', 'value'], rows, claim)['status'], 'uncheckable')

    def test_blank_and_nonfinite_values(self):
        for value in ['', 'NaN', 'Infinity', '1,000', '$10', '10%']:
            with self.subTest(value=value):
                result = checker.evaluate(['value'], [(2, {'value': value})], {'id': 'x', 'kind': 'sum', 'reported': 0, 'value': {'column': 'value'}})
                self.assertEqual(result['status'], 'uncheckable')

    def test_rounding_tolerance(self):
        claim = copy.deepcopy(self.claims[2]); claim.update(reported='6.7', tolerance='0.05')
        self.assertEqual(checker.evaluate(self.fields, self.rows, claim)['status'], 'match')
        claim['tolerance'] = '-1'
        self.assertEqual(checker.evaluate(self.fields, self.rows, claim)['status'], 'uncheckable')

    def test_difference_supports_negative_values(self):
        claim = {'id': 'x', 'kind': 'difference', 'reported': -6000, 'current': self.claims[1]['baseline'], 'baseline': self.claims[1]['current']}
        self.assertEqual(checker.evaluate(self.fields, self.rows, claim)['status'], 'match')

    def test_unknown_selector_is_not_silently_ignored(self):
        claim = copy.deepcopy(self.claims[0]); claim['value']['filter'] = {'month': '2026-10'}
        self.assertEqual(checker.evaluate(self.fields, self.rows, claim)['status'], 'uncheckable')

    def test_duplicate_claim_ids_fail(self):
        with self.assertRaises(ValueError): checker.check(self.fields, self.rows, [self.claims[0], self.claims[0]])

    def test_cli_exit_and_output(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/'checks.json'
            process = subprocess.run([sys.executable, str(ROOT/'skills/business-report-checker/scripts/check_report.py'), str(ROOT/'examples/report-check/sales.csv'), str(ROOT/'examples/report-check/claims.json'), '--out', str(output), '--fail-on-findings'], capture_output=True, text=True)
            self.assertEqual(process.returncode, 1, process.stderr)
            self.assertEqual(json.loads(output.read_text())['counts']['mismatch'], 3)

    def test_input_overwrite_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'source.csv'; source.write_text('value\n1\n')
            claims = Path(d)/'claims.json'; claims.write_text(json.dumps([{'id':'x','kind':'sum','reported':1,'value':{'column':'value'}}]))
            process = subprocess.run([sys.executable, str(ROOT/'skills/business-report-checker/scripts/check_report.py'), str(source), str(claims), '--out', str(source)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(source.read_text(), 'value\n1\n')

class PackagingTests(unittest.TestCase):
    def test_skills_have_frontmatter_and_local_scripts(self):
        for path in (ROOT/'skills').iterdir():
            contents = (path/'SKILL.md').read_text()
            self.assertTrue(contents.startswith('---\nname: '+path.name+'\n'))
            self.assertIn('\ndescription: ', contents)
            self.assertTrue(list((path/'scripts').glob('*.py')))

    def test_manifest(self):
        manifest = json.loads((ROOT/'.claude-plugin/plugin.json').read_text())
        self.assertEqual(manifest['version'], '0.1.0')
        self.assertEqual(manifest['name'], ROOT.name)

if __name__ == '__main__': unittest.main()
