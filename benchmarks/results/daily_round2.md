# Daily Corpus Round 2 + Production Lexicon Cleanup（v0.2 development, DEV only）

Selection plan sha256 `83c59d9b35d56b76ab0bfe81daa39b5ddb25549f8b269e76c0a606cc4e23e852`（benchmarks/frozen/v0.2_selection_plan.json，實驗前凍結）。
Production daily sources: ['tatoeba_cmn_hant', 'unihan_variants']。v0.1 TEST 只用於語料排除。

## reference

| config | gates | everyday base top1 | everyday teacher top1 | teacher vs V0 teacher W→C / C→W | MRR | R@3 | R@5 | R@10 | top-4 window | GOV base top1 | GOV teacher top1 | GOV teacher vs V0 W→C / C→W | lexicon entries | +RSS MB | decoder p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_v0 | pass | 0.473 | 0.697 | 0 / 0 | 0.600 | 0.700 | 0.783 | 0.837 | 0.747 | 0.802 | 0.860 | 0 / 0 | 16759 | 0.0 | 60 / 170 |

## 1_reading

| config | gates | everyday base top1 | everyday teacher top1 | teacher vs V0 teacher W→C / C→W | MRR | R@3 | R@5 | R@10 | top-4 window | GOV base top1 | GOV teacher top1 | GOV teacher vs V0 W→C / C→W | lexicon entries | +RSS MB | decoder p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_R0 | not eligible | 0.647 | 0.760 | 33 / 14 | 0.736 | 0.810 | 0.843 | 0.873 | 0.827 | 0.823 | 0.858 | 18 / 19 | 154115 | 23.1 | 63 / 196 |
| S1_R1 | pass | 0.640 | 0.760 | 33 / 14 | 0.732 | 0.803 | 0.847 | 0.890 | 0.833 | 0.802 | 0.853 | 17 / 20 | 48893 | 12.6 | 63 / 203 |
| S1_R2 | pass | 0.643 | 0.760 | 33 / 14 | 0.734 | 0.807 | 0.847 | 0.887 | 0.833 | 0.807 | 0.855 | 18 / 20 | 50882 | 13.7 | 42 / 148 |
| S1_R3 | pass | 0.633 | 0.760 | 33 / 14 | 0.732 | 0.803 | 0.840 | 0.897 | 0.823 | 0.830 | 0.870 | 20 / 16 | 68586 | 14.6 | 64 / 175 |

selected: **S1_R2**; tie set ['S1_R2', 'S1_R1', 'S1_R3']; failed gates {"S1_R0": ["not_production_eligible"]}

## 2_extraction

| config | gates | everyday base top1 | everyday teacher top1 | teacher vs V0 teacher W→C / C→W | MRR | R@3 | R@5 | R@10 | top-4 window | GOV base top1 | GOV teacher top1 | GOV teacher vs V0 W→C / C→W | lexicon entries | +RSS MB | decoder p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S2_L1 | pass | 0.643 | 0.760 | 33 / 14 | 0.734 | 0.807 | 0.847 | 0.887 | 0.833 | 0.807 | 0.855 | 18 / 20 | 50882 | 11.9 | 63 / 199 |
| S2_L2 | gov_baseline_regression | 0.677 | 0.787 | 34 / 7 | 0.767 | 0.837 | 0.883 | 0.923 | 0.867 | 0.748 | 0.843 | 8 / 15 | 21228 | 10.5 | 66 / 179 |
| S2_L3 | gov_baseline_regression | 0.663 | 0.793 | 36 / 7 | 0.758 | 0.837 | 0.883 | 0.913 | 0.863 | 0.745 | 0.845 | 7 / 13 | 20642 | 10.3 | 76 / 220 |
| S2_L4 | gov_baseline_regression, gov_teacher_regression | 0.650 | 0.767 | 34 / 13 | 0.741 | 0.813 | 0.853 | 0.887 | 0.840 | 0.752 | 0.823 | 9 / 24 | 38565 | 11.3 | 36 / 122 |
| S2_L5 | pass | 0.640 | 0.767 | 35 / 14 | 0.736 | 0.813 | 0.860 | 0.897 | 0.843 | 0.797 | 0.850 | 15 / 19 | 42548 | 13.6 | 39 / 154 |

