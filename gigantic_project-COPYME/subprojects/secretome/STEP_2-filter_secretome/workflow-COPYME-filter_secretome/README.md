# workflow-COPYME-filter_secretome

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 25 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP: [`../AI_GUIDE.md`](../AI_GUIDE.md) — STEP_2-filter_secretome
- Parent (subproject): [`../../README.md`](../../README.md) — secretome overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from:
  - `../../output_to_input/STEP_1-build_evidence_table/` (upstream STEP_1 wide tables)
  - `../../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/` (orthogroup augmentation; canonical species70, 202,994 orthogroups)
  - `../../../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/` (blastp_top10 augmentation)
  - `INPUT_user/<filter_manifest>.json` (user-defined filter rules)
- Outputs to: `../../output_to_input/STEP_2-filter_secretome/`
- 6 scripts; final = `write_run_log` per §45
- Conda env: `aiG-secretome-filter_secretome`

---

## Purpose

Workflow template for STEP_2: filter the per-species evidence tables
into per-species secretome tables, augmenting with derived columns,
orthogroups, and top-10 BLAST hits along the way.

## Prerequisites

1. **STEP_1 (STEP_1-build_evidence_table) complete** —
   `../../output_to_input/STEP_1-build_evidence_table/` populated
2. **orthogroups** complete (for `augment_with_orthogroups`)
3. **one_direction_homologs** complete (for `augment_with_blastp_top10`)
4. **User filter manifest** in `INPUT_user/<name>.json`

## Usage

```bash
cp -r workflow-COPYME-filter_secretome workflow-RUN_1-filter_secretome
cd workflow-RUN_1-filter_secretome

# Place filter manifest in INPUT_user/
vi INPUT_user/strict_secretome.json

# Edit YAML (execution_mode + filter_manifest_filename)
vi START_HERE-user_config.yaml

# Run
bash RUN-workflow.sh
```

To test multiple filter manifests in parallel, make multiple RUN_N
sibling dirs each with its own `INPUT_user/<manifest>.json`.

## Outputs

`OUTPUT_pipeline/`:
- `1-output/` — validated filter manifest
- `2-output/` — filtered per-species secretome tables (final output)
- `3-output/` — derived-column augmented tables
- `4-output/` — run log
- `5-output/` — orthogroup-augmented tables
- `6-output/` — blastp_top10-augmented tables

(Note: process numbering reflects design evolution — see ai/AI_GUIDE.md
for execution order.)

Symlinked into `../../output_to_input/STEP_2-filter_secretome/`.

## See Also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — workflow execution + filter-manifest format
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — STEP concepts
- `../../STEP_1-build_evidence_table/README.md` — upstream STEP_1
