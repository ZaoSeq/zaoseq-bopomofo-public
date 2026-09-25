# Daily Corpus V1 results（v0.2 development, DEV only）

Coverage-DEV v1.1（300）與 GOV-DEV（400）。v0.1 TEST 只用於語料排除，未用於任何選擇。

Selection rule: DEV only (Coverage-DEV v1.1 + GOV-DEV). Pick the candidate with the highest Coverage-DEV v1.1 R@5 among those whose GOV-DEV R@1 is at least A's minus 0.02; ties go to higher top-4-family window recall, then to the smaller daily weight / earlier variant. If no candidate satisfies the GOV constraint, the one with the smallest GOV drop is reported as selected and flagged.

- C selection: {"selected": "C_daily0.25", "gov_r1_floor": 0.7825, "passing": [], "constraint_satisfied": false}
- E selection: {"selected": "E_pmi", "gov_r1_floor": 0.7825, "passing": ["E_raw_freq", "E_doc_freq", "E_pmi", "E_interpolated"], "constraint_satisfied": true}

## Trade-off

| config | everyday top1 | everyday R@5 | top-4 window | teacher everyday top1 | GOV top1 | teacher GOV top1 | lexicon entries | LM MB | decoder p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| A gov only (V0) | 0.473 | 0.783 | 0.747 | 0.697 | 0.802 | 0.860 | 16759 | 9.27 | 71 / 186 |
| B daily only | 0.550 | 0.743 | 0.727 | – | 0.312 | – | 16759 | 10.11 | 48 / 147 |
| C daily0.25 (selected; = D = F) | 0.617 | 0.860 | 0.843 | 0.780 | 0.745 | 0.848 | 16759 | 10.11 | 100 / 255 |
| C daily0.5 | 0.607 | 0.857 | 0.843 | – | 0.715 | – | 16759 | 10.11 | 84 / 232 |
| C daily0.75 | 0.640 | 0.857 | 0.823 | – | 0.667 | – | 16759 | 10.11 | 78 / 219 |
| G gov + OASST1 prompter (DEV only) | 0.497 | 0.750 | 0.723 | – | 0.770 | – | 16759 | 9.29 | 70 / 198 |
| H gov + Tatoeba + OASST1 (DEV only) | 0.613 | 0.860 | 0.843 | – | 0.743 | – | 16759 | 10.11 | 87 / 222 |
| E raw_freq | 0.660 | 0.857 | 0.847 | – | 0.815 | – | 135915 | 10.11 | 85 / 256 |
| E doc_freq | 0.660 | 0.857 | 0.847 | – | 0.815 | – | 132826 | 10.11 | 85 / 242 |
| E pmi (selected) | 0.643 | 0.863 | 0.847 | 0.780 | 0.785 | 0.860 | 58111 | 10.11 | 85 / 253 |
| E daily_weighted | 0.657 | 0.880 | 0.863 | – | 0.770 | – | 37712 | 10.11 | 79 / 244 |
| E interpolated | 0.647 | 0.857 | 0.847 | – | 0.785 | – | 58451 | 10.11 | 82 / 228 |

## Coverage-DEV v1.1

| config | R@1 (top1) | R@3 | R@5 | R@10 | unlimited | top-4 window | word coverage | char acc | MRR |
|---|---|---|---|---|---|---|---|---|---|
| A gov only (V0) | 0.473 | 0.700 | 0.783 | 0.837 | 0.917 | 0.747 | 0.245 | 0.904 | 0.600 |
| B daily only | 0.550 | 0.703 | 0.743 | 0.813 | 0.913 | 0.727 | 0.245 | 0.920 | 0.643 |
| C daily0.25 (selected; = D = F) | 0.617 | 0.797 | 0.860 | 0.900 | 0.960 | 0.843 | 0.245 | 0.935 | 0.720 |
| C daily0.5 | 0.607 | 0.810 | 0.857 | 0.907 | 0.963 | 0.843 | 0.245 | 0.934 | 0.721 |
| C daily0.75 | 0.640 | 0.797 | 0.857 | 0.910 | 0.963 | 0.823 | 0.245 | 0.939 | 0.735 |
| G gov + OASST1 prompter (DEV only) | 0.497 | 0.687 | 0.750 | 0.793 | 0.890 | 0.723 | 0.245 | 0.904 | 0.606 |
| H gov + Tatoeba + OASST1 (DEV only) | 0.613 | 0.797 | 0.860 | 0.900 | 0.960 | 0.843 | 0.245 | 0.935 | 0.718 |
| E raw_freq | 0.660 | 0.813 | 0.857 | 0.877 | 0.947 | 0.847 | 0.759 | 0.935 | 0.745 |
| E doc_freq | 0.660 | 0.813 | 0.857 | 0.877 | 0.947 | 0.847 | 0.759 | 0.935 | 0.745 |
| E pmi (selected) | 0.643 | 0.817 | 0.863 | 0.887 | 0.950 | 0.847 | 0.565 | 0.938 | 0.739 |
| E daily_weighted | 0.657 | 0.830 | 0.880 | 0.907 | 0.977 | 0.863 | 0.610 | 0.943 | 0.754 |
| E interpolated | 0.647 | 0.823 | 0.857 | 0.900 | 0.963 | 0.847 | 0.605 | 0.939 | 0.745 |