selected: **S2_L5**; tie set ['S2_L5']; failed gates {"S2_L2": ["gov_baseline_regression"], "S2_L3": ["gov_baseline_regression"], "S2_L4": ["gov_baseline_regression", "gov_teacher_regression"]}

## 3_prior

| config | gates | everyday base top1 | everyday teacher top1 | teacher vs V0 teacher W→C / C→W | MRR | R@3 | R@5 | R@10 | top-4 window | GOV base top1 | GOV teacher top1 | GOV teacher vs V0 W→C / C→W | lexicon entries | +RSS MB | decoder p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S3_flat | pass | 0.640 | 0.767 | 35 / 14 | 0.736 | 0.813 | 0.860 | 0.897 | 0.843 | 0.797 | 0.850 | 15 / 19 | 42548 | 12.6 | 52 / 176 |
| S3_raw | pass | 0.640 | 0.767 | 36 / 15 | 0.736 | 0.810 | 0.850 | 0.900 | 0.840 | 0.807 | 0.860 | 16 / 16 | 42548 | 11.6 | 64 / 283 |
| S3_log | pass | 0.643 | 0.770 | 36 / 14 | 0.738 | 0.817 | 0.857 | 0.897 | 0.843 | 0.805 | 0.853 | 15 / 18 | 42548 | 11.9 | 63 / 199 |
| S3_doc | pass | 0.637 | 0.767 | 36 / 15 | 0.734 | 0.810 | 0.850 | 0.900 | 0.840 | 0.805 | 0.860 | 16 / 16 | 42548 | 12.8 | 64 / 172 |
| S3_daily_only | pass | 0.650 | 0.780 | 36 / 11 | 0.746 | 0.827 | 0.867 | 0.903 | 0.857 | 0.802 | 0.858 | 15 / 16 | 42548 | 11.7 | 63 / 196 |
| S3_interpolated | pass | 0.633 | 0.763 | 36 / 16 | 0.731 | 0.810 | 0.857 | 0.893 | 0.840 | 0.805 | 0.863 | 16 / 15 | 42548 | 12.8 | 63 / 175 |
| S3_rank_bucket | pass | 0.640 | 0.770 | 36 / 14 | 0.737 | 0.813 | 0.857 | 0.903 | 0.843 | 0.807 | 0.858 | 16 / 17 | 42548 | 11.8 | 74 / 268 |

selected: **S3_daily_only**; tie set ['S3_daily_only']; failed gates {}

## 4_lm_weight

| config | gates | everyday base top1 | everyday teacher top1 | teacher vs V0 teacher W→C / C→W | MRR | R@3 | R@5 | R@10 | top-4 window | GOV base top1 | GOV teacher top1 | GOV teacher vs V0 W→C / C→W | lexicon entries | +RSS MB | decoder p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S4_daily0 | pass | 0.523 | 0.703 | 14 / 12 | 0.637 | 0.727 | 0.797 | 0.850 | 0.773 | 0.835 | 0.863 | 13 / 12 | 42548 | 2.4 | 55 / 172 |
| S4_daily0.1 | pass | 0.643 | 0.763 | 34 / 14 | 0.735 | 0.800 | 0.860 | 0.893 | 0.843 | 0.835 | 0.868 | 16 / 13 | 42548 | 13.1 | 62 / 186 |
| S4_daily0.25 | pass | 0.650 | 0.780 | 36 / 11 | 0.746 | 0.827 | 0.867 | 0.903 | 0.857 | 0.802 | 0.858 | 15 / 16 | 42548 | 11.8 | 67 / 172 |
| S4_daily0.5 **(final)** | pass | 0.650 | 0.787 | 42 / 15 | 0.751 | 0.827 | 0.873 | 0.907 | 0.857 | 0.790 | 0.858 | 18 / 19 | 42548 | 11.4 | 61 / 186 |

