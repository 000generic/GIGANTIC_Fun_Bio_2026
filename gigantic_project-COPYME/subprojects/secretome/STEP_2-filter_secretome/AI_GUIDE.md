# AI Guide: STEP_2-filter_secretome

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 25 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — secretome overview
- Parent (subproject README): [`../README.md`](../README.md)
- Upstream unit: [`../STEP_1-build_evidence_table/`](../STEP_1-build_evidence_table/) (STEP_1; produces the evidence tables this STEP consumes)
- Workflow template: [`workflow-COPYME-filter_secretome/`](workflow-COPYME-filter_secretome/)
- This STEP's workflow guide: [`workflow-COPYME-filter_secretome/ai/AI_GUIDE.md`](workflow-COPYME-filter_secretome/ai/AI_GUIDE.md)
- Reads FROM:
  - `../output_to_input/STEP_1-build_evidence_table/` (upstream — per-species wide evidence tables)
  - `../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/` (for orthogroup augmentation in script 005; canonical species70, 202,994 orthogroups)
  - `../../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/` (for blastp_top10 augmentation in script 006)
  - `INPUT_user/<filter_manifest>.json` (user-defined filter rules)
- Outputs TO: `../output_to_input/STEP_2-filter_secretome/` — per-species filtered secretome tables
- 6 scripts (validate / apply_filters / augment×3 / `write_run_log` per §45)
- Conda env: `aiG-secretome-filter_secretome`

---

## Purpose

Consumes the wide per-species evidence tables from
`STEP_1-build_evidence_table` (STEP_1), augments with
derived columns + orthogroups + top-10 BLAST hits, applies a
user-defined JSON filter manifest, and emits the per-species filtered
secretome.

## Pipeline (6 scripts — execution order ≠ numeric order)

Per script header in `main.nf`:

| Order | # | Script | Function |
|-------|---|--------|----------|
| 1 | 001 | `validate_filter_manifest.py` | JSON syntax + structure validation |
| 2 | 003 | `augment_with_derived_columns.py` | Cysteine count, Pfam max-per-accession |
| 3 | 005 | `augment_with_orthogroups.py` | OG_ID + total members + 4 model-species ortholog cols |
| 4 | 006 | `augment_with_blastp_top10.py` | Top 10 NCBI nr hits + e-values + headers |
| 5 | 002 | `apply_filters_per_species.py` | Filter manifest applied AFTER augment so filter clauses can reference derived cols |
| 6 | 004 | `write_run_log.py` | Final marker per §45 |

The non-sequential numbering reflects design evolution: validate (001)
and write_run_log (004) keep their natural slots; augmenters (003/005/006)
run before the filter (002) so filter expressions can reference augmented
columns.

## Why "STEP_2"

This unit is correctly named STEP_2 — it depends sequentially on STEP_1
(`STEP_1-build_evidence_table`). Per §41, sequential-dependency units
should be STEP_*. The naming inconsistency is on the upstream unit
(see subproject AI_GUIDE) — this one is canonical.

## Filter Manifest

`INPUT_user/<name>.json` — user-defined filter rules. Each rule selects
KEEPER/DROPPER on a column (e.g., `Pfam_Max_Hits_Per_Single_Accession ≤ 4`,
`Signal_Peptide_Prediction = "Sec/SPI"`). Multiple filter manifests can
be tested in parallel by creating multiple RUN_N dirs each with their
own filter manifest.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — subproject overview + Moroz spec
- [`workflow-COPYME-filter_secretome/README.md`](workflow-COPYME-filter_secretome/README.md) — workflow usage
- [`workflow-COPYME-filter_secretome/ai/AI_GUIDE.md`](workflow-COPYME-filter_secretome/ai/AI_GUIDE.md) — workflow execution
- `../STEP_1-build_evidence_table/AI_GUIDE.md` — upstream STEP_1
