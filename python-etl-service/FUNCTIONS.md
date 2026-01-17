# Python ETL Service - Function Audit

Generated: 2026-01-17

## Summary by File (137 total functions)

| File | Count |
|------|-------|
| `app/services/house_etl.py` | 25 |
| `app/services/ml_signal_model.py` | 17 |
| `app/services/senate_etl.py` | 15 |
| `app/services/auto_correction.py` | 14 |
| `app/services/error_report_processor.py` | 12 |
| `app/services/sandbox.py` | 10 |
| `app/services/politician_dedup.py` | 10 |
| `app/services/feature_pipeline.py` | 9 |
| `app/services/name_enrichment.py` | 6 |
| `app/services/party_enrichment.py` | 5 |
| `app/services/bioguide_enrichment.py` | 5 |
| `app/services/ticker_backfill.py` | 4 |
| `app/routes/quality.py` | 3 |
| `app/services/parser.py` | 1 |
| `app/routes/etl.py` | 1 |

---

## Full Function List by File

### app/routes/etl.py
| Line | Function |
|------|----------|
| 281 | `parse_pdf_url` |

### app/routes/quality.py
| Line | Function |
|------|----------|
| 22 | `get_supabase` |
| 31 | `get_polygon_api_key` |
| 335 | `validate_record_integrity` |

### app/services/auto_correction.py
| Line | Function |
|------|----------|
| 87 | `__init__` |
| 91 | `_get_supabase` |
| 101 | `correct_ticker` |
| 141 | `correct_value_range` |
| 183 | `correct_date_format` |
| 238 | `correct_amount_text` |
| 309 | `run_ticker_corrections` |
| 350 | `run_value_range_corrections` |
| 404 | `_apply_correction` |
| 432 | `_apply_range_correction` |
| 459 | `_apply_amount_correction` |
| 486 | `_log_correction` |
| 519 | `_mark_correction_applied` |
| 532 | `rollback_correction` |

### app/services/bioguide_enrichment.py
| Line | Function |
|------|----------|
| 32 | `get_supabase_client` |
| 43 | `normalize_name` |
| 120 | `fetch_politicians_without_bioguide` |
| 142 | `update_politician_from_congress` |
| 221 | `match_politicians` |

### app/services/error_report_processor.py
| Line | Function |
|------|----------|
| 58 | `__init__` |
| 63 | `_get_supabase` |
| 69 | `_get_ollama_client` |
| 76 | `test_connection` |
| 84 | `get_pending_reports` |
| 103 | `interpret_corrections` |
| 151 | `_build_prompt` |
| 196 | `process_report` |
| 266 | `_apply_corrections` |
| 321 | `_normalize_party` |
| 332 | `_update_report_status` |
| 346 | `process_all_pending` |

### app/services/feature_pipeline.py
| Line | Function |
|------|----------|
| 40 | `get_supabase` |
| 45 | `generate_label` |
| 79 | `__init__` |
| 175 | `_aggregate_by_week` |
| 367 | `_extract_features` |
| 447 | `__init__` |
| 467 | `to_dict` |
| 594 | `get_training_job` |
| 599 | `create_training_job` |

### app/services/house_etl.py
| Line | Function |
|------|----------|
| 52 | `__init__` |
| 62 | `record_success` |
| 74 | `record_error` |
| 98 | `get_stats` |
| 147 | `parse_asset_type` |
| 156 | `parse_value_range` |
| 173 | `parse_dollar` |
| 207 | `_validate_and_correct_year` |
| 255 | `extract_dates_from_row` |
| 303 | `sanitize_string` |
| 315 | `clean_asset_name` |
| 365 | `extract_text_from_pdf` |
| 378 | `extract_tables_from_pdf` |
| 390 | `is_header_row` |
| 416 | `is_metadata_row` |
| 452 | `parse_transaction_from_row` |
| 585 | `get_zip_url` |
| 590 | `get_pdf_url` |
| 686 | `extract_index_file` |
| 699 | `parse_filing_date` |
| 709 | `parse_disclosure_record` |
| 749 | `parse_disclosure_index` |
| 768 | `get_supabase_client` |
| 779 | `find_or_create_politician` |
| 829 | `upload_transaction_to_supabase` |

### app/services/ml_signal_model.py
| Line | Function |
|------|----------|
| 57 | `get_supabase` |
| 62 | `ensure_storage_bucket_exists` |
| 82 | `upload_model_to_storage` |
| 117 | `download_model_from_storage` |
| 148 | `compute_feature_hash` |
| 163 | `__init__` |
| 182 | `prepare_features` |
| 217 | `train` |
| 309 | `predict` |
| 340 | `predict_batch` |
| 373 | `save` |
| 393 | `load` |
| 408 | `get_feature_importance` |
| 420 | `get_active_model` |
| 426 | `load_active_model` |
| 484 | `cache_prediction` |
| 512 | `get_cached_prediction` |

### app/services/name_enrichment.py
| Line | Function |
|------|----------|
| 37 | `get_supabase` |
| 147 | `parse_ollama_name_response` |
| 197 | `__init__` |
| 210 | `to_dict` |
| 358 | `get_name_job` |
| 363 | `create_name_job` |

### app/services/parser.py
| Line | Function |
|------|----------|
| 9 | `extract_ticker_from_text` |

### app/services/party_enrichment.py
| Line | Function |
|------|----------|
| 31 | `get_supabase` |
| 111 | `__init__` |
| 124 | `to_dict` |
| 235 | `get_job` |
| 240 | `create_job` |

