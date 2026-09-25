# Coverage V1 results（DEV only）

V0 equivalence：{"coverage_dev": {"cases": 300, "mismatches": []}, "gov_dev": {"cases": 400, "mismatches": []}}

## Coverage-DEV（300）

| config | R@1 | R@3 | R@5 | R@10 | unlimited | top-4 family window | candidates | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| v0 | 0.470 | 0.697 | 0.780 | 0.833 | 0.917 | 0.743 | 20.0 | 82 | 228 |
| nbest50 | 0.470 | 0.697 | 0.780 | 0.833 | 0.917 | 0.743 | 49.7 | 84 | 229 |
| nbest100 | 0.470 | 0.697 | 0.780 | 0.833 | 0.917 | 0.743 | 91.9 | 71 | 186 |
| beam24 | 0.467 | 0.690 | 0.773 | 0.820 | 0.887 | 0.737 | 20.0 | 40 | 104 |
| beam96 | 0.470 | 0.697 | 0.780 | 0.833 | 0.960 | 0.743 | 20.0 | 141 | 392 |
| beam96_nbest100 | 0.470 | 0.697 | 0.780 | 0.833 | 0.960 | 0.743 | 99.4 | 146 | 404 |
| beam192_nbest100 | 0.470 | 0.697 | 0.780 | 0.833 | 0.980 | 0.743 | 100.0 | 196 | 691 |
| span8 | 0.307 | 0.447 | 0.490 | 0.523 | 0.550 | 0.477 | 20.0 | 23 | 60 |
| span16 | 0.440 | 0.653 | 0.723 | 0.767 | 0.833 | 0.697 | 20.0 | 40 | 89 |
| span32 | 0.467 | 0.687 | 0.770 | 0.823 | 0.903 | 0.733 | 20.0 | 60 | 135 |
| lexslots16 | 0.470 | 0.697 | 0.780 | 0.833 | 0.917 | 0.743 | 20.0 | 106 | 266 |
| lexslots32 | 0.470 | 0.697 | 0.780 | 0.833 | 0.917 | 0.743 | 20.0 | 132 | 350 |
| tonevar | 0.457 | 0.680 | 0.757 | 0.810 | 0.907 | 0.713 | 20.0 | 85 | 217 |
| prune_lexical | 0.237 | 0.337 | 0.370 | 0.387 | 0.403 | 0.350 | 20.0 | 73 | 190 |
| derived_c50_pmi3_w10 | 0.487 | 0.693 | 0.773 | 0.827 | 0.913 | 0.740 | 20.0 | 66 | 203 |
| derived_c20_pmi3_w10 | 0.493 | 0.693 | 0.767 | 0.820 | 0.913 | 0.740 | 20.0 | 73 | 224 |
| derived_c20_pmi5_w10 | 0.487 | 0.707 | 0.777 | 0.843 | 0.930 | 0.753 | 20.0 | 72 | 199 |
| derived_c50_pmi3_w3 | 0.490 | 0.697 | 0.773 | 0.827 | 0.920 | 0.747 | 20.0 | 78 | 218 |

## GOV-DEV（400）

| config | R@1 | R@3 | R@5 | R@10 | unlimited | top-4 family window | candidates | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| v0 | 0.802 | 0.887 | 0.915 | 0.945 | 0.978 | 0.907 | 20.0 | 40 | 141 |
| nbest50 | 0.802 | 0.887 | 0.915 | 0.945 | 0.978 | 0.907 | 50.0 | 74 | 205 |
| nbest100 | 0.802 | 0.887 | 0.915 | 0.945 | 0.978 | 0.907 | 99.6 | 68 | 191 |
| beam24 | 0.802 | 0.880 | 0.907 | 0.935 | 0.963 | 0.900 | 20.0 | 37 | 106 |
| beam96 | 0.802 | 0.887 | 0.915 | 0.945 | 0.983 | 0.907 | 20.0 | 128 | 341 |
| beam96_nbest100 | 0.802 | 0.887 | 0.915 | 0.945 | 0.983 | 0.907 | 100.0 | 83 | 281 |
| beam192_nbest100 | 0.802 | 0.887 | 0.915 | 0.945 | 0.995 | 0.907 | 100.0 | 242 | 689 |
| span8 | 0.357 | 0.395 | 0.403 | 0.412 | 0.420 | 0.403 | 20.0 | 15 | 39 |
| span16 | 0.682 | 0.735 | 0.757 | 0.775 | 0.800 | 0.745 | 20.0 | 29 | 75 |
| span32 | 0.760 | 0.840 | 0.858 | 0.885 | 0.915 | 0.850 | 20.0 | 48 | 121 |
| lexslots16 | 0.802 | 0.887 | 0.915 | 0.945 | 0.978 | 0.907 | 20.0 | 89 | 235 |
| lexslots32 | 0.802 | 0.887 | 0.915 | 0.945 | 0.978 | 0.907 | 20.0 | 111 | 317 |
| tonevar | 0.802 | 0.882 | 0.912 | 0.945 | 0.978 | 0.907 | 20.0 | 66 | 181 |
| prune_lexical | 0.297 | 0.315 | 0.318 | 0.323 | 0.328 | 0.318 | 20.0 | 63 | 171 |
| derived_c50_pmi3_w10 | 0.812 | 0.902 | 0.925 | 0.953 | 0.988 | 0.925 | 20.0 | 73 | 211 |
| derived_c20_pmi3_w10 | 0.838 | 0.907 | 0.927 | 0.950 | 0.988 | 0.927 | 20.0 | 67 | 199 |
| derived_c20_pmi5_w10 | 0.830 | 0.897 | 0.927 | 0.945 | 0.985 | 0.917 | 20.0 | 68 | 197 |
| derived_c50_pmi3_w3 | 0.818 | 0.902 | 0.927 | 0.958 | 0.988 | 0.925 | 20.0 | 67 | 189 |