## GOV-DEV

| config | R@1 (top1) | R@3 | R@5 | R@10 | unlimited | top-4 window | word coverage | char acc | MRR |
|---|---|---|---|---|---|---|---|---|---|
| A gov only (V0) | 0.802 | 0.887 | 0.915 | 0.945 | 0.978 | 0.907 | – | 0.946 | 0.852 |
| B daily only | 0.312 | 0.417 | 0.463 | 0.512 | 0.695 | 0.443 | – | 0.733 | 0.381 |
| C daily0.25 (selected; = D = F) | 0.745 | 0.868 | 0.897 | 0.920 | 0.968 | 0.887 | – | 0.929 | 0.814 |
| C daily0.5 | 0.715 | 0.853 | 0.882 | 0.912 | 0.960 | 0.868 | – | 0.915 | 0.786 |
| C daily0.75 | 0.667 | 0.802 | 0.853 | 0.880 | 0.948 | 0.830 | – | 0.899 | 0.747 |
| G gov + OASST1 prompter (DEV only) | 0.770 | 0.868 | 0.882 | 0.905 | 0.960 | 0.873 | – | 0.937 | 0.825 |
| H gov + Tatoeba + OASST1 (DEV only) | 0.743 | 0.868 | 0.897 | 0.920 | 0.968 | 0.887 | – | 0.928 | 0.813 |
| E raw_freq | 0.815 | 0.902 | 0.910 | 0.930 | 0.985 | 0.910 | – | 0.947 | 0.862 |
| E doc_freq | 0.815 | 0.902 | 0.910 | 0.930 | 0.985 | 0.910 | – | 0.947 | 0.862 |
| E pmi (selected) | 0.785 | 0.895 | 0.917 | 0.938 | 0.980 | 0.907 | – | 0.940 | 0.846 |
| E daily_weighted | 0.770 | 0.877 | 0.910 | 0.940 | 0.983 | 0.895 | – | 0.938 | 0.833 |
| E interpolated | 0.785 | 0.877 | 0.910 | 0.930 | 0.980 | 0.895 | – | 0.942 | 0.840 |

## Language-model cross-entropy（bits / char）

| config | daily DEV split | GOV-DEV split (2000 sentences) |
|---|---|---|
| A gov only (V0) | 8.9486 | 6.0387 |
| B daily only | 6.342 | 10.3942 |
| C daily0.25 (selected; = D = F) | 6.926 | 6.1969 |
| C daily0.5 | 6.4886 | 6.5271 |
| C daily0.75 | 6.268 | 7.1086 |
| G gov + OASST1 prompter (DEV only) | 8.5801 | 6.2853 |
| H gov + Tatoeba + OASST1 (DEV only) | 6.9255 | 6.1966 |

## Frequency-aware derived lexicon

| variant | estimator | min docs | min PMI | n-grams ≥2/M | eligible | by length | daily-only | gov-only | median weight |
|---|---|---|---|---|---|---|---|---|---|
| raw_freq | pooled | 2 | 0.0 | 128798 | 71330 | {"2": 25343, "3": 24261, "4": 21726} | 387 | 57271 | 10.0 |
| doc_freq | pooled | 5 | 0.0 | 128798 | 69644 | {"2": 25233, "3": 23982, "4": 20429} | 387 | 55593 | 10.0 |
| pmi | pooled | 5 | 5.0 | 128798 | 23901 | {"2": 5774, "3": 4868, "4": 13259} | 231 | 19280 | 10.0 |
| daily_weighted | interpolated_daily0.75 | 5 | 5.0 | 107915 | 12648 | {"2": 5635, "3": 3422, "4": 3591} | 1268 | 5121 | 10.0 |
| interpolated | interpolated_daily0.25 | 5 | 5.0 | 133693 | 24255 | {"2": 6760, "3": 6048, "4": 11447} | 1767 | 16372 | 10.0 |

