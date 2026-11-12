# Claim format

The input is a non-empty JSON array. Each claim needs a unique string `id`, the exact report `text`, a `kind`, a numeric `reported` value, and the selectors required for its calculation. Include report locations in the text or a separate ledger. Decimal strings preserve precision.

A selector has a `column` and an optional `where` map. Filters match CSV strings exactly. The selected numeric column is summed across all matching rows. Source row numbers include the header as row 1.

```json
{
  "id": "revenue-growth",
  "text": "Revenue increased by 25% in October.",
  "kind": "growth_pct",
  "reported": "25",
  "tolerance": "0.05",
  "baseline": {"column": "revenue", "where": {"month": "2026-09"}},
  "current": {"column": "revenue", "where": {"month": "2026-10"}}
}
```

| Kind | Selectors | Calculation |
| --- | --- | --- |
| `sum` | `value` | Sum of selected values |
| `difference` | `current`, `baseline` | Current minus baseline |
| `growth_pct` | `current`, `baseline` | 100 x (current - baseline) / baseline |
| `ratio_pct` | `numerator`, `denominator` | 100 x numerator / denominator |
| `pp_change` | `current_numerator`, `current_denominator`, `baseline_numerator`, `baseline_denominator` | Current ratio minus baseline ratio, multiplied by 100 |

`reported: 25` means 25% for `growth_pct` and `ratio_pct`, and 25 percentage points for `pp_change`. It does not mean 0.25. Sum and difference use the source column's units.

Tolerance is an absolute difference in the output unit. The default is 0.01. Set it from the precision of the original report; for example, a figure rounded to one decimal place can differ by up to 0.05. Record any larger tolerance and its reason.

No matching rows, blank numeric values, an unsupported calculation, or a non-positive divisor produce `uncheckable`. Negative values are allowed in sums and differences. The script does not check data uniqueness, fiscal-calendar alignment, statistical significance, or causal claims.

Exit codes: 0 for a completed run, 1 when `--fail-on-findings` is used and findings remain, 2 for an invalid input file or CLI error. Findings are written before an exit code of 1.
