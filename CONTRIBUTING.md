# Contributing

Useful contributions include a reproducible counting error, a calculation the checker handles incorrectly, a clearer instruction for an ambiguous case, or an anonymized example that exposes a gap.

Open an issue with the smallest input that reproduces the problem, the actual result, and the expected result. Use synthetic data when the source is confidential. Do not include customer identifiers, account credentials, or internal business records.

For a pull request, explain the behavior being changed and add a regression test when applicable. Run `python -m unittest discover -s tests -v`. Keep sample outputs consistent with the code. Changes to a skill should include an example request that shows why the instruction is needed.

Keep arithmetic checks separate from claims about meaning. Do not silently remove duplicate feedback, infer missing financial values, or use a matching calculation as proof that a report is accurate in every respect.
