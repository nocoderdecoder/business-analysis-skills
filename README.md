# Business Analysis Skills

Two agent skills for working with customer feedback and checking numerical reports. Both include Python scripts that make the counts and calculations reproducible.

| Skill | Input | Output |
| --- | --- | --- |
| Customer Feedback Analyst | A CSV of comments or reviews | Topic counts, exact supporting excerpts, and a record-level annotation file |
| Business Report Checker | A report, its CSV source, and mapped claims | Recalculated values, source rows, and a list of mismatches or missing evidence |

The scripts run locally with Python 3.10 or later and need no additional packages. Interpreting comments and mapping report claims are agent-assisted steps. The scripts audit those inputs; they do not replace judgment about what the data means.

## Install

With the Skills CLI:

```sh
npx skills add nocoderdecoder/business-analysis-skills
```

Or clone the repository and copy either folder under `skills/` into a project's `.claude/skills/` directory. Each skill is self-contained. The repository also includes a Claude Code plugin manifest; after cloning, it can be loaded locally with:

```sh
claude --plugin-dir ./business-analysis-skills
```

The package follows the Agent Skills directory format. Host-specific installation is not part of the automated tests; see [the test scope](TESTING.md).

## Try the examples

From the repository root:

```sh
python skills/customer-feedback-analyst/scripts/feedback.py summarize examples/feedback/reviews.csv --topics examples/feedback/topics.json --annotations examples/feedback/annotations.jsonl --out /tmp/feedback-summary.json
python skills/business-report-checker/scripts/check_report.py examples/report-check/sales.csv examples/report-check/claims.json --out /tmp/report-checks.json
```

The [feedback example](examples/feedback/findings.md) includes conflicting opinions and duplicate text. The [report example](examples/report-check/review.md) includes a wrong growth rate, a wrong aggregate conversion rate, and a percentage-point error. All example records are synthetic.

Example requests after installation:

> Analyze these reviews. Show the recurring complaints, the denominator for each count, and the comments supporting each finding.

> Check this monthly report against the sales export. Recalculate its numerical claims and list anything that cannot be checked.

## What the checks establish

The feedback script verifies that annotations refer to real records, excerpts occur in those records, and every eligible record has been reviewed. Topic relevance and sentiment still need review. Counts describe submitted records, not a representative customer population.

The report calculator verifies arithmetic for explicitly mapped claims. It cannot determine whether those mappings capture the report's meaning. A matching total does not establish that the metric definition, chosen time period, or causal explanation is correct.

The scripts make no network requests and collect no telemetry. An agent host may send supplied data to its model provider under that host's settings. Keep confidential material out of public issues and pull requests.

## Development

```sh
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for bug reports and changes. MIT licensed.