## Frequency weights vs flat weights（diagnostic）

diagnostic only, not a selection candidate: selected E word list (pmi) with every derived word at the median weight 10

| config | R@1 | R@5 | top-4 window |
|---|---|---|---|
| E pmi, every derived word weight 10 (Coverage-DEV) | 0.650 | 0.863 | 0.850 |
| E pmi, every derived word weight 10 (GOV-DEV) | 0.785 | 0.917 | 0.910 |

Fresh-process memory: {"rss_start_mb": 39.4, "v0_load_s": 4.65, "rss_after_v0_mb": 335.8, "daily_lm_load_s": 0.21, "rss_after_daily_lm_mb": 345.9, "derived_lexicon_load_s": 3.16, "rss_after_derived_lexicon_mb": 693.3}

## Homophone competitors（selected E）

- derived readings with an existing same-length competitor: 7; derived weight above best competitor: 2
- Coverage-DEV change vs selected C: {"wrong_to_correct": 13, "correct_to_wrong": 5, "wrong_to_correct_with_derived_word": 13, "correct_to_wrong_with_derived_word": 5}
- GOV-DEV change vs selected C: {"wrong_to_correct": 22, "correct_to_wrong": 6, "wrong_to_correct_with_derived_word": 22, "correct_to_wrong_with_derived_word": 6}

## Frozen fine-tuned Laya（observation only）

| config | set | decoder top1 | teacher top1 | teacher vs decoder: W→C / C→W | teacher vs A teacher: W→C / C→W | teacher p50/p95 ms | fallbacks |
|---|---|---|---|---|---|---|---|
| A gov only (V0) | coverage_dev | 0.473 | 0.697 | 74 / 7 | – | 48.49 / 72.48 | 0 |
| A gov only (V0) | gov_dev | 0.802 | 0.860 | 31 / 8 | – | 55.91 / 73.42 | 0 |
| C daily0.25 (selected; = D = F) | coverage_dev | 0.617 | 0.780 | 55 / 6 | 31 / 6 (p=0.0) | 66.42 / 138.83 | 0 |
| C daily0.25 (selected; = D = F) | gov_dev | 0.745 | 0.848 | 53 / 12 | 5 / 10 (p=0.3018) | 66.16 / 95.54 | 0 |
| E pmi (selected) | coverage_dev | 0.643 | 0.780 | 49 / 8 | 37 / 12 (p=0.0005) | 54.99 / 71.37 | 0 |
| E pmi (selected) | gov_dev | 0.785 | 0.860 | 45 / 15 | 16 / 16 (p=1.0) | 54.29 / 71.47 | 0 |

## Teacher window diagnostic（not adopted; production stays K=4）