selected: **S4_daily0.5**; tie set ['S4_daily0.5']; failed gates {}

## diagnostic

| config | gates | everyday base top1 | everyday teacher top1 | teacher vs V0 teacher W→C / C→W | MRR | R@3 | R@5 | R@10 | top-4 window | GOV base top1 | GOV teacher top1 | GOV teacher vs V0 W→C / C→W | lexicon entries | +RSS MB | decoder p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DIAG_oasst_mix | not eligible | 0.650 | 0.790 | 43 / 15 | 0.752 | 0.830 | 0.870 | 0.907 | 0.860 | 0.790 | 0.853 | 16 / 19 | 42548 | 12.9 | 61 / 191 |

## Final selection（PRECOMMITTED rule）

selected **S4_daily0.5**; tie set ['S4_daily0.5']; eligible 17

## Lexicon variants

| recipe | derived words | by length | daily-supported | gov-only | unsupported readings | false competitors | compact MB | weights |
|---|---|---|---|---|---|---|---|---|
| R0_cartesian|L1_mixed|flat | 82841 | {"2": 35409, "3": 25611, "4": 21821} | 17318 | 65523 | 85529 | 10813 | 5.37 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R1_unambiguous|L1_mixed|flat | 32134 | {"2": 15937, "3": 9182, "4": 7015} | 5827 | 26307 | 0 | 0 | 1.507 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R2_known_word|L1_mixed|flat | 34123 | {"2": 15937, "3": 10272, "4": 7914} | 6175 | 27948 | 0 | 0 | 1.586 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R3_bounded|L1_mixed|flat | 51827 | {"2": 23212, "3": 15958, "4": 12657} | 12539 | 39288 | 0 | 0 | 2.23 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R2_known_word|L2_daily_only|flat | 4469 | {"2": 2603, "3": 1122, "4": 744} | 4469 | 0 | 0 | 0 | 0.512 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R2_known_word|L3_daily_supported|flat | 3883 | {"2": 3233, "3": 557, "4": 93} | 3883 | 0 | 0 | 0 | 0.483 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R2_known_word|L4_domain_ratio|flat | 21806 | {"2": 12581, "3": 6361, "4": 2864} | 5575 | 16231 | 0 | 0 | 1.117 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R2_known_word|L5_doc_frequency|flat | 25789 | {"2": 14649, "3": 7640, "4": 3500} | 5977 | 19812 | 0 | 0 | 1.257 | {"min": 10.0, "p25": 10.0, "median": 10.0, "p75": 10.0, "max": 10.0} |
| R2_known_word|L5_doc_frequency|raw | 25789 | {"2": 14649, "3": 7640, "4": 3500} | 5977 | 19812 | 0 | 0 | 1.257 | {"min": 4.3902, "p25": 6.0976, "median": 10.0, "p75": 20.9756, "max": 200.0} |
| R2_known_word|L5_doc_frequency|log | 25789 | {"2": 14649, "3": 7640, "4": 3500} | 5977 | 19812 | 0 | 0 | 1.257 | {"min": 6.4249, "p25": 7.8516, "median": 10.0, "p75": 13.2171, "max": 39.5848} |
| R2_known_word|L5_doc_frequency|doc | 25789 | {"2": 14649, "3": 7640, "4": 3500} | 5977 | 19812 | 0 | 0 | 1.257 | {"min": 3.0, "p25": 6.5517, "median": 10.0, "p75": 18.9655, "max": 200.0} |
| R2_known_word|L5_doc_frequency|daily_only | 25789 | {"2": 14649, "3": 7640, "4": 3500} | 5977 | 19812 | 0 | 0 | 1.257 | {"min": 3.0, "p25": 3.0, "median": 3.0, "p75": 3.0, "max": 200.0} |
| R2_known_word|L5_doc_frequency|interpolated | 25789 | {"2": 14649, "3": 7640, "4": 3500} | 5977 | 19812 | 0 | 0 | 1.257 | {"min": 3.0, "p25": 5.4369, "median": 10.0, "p75": 20.9655, "max": 200.0} |
| R2_known_word|L5_doc_frequency|rank_bucket | 25789 | {"2": 14649, "3": 7640, "4": 3500} | 5977 | 19812 | 0 | 0 | 1.257 | {"min": 3.0, "p25": 3.0, "median": 10.0, "p75": 20.0, "max": 50.0} |

