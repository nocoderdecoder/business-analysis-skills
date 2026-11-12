# Test scope

The automated tests cover CSV validation, duplicate handling, annotation coverage, exact excerpt checks, deterministic topic counts, arithmetic, weighted rates, zero denominators, missing data, and CLI exit behavior. The example outputs are generated from the bundled synthetic fixtures.

Separate trial tasks exercised both skills on synthetic fixtures outside the bundled examples. The feedback task retained duplicate records, rejected an instruction embedded in a comment, and preserved mixed sentiment. The report task caught incorrect aggregate conversion and percentage-point claims and left missing-period revenue uncheckable.

Skill behavior also requires review in the intended agent host. An agent chooses topics, interprets sentiment, and maps prose to calculations. Passing script tests does not establish the accuracy of those choices.

Claude directory approval, installation analytics, and downstream adoption are not tested by this repository. There are no external-use claims in this release.