| config | set | K | gold in window | teacher top1 | same pick as K=4 | vs K=4: W→C / C→W | p50/p95 ms | GPU peak MB |
|---|---|---|---|---|---|---|---|---|
| A gov only (V0) | coverage_dev | K=4 | 0.747 | 0.697 | 1.000 | 0 / 0 | 48.49 / 72.48 | 1507.3 |
| A gov only (V0) | coverage_dev | K=5 | 0.783 | 0.700 | 0.877 | 8 / 7 | 47.38 / 56.09 | 1507.6 |
| A gov only (V0) | coverage_dev | K=6 | 0.787 | 0.707 | 0.870 | 10 / 7 | 47.76 / 56.79 | 1507.8 |
| A gov only (V0) | coverage_dev | K=8 | 0.817 | 0.710 | 0.837 | 14 / 10 | 47.6 / 59.8 | 1508.4 |
| A gov only (V0) | gov_dev | K=4 | 0.907 | 0.860 | 1.000 | 0 / 0 | 55.91 / 73.42 | 1508.1 |
| A gov only (V0) | gov_dev | K=5 | 0.915 | 0.863 | 0.955 | 4 / 3 | 45.68 / 62.67 | 1508.5 |
| A gov only (V0) | gov_dev | K=6 | 0.925 | 0.865 | 0.930 | 7 / 5 | 43.16 / 54.65 | 1508.9 |
| A gov only (V0) | gov_dev | K=8 | 0.935 | 0.868 | 0.917 | 12 / 9 | 50.22 / 68.43 | 1513.1 |
| E pmi (selected) | coverage_dev | K=4 | 0.847 | 0.780 | 1.000 | 0 / 0 | 54.99 / 71.37 | 1507.3 |
| E pmi (selected) | coverage_dev | K=5 | 0.863 | 0.783 | 0.920 | 8 / 7 | 51.81 / 67.41 | 1507.6 |
| E pmi (selected) | coverage_dev | K=6 | 0.867 | 0.773 | 0.887 | 9 / 11 | 57.02 / 76.58 | 1507.8 |
| E pmi (selected) | coverage_dev | K=8 | 0.880 | 0.790 | 0.873 | 12 / 9 | 60.47 / 72.47 | 1508.4 |
| E pmi (selected) | gov_dev | K=4 | 0.907 | 0.860 | 1.000 | 0 / 0 | 54.29 / 71.47 | 1508.1 |
| E pmi (selected) | gov_dev | K=5 | 0.917 | 0.848 | 0.940 | 5 / 10 | 53.86 / 75.46 | 1508.6 |
| E pmi (selected) | gov_dev | K=6 | 0.920 | 0.860 | 0.950 | 6 / 6 | 57.61 / 76.31 | 1508.9 |
| E pmi (selected) | gov_dev | K=8 | 0.932 | 0.860 | 0.925 | 9 / 9 | 55.64 / 75.52 | 1513.2 |

## Latency / RAM / artifact size

Load: {"gov_context_s": 8.74, "rss_after_gov_mb": 645.7, "rss_before_mb": 36.3}; lexicon statistics build 73.2 s

| config | gov LM MB | daily LM MB | lexicon entries | extra load s | RSS delta MB | LM extend µs | Coverage p50/p95 ms | GOV p50/p95 ms |
|---|---|---|---|---|---|---|---|---|
| A gov only (V0) | 9.27 | 0.0 | 16759 | 0.0 | 1.3 | 14.364 | 71 / 186 | 71 / 183 |
| B daily only | 9.27 | 0.84 | 16759 | 0.356 | 9.9 | 2.917 | 48 / 147 | 44 / 138 |
| C daily0.25 (selected; = D = F) | 9.27 | 0.84 | 16759 | 0.0 | 0.5 | 15.187 | 100 / 255 | 81 / 213 |
| C daily0.5 | 9.27 | 0.84 | 16759 | 0.0 | -0.2 | 10.508 | 84 / 232 | 65 / 183 |
| C daily0.75 | 9.27 | 0.84 | 16759 | 0.0 | 0.2 | 16.855 | 78 / 219 | 76 / 191 |
| G gov + OASST1 prompter (DEV only) | 9.27 | 0.02 | 16759 | 0.007 | -0.1 | 13.988 | 70 / 198 | 73 / 194 |
| H gov + Tatoeba + OASST1 (DEV only) | 9.27 | 0.84 | 16759 | 0.229 | 23.5 | 16.303 | 87 / 222 | 73 / 192 |
| E raw_freq | 9.27 | 0.84 | 135915 | 0.0 | -16.6 | 15.72 | 85 / 256 | 77 / 220 |
| E doc_freq | 9.27 | 0.84 | 132826 | 0.0 | -15.9 | 15.614 | 85 / 242 | 80 / 217 |
| E pmi (selected) | 9.27 | 0.84 | 58111 | 0.0 | -3.9 | 16.881 | 85 / 253 | 78 / 230 |
| E daily_weighted | 9.27 | 0.84 | 37712 | 0.0 | -0.7 | 15.043 | 79 / 244 | 76 / 207 |
| E interpolated | 9.27 | 0.84 | 58451 | 0.0 | -3.5 | 15.683 | 82 / 228 | 75 / 198 |

## Corpus V1

| source | documents | sentences seen | kept | Han chars kept | traditional ratio | simplified rate | Han ratio | median length | top-10 contributor share | splits |
|---|---|---|---|---|---|---|---|---|---|---|
| oasst1_zh_prompter | 1263 | 1540 | 182 | 2823 | 0.754 | 0.880 | 0.878 | 13.0 | 0.8077 | {"dev": 13, "test": 7, "train": 162} |
| tatoeba_cmn_hant | 39743 | 39720 | 38808 | 411222 | 0.998 | 0.005 | 0.882 | 9.0 | 0.9129 | {"dev": 1912, "test": 1946, "train": 34950} |