Rejections:

- R0_cartesian|L1_mixed|flat: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 13571, "too_few_documents": 819}
- R1_unambiguous|L1_mixed|flat: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 64278, "too_few_documents": 819}
- R2_known_word|L1_mixed|flat: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 62289, "too_few_documents": 819}
- R3_bounded|L1_mixed|flat: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44585, "too_few_documents": 819}
- R2_known_word|L2_daily_only|flat: {"below_daily_count": 117289, "fragment_of_longer_ngram": 5642, "low_daily_pmi": 18053, "readings_unresolved": 13717, "too_few_daily_documents": 440}
- R2_known_word|L3_daily_supported|flat: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "no_daily_support": 83351, "readings_unresolved": 9178, "too_few_documents": 819}
- R2_known_word|L4_domain_ratio|flat: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "government_domain_concentrated": 34530, "numeral_template": 1579, "readings_unresolved": 38497, "too_few_documents": 819}
- R2_known_word|L5_doc_frequency|flat: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44821, "too_few_documents": 2770, "too_few_sources": 23851}
- R2_known_word|L5_doc_frequency|raw: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44821, "too_few_documents": 2770, "too_few_sources": 23851}
- R2_known_word|L5_doc_frequency|log: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44821, "too_few_documents": 2770, "too_few_sources": 23851}
- R2_known_word|L5_doc_frequency|doc: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44821, "too_few_documents": 2770, "too_few_sources": 23851}
- R2_known_word|L5_doc_frequency|daily_only: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44821, "too_few_documents": 2770, "too_few_sources": 23851}
- R2_known_word|L5_doc_frequency|interpolated: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44821, "too_few_documents": 2770, "too_few_sources": 23851}
- R2_known_word|L5_doc_frequency|rank_bucket: {"below_pooled_frequency": 31043, "fragment_of_longer_ngram": 31336, "readings_unresolved": 44821, "too_few_documents": 2770, "too_few_sources": 23851}

## Homophone order by prior（Coverage-DEV gold multi-character words that share a reading with another same-length entry）

| prior | contested gold words | gold ranked first |
|---|---|---|
| flat | 47 | 35 |
| raw | 47 | 42 |
| log | 47 | 42 |
| doc | 47 | 41 |
| daily_only | 47 | 41 |
| interpolated | 47 | 43 |
| rank_bucket | 47 | 41 |

## Memory: representation comparison（fresh process each）

lexicon_benchmark: compact artifact 1.257 MB, provenance JSON 13.203 MB

| representation | load s | +RSS MB | lookup µs |
|---|---|---|---|
| frozen_lexicon_with_provenance_alive | 0.976 | 79.0 | 0.134 |
| frozen_lexicon | 0.928 | 78.7 | 0.115 |
| compact | 0.118 | 10.0 | 1.168 |

lexicon_benchmark_R0: compact artifact 5.37 MB, provenance JSON 41.122 MB

| representation | load s | +RSS MB | lookup µs |
|---|---|---|---|
| frozen_lexicon_with_provenance_alive | 3.484 | 263.7 | 0.204 |
| frozen_lexicon | 3.231 | 262.3 | 0.198 |
| compact | 0.162 | 21.5 | 1.299 |

## Exact equivalence（frozen Lexicon + uncached LM vs compact lexicon + cached LM）

S4_daily0.5: 700 DEV cases, mismatches 0; latency {"frozen_lexicon_uncached_lm": {"p50": 86.6, "p95": 238.3}, "compact_lexicon_cached_lm": {"p50": 64.9, "p95": 207.9}}

