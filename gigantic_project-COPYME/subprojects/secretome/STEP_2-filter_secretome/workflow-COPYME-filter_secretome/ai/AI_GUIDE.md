# AI Guide: filter_secretome Workflow (STEP_2)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 25 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — STEP_2-filter_secretome
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — secretome overview
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from:
  - `../../../output_to_input/STEP_1-build_evidence_table/` (upstream STEP_1)
  - `../../../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/` (canonical species70; 202,994 orthogroups / 1,375,926 members)
  - `../../../../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/`
  - `../INPUT_user/<filter_manifest>.json`
- Outputs to: `../../../output_to_input/STEP_2-filter_secretome/`
- 6 scripts; final = `write_run_log` per §45
- Conda env: `aiG-secretome-filter_secretome`

---

## Pipeline (execution order ≠ script-number order)

Per the main.nf comment block, execution order is **001 → 003 → 005 → 006 → 002 → 004**:

| Order | # | Script | Function |
|-------|---|--------|----------|
| 1 | 001 | `validate_filter_manifest.py` | JSON syntax + structure validation; fail-fast |
| 2 | 003 | `augment_with_derived_columns.py` | Cysteine count, Pfam max-per-accession (one row per protein → wider) |
| 3 | 005 | `augment_with_orthogroups.py` | OG_ID + total members + 4 model-species ortholog cols |
| 4 | 006 | `augment_with_blastp_top10.py` | Top 10 NCBI nr hits + e-values + headers |
| 5 | 002 | `apply_filters_per_species.py` | Filter manifest applied AFTER augment so filter clauses can reference derived/augmented cols |
| 6 | 004 | `write_run_log.py` | Final marker per §45 |

The non-sequential numbering preserves natural slots (001 validate /
004 write_run_log) while letting the augment scripts (003/005/006) run
before the filter (002) — necessary so filter expressions like
`Pfam_Max_Hits_Per_Single_Accession ≤ 4` can reference columns added
by the augmenters.

## Filter Manifest Format

`INPUT_user/<filter_manifest>.json` — referenced by `filter_manifest_filename`
in `START_HERE-user_config.yaml`. Each rule selects KEEPER/DROPPER on a
named column.

Typical filter columns:
- `Signal_Peptide_Prediction` — values like `"Sec/SPI"`, `"Sec/SPII"`, `"Tat/SPI"`, or `null`
- `DeepLoc_Transmembrane` / `DeepLoc_Extracellular` — probability thresholds
- `Pfam_Max_Hits_Per_Single_Accession` — ≤ N
- `Pfam_Unique_Accessions` — exact count
- `Cysteine_Count` — ≥ N
- `Orthogroup_Total_Members` — ≥ N
- `Blastp_Top10_Best_Evalue` — ≤ threshold

The exact column names available depend on the upstream evidence table
schema; check a sample evidence-table TSV for current column names.

## execution_mode

In `START_HERE-user_config.yaml`:
- `local` — sequential per-species on head node
- `slurm` — single SLURM allocation
- `slurm_burst` — per-species fan-out (recommended for species70)

## Multiple Filter Manifests in Parallel

To compare strict vs permissive vs consensus secretomes, create multiple
RUN_N sibling dirs each with a different `INPUT_user/<name>.json` manifest.
The output dirs are uniquely identified by the RUN_N name; symlinks into
`output_to_input/STEP_2-filter_secretome/` track the canonical run (per
§39 canonical-RUN rule for publishing).

## Common Failure Modes

| Error | Cause | Solution |
|-------|-------|----------|
| validate_filter_manifest: "unknown column X" | Filter rule references a column that doesn't exist in the upstream evidence table OR isn't added by any augmenter | Check a sample evidence-table TSV; use only columns that actually exist after augmenters run |
| augment_with_orthogroups: "OG not found for species X" | orthogroups subproject's OrthoHMM table doesn't include X | Verify orthogroups subproject completed for the same species set |
| augment_with_blastp_top10: "no nr hits for species X" | one_direction_homologs didn't run for X | Check the upstream blastp_top10 directory has species X |

## See Also

- [`../README.md`](../README.md) — workflow usage
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — STEP concepts
- [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — subproject overview + Moroz spec
- `../../../STEP_1-build_evidence_table/AI_GUIDE.md` — upstream STEP_1