Drops: {"oasst1_zh_prompter": {"simplified": 1356, "duplicate_other_daily_source": 2, "doc:too_short_or_low_han": 151, "doc:markup_or_code": 3}, "tatoeba_cmn_hant": {"non_standard_char": 479, "simplified": 183, "duplicate_in_source": 114, "cross_split_near_dup": 87, "eval_overlap": 31, "weird_unicode": 18, "doc:too_short_or_low_han": 1059, "doc:email": 3, "doc:long_number": 2}}

Evaluation-set exclusions: {"oasst1_zh_prompter": {}, "tatoeba_cmn_hant": {"hand_dev_sanity:near_duplicate": 11, "coverage_dev_v1.0:near_duplicate": 6, "gov_dev_corpus_split:shared_8gram": 4, "reference_v0_1_test_everyday:near_duplicate": 3, "hand_dev_sanity:shared_8gram": 2, "reference_v0_1_test_gov_corpus_split:shared_8gram": 2, "coverage_dev_v1.0:shared_8gram": 2, "reference_v0_1_test_everyday:shared_8gram": 1}}

Language models (train split): {"daily_all": {"train_sentences": 35112, "char_tokens": 453125, "char_vocabulary": 3694, "char_bigrams": 91400, "char_trigrams_kept": 47902, "min_trigram_count": 2, "sources": ["oasst1_zh_prompter", "tatoeba_cmn_hant"], "production_eligible": false}, "daily_production": {"train_sentences": 34950, "char_tokens": 450195, "char_vocabulary": 3685, "char_bigrams": 90790, "char_trigrams_kept": 47616, "min_trigram_count": 2, "sources": ["tatoeba_cmn_hant"], "production_eligible": true}, "oasst1_zh_prompter": {"train_sentences": 162, "char_tokens": 2930, "char_vocabulary": 664, "char_bigrams": 2038, "char_trigrams_kept": 233, "min_trigram_count": 2, "sources": ["oasst1_zh_prompter"], "production_eligible": false}, "tatoeba_cmn_hant": {"train_sentences": 34950, "char_tokens": 450195, "char_vocabulary": 3685, "char_bigrams": 90790, "char_trigrams_kept": 47616, "min_trigram_count": 2, "sources": ["tatoeba_cmn_hant"], "production_eligible": true}}

## Sources

| source | status | scope | license | training use | redistribution |
|---|---|---|---|---|---|
| cv_sentence_collector_zh_tw | HOLD | none | CC0 1.0 | yes | yes (CC0); not exercised: raw text is not committed |
| tatoeba_cmn_hant | APPROVED | production | CC BY 2.0 FR (the cmn CC0 subset file is empty) | yes | yes with attribution; not exercised: raw text is not committed |
| oasst1_zh_prompter | APPROVED | dev_experiment | Apache-2.0 | yes | yes with license notice; not exercised: raw text is not committed |
| oasst1_zh_assistant | HOLD | none | Apache-2.0 | unknown | yes with license notice |
| mdc_common_voice_zh_tw | HOLD | none | CC0 1.0 (dataset) plus Mozilla Data Collective terms of access | unknown | no: MDC asks users not to post, distribute or mirror any Common Voice dataset outside MDC |
| cv_zh_tw_setences | HOLD | none | unknown (repository code is MPL-2.0; README says 'the majority' of /server/data is CC0) | unknown | unknown |
| cv_zh_tw_chatlogs | HOLD | none | unknown | unknown | unknown |
| cv_zh_tw_lms | HOLD | none | unknown | unknown | unknown |
| cv_zh_tw_taipei_city_gov | HOLD | none | unknown | unknown | unknown |
| twllm_data | HOLD | none | Apache-2.0 (as declared by the uploader) | unknown | unknown |
| taiwan_tongues_asr_ce | HOLD | none | other ('released under the original project's license terms', not specified) | unknown | unknown |
| excluded_by_policy | REJECTED | none | various / unclear | unknown | unknown |
| unihan_variants | APPROVED | production | Unicode License v3 | yes (reference data, not a text corpus: used only to flag Simplified-script characters) | yes with copyright and permission notice; not exercised |