### app/services/politician_dedup.py
| Line | Function |
|------|----------|
| 45 | `__init__` |
| 48 | `_get_supabase` |
| 54 | `normalize_name` |
| 105 | `find_duplicates` |
| 177 | `_pick_winner` |
| 187 | `score` |
| 198 | `_count_disclosures` |
| 217 | `merge_group` |
| 302 | `process_all` |
| 351 | `preview` |

### app/services/sandbox.py
| Line | Function |
|------|----------|
| 35 | `__init__` |
| 40 | `__call__` |
| 60 | `get_output` |
| 190 | `validate_code` |
| 236 | `compile_lambda` |
| 280 | `_create_safe_math_module` |
| 309 | `execute` |
| 349 | `execute_code` |
| 384 | `_signal_was_modified` |
| 393 | `apply_lambda_to_signals` |

### app/services/senate_etl.py
| Line | Function |
|------|----------|
| 110 | `upsert_senator_to_db` |
| 155 | `_upsert_senator_by_name` |
| 228 | `get_supabase_client` |
| 237 | `find_or_create_politician` |
| 290 | `clean_asset_name` |
| 311 | `upload_transaction_to_supabase` |
| 380 | `parse_asset_type` |
| 405 | `parse_value_range` |
| 413 | `sanitize_string` |
| 423 | `extract_tables_from_pdf` |
| 433 | `extract_text_from_pdf` |
| 444 | `is_header_row` |
| 451 | `parse_transaction_from_row` |
| 963 | `parse_datatables_record` |
| 1162 | `get_cell` |

### app/services/ticker_backfill.py
| Line | Function |
|------|----------|
| 20 | `get_supabase_client` |
| 77 | `extract_ticker_from_asset_name` |
| 277 | `extract_transaction_type_from_raw` |
| 414 | `is_metadata_only` |

---

## Duplicate Functions

**16 functions are duplicated across files** (excluding `__init__` and `to_dict`):

| Function | Count | Candidate for Refactoring |
|----------|-------|---------------------------|
| `get_supabase` | 5 | ✅ High priority |
| `get_supabase_client` | 4 | ✅ High priority |
| `_get_supabase` | 3 | ✅ High priority |
| `upload_transaction_to_supabase` | 2 | ✅ Medium priority |
| `sanitize_string` | 2 | ✅ Medium priority |
| `parse_value_range` | 2 | ✅ Medium priority |
| `parse_transaction_from_row` | 2 | ⚠️ May differ by chamber |
| `parse_asset_type` | 2 | ✅ Medium priority |
| `normalize_name` | 2 | ✅ Medium priority |
| `is_header_row` | 2 | ✅ Medium priority |
| `find_or_create_politician` | 2 | ✅ Medium priority |
| `extract_text_from_pdf` | 2 | ✅ High priority |
| `extract_tables_from_pdf` | 2 | ✅ High priority |
| `clean_asset_name` | 2 | ✅ Medium priority |

---

### Detailed Duplicate Locations

#### `get_supabase` (5 occurrences)
```
app/routes/quality.py:22
app/services/party_enrichment.py:31
app/services/name_enrichment.py:37
app/services/ml_signal_model.py:57
app/services/feature_pipeline.py:40
```

#### `get_supabase_client` (4 occurrences)
```
app/services/bioguide_enrichment.py:32
app/services/ticker_backfill.py:20
app/services/senate_etl.py:228
app/services/house_etl.py:768
```

#### `_get_supabase` (3 occurrences)
```
app/services/error_report_processor.py:63
app/services/politician_dedup.py:48
app/services/auto_correction.py:91
```

#### `upload_transaction_to_supabase` (2 occurrences)
```
app/services/senate_etl.py:311
app/services/house_etl.py:829
```

#### `sanitize_string` (2 occurrences)
```
app/services/senate_etl.py:413
app/services/house_etl.py:303
```

#### `parse_value_range` (2 occurrences)
```
app/services/senate_etl.py:405
app/services/house_etl.py:156
```

#### `parse_transaction_from_row` (2 occurrences)
```
app/services/senate_etl.py:451
app/services/house_etl.py:452
```

#### `parse_asset_type` (2 occurrences)
```
app/services/senate_etl.py:380
app/services/house_etl.py:147
```

#### `normalize_name` (2 occurrences)
```
app/services/bioguide_enrichment.py:43
app/services/politician_dedup.py:54
```

#### `is_header_row` (2 occurrences)
```
app/services/senate_etl.py:444
app/services/house_etl.py:390
```

#### `find_or_create_politician` (2 occurrences)
```
app/services/senate_etl.py:237
app/services/house_etl.py:779
```

#### `extract_text_from_pdf` (2 occurrences)
```
app/services/senate_etl.py:433
app/services/house_etl.py:365
```

#### `extract_tables_from_pdf` (2 occurrences)
```
app/services/senate_etl.py:423
app/services/house_etl.py:378
```

#### `clean_asset_name` (2 occurrences)
```
app/services/senate_etl.py:290
app/services/house_etl.py:315
```

---

## Refactoring Recommendations

### 1. Create `app/services/common/db.py`
Consolidate all Supabase client functions:
- `get_supabase()`
- `get_supabase_client()`

### 2. Create `app/services/common/pdf_utils.py`
Consolidate PDF extraction functions:
- `extract_text_from_pdf()`
- `extract_tables_from_pdf()`

### 3. Create `app/services/common/parsing.py`
Consolidate parsing utilities:
- `sanitize_string()`
- `parse_value_range()`
- `parse_asset_type()`
- `clean_asset_name()`
- `is_header_row()`
- `normalize_name()`

### 4. Create `app/services/common/politician.py`
Consolidate politician management:
- `find_or_create_politician()`
- `upload_transaction_to_supabase()`
