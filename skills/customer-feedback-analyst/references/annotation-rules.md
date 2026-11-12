# Annotation rules

A topic describes what a comment is about. Sentiment describes the attitude toward that topic. A response can praise delivery speed and criticize packaging; it should receive two labels.

Use a specific topic when the text supports it. “Bad experience” does not establish a delivery, pricing, or product-quality problem. An empty label list means the record was read and no defined topic applied.

For mixed comments within one topic, use `mixed` and choose an excerpt containing both sides when possible. Keep the complete text available for review. An excerpt confirms that words occur in the source; it does not prove that the chosen interpretation is correct.

Count distinct record ids within each topic. A long comment mentioning delivery five times still contributes one delivery record. Keep a common denominator of all eligible records, including reviewed records with no assigned topic. Report exclusions separately.

Repeated text may be genuine or duplicated collection. The audit flags normalized exact repeats; it does not decide which explanation is correct. Near-duplicate detection is outside the script's scope.

When a topic definition changes, recheck earlier labels. Compare periods only after applying the same definitions to both. Do not describe differences as statistically significant without an appropriate analysis.