## V0 coverage indicators（Coverage-DEV）

- OOV rate 0.000；reading coverage 1.000；multi-character word coverage 0.245
- gold never generated 25（unreachable 0，beam-pruned 25）；generated but outside top-5 41

## Oracle lexicon diagnostic（upper bound, not adoptable）

upper bound only: Coverage-DEV gold words added to the lexicon; not an adoptable configuration

| config | R@1 | R@3 | R@5 | R@10 | unlimited | top-4 family window | candidates | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| v0 + 515 gold words | 0.717 | 0.897 | 0.943 | 0.967 | 0.993 | 0.927 | 20.0 | 73 | 197 |

## Missing-candidate taxonomy, V0, coverage_dev（77 cases）

| category | count | share |
|---|---|---|
| lexical_missing | 32 | 0.416 |
| pronunciation_variant_missing | 0 | 0.000 |
| segmentation_missing | 0 | 0.000 |
| beam_pruned | 11 | 0.143 |
| score_pruned | 17 | 0.221 |
| proper_noun | 4 | 0.052 |
| colloquial_word | 2 | 0.026 |
| orthographic_variant | 0 | 0.000 |
| character_reading_missing | 0 | 0.000 |
| candidate_family_issue | 11 | 0.143 |
| other | 0 | 0.000 |

stage: {"generated_ranked_low": 27, "beam_pruned": 25, "outside_output": 14, "top5": 11}

## Missing-candidate taxonomy, V0, gov_dev（37 cases）

| category | count | share |
|---|---|---|
| lexical_missing | 0 | 0.000 |
| pronunciation_variant_missing | 0 | 0.000 |
| segmentation_missing | 0 | 0.000 |
| beam_pruned | 9 | 0.243 |
| score_pruned | 25 | 0.676 |
| proper_noun | 0 | 0.000 |
| colloquial_word | 0 | 0.000 |
| orthographic_variant | 0 | 0.000 |
| character_reading_missing | 0 | 0.000 |
| candidate_family_issue | 3 | 0.081 |
| other | 0 | 0.000 |

stage: {"generated_ranked_low": 16, "outside_output": 9, "beam_pruned": 9, "top5": 3}

## Timing breakdown（V0, Coverage-DEV, instrumented）

{"lexicon_lookup": 0.009, "lm_scoring": 0.637, "beam_sort_prune": 0.032, "kbest_finalize": 0.009, "candidate_family": 0.001, "other_lattice_overhead": 0.313, "mean_total_ms_instrumented": 88.43}

## Frozen fine-tuned Laya on each candidate set（observation only）

```json
{
  "coverage_dev": {
    "v0": {
      "decoder_order_top1": 0.47,
      "fine_tuned_laya_top1": 0.6933
    },
    "derived_c20_pmi5_w10": {
      "decoder_order_top1": 0.4867,
      "fine_tuned_laya_top1": 0.71
    },
    "paired_decoder_order_top1": {
      "fixed": 9,
      "broken": 4,
      "mcnemar_p": 0.2668
    },
    "paired_fine_tuned_laya_top1": {
      "fixed": 12,
      "broken": 7,
      "mcnemar_p": 0.3593
    }
  },
  "gov_dev": {
    "v0": {
      "decoder_order_top1": 0.8025,
      "fine_tuned_laya_top1": 0.86
    },
    "derived_c20_pmi5_w10": {
      "decoder_order_top1": 0.83,
      "fine_tuned_laya_top1": 0.86
    },
    "paired_decoder_order_top1": {
      "fixed": 18,
      "broken": 7,
      "mcnemar_p": 0.0433
    },
    "paired_fine_tuned_laya_top1": {
      "fixed": 12,
      "broken": 12,
      "mcnemar_p": 1.0
    }
  }
}
```

## Derived-lexicon statistics

- derived_c50_pmi3_w10: {"bigram_words": 8032, "trigram_words": 10060, "entries": 26637, "ambiguous_words": 6268, "skipped_too_many_readings": 1731}
- derived_c20_pmi3_w10: {"bigram_words": 13546, "trigram_words": 26219, "entries": 58899, "ambiguous_words": 14104, "skipped_too_many_readings": 4108}
- derived_c20_pmi5_w10: {"bigram_words": 7258, "trigram_words": 13315, "entries": 31015, "ambiguous_words": 7616, "skipped_too_many_readings": 1846}
- derived_c50_pmi3_w3: {"bigram_words": 8032, "trigram_words": 10060, "entries": 26637, "ambiguous_words": 6268, "skipped_too_many_readings": 1731}
