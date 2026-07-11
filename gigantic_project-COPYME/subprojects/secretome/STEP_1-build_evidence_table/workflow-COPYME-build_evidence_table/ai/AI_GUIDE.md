# AI Guide: build_evidence_table Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 23 (workflow scaffold)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — STEP_1-build_evidence_table
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — secretome overview
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from: `../../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/` + `../INPUT_user/proteome_manifest.tsv`
- Outputs to: `../../../output_to_input/STEP_1-build_evidence_table/` (symlinks from `../OUTPUT_pipeline/`)
- 3 scripts (validate / build_evidence_table / `write_run_log` per §45)
- Conda env: `aiG-secretome-build_evidence_table`

---

## Pipeline (3 NextFlow processes)

| # | Script | Function |
|---|--------|----------|
| 001 | `validate_proteome_manifest.py` | Validate manifest; fail-fast on missing proteomes |
| 002 | `build_evidence_table.py` | Pivot long-format DB → wide per-protein evidence table per species |
| 003 | `write_run_log.py` | Timestamped run log per §45 |

## Status

Operational. Script 002 (`build_evidence_table.py`) is the substantive piece
and is fully implemented: it pivots the long-format standardized annotation
database into one wide per-protein evidence table per species (default 6-tool
"Leonid simplified" column set), augmented with the full DeepLoc probability
vector. One evidence table per species is written to `2-output/` and exposed
via `output_to_input/STEP_1-build_evidence_table/` for STEP_2.

## Path handling

Upstream input paths in `START_HERE-user_config.yaml`
(`annotation_database_dir`, `deeploc_csv_dir`) are **relative** to the workflow
directory and consumed via `annotations_hmms/output_to_input/`. `main.nf`
passes an absolute `--workflow-root ${projectDir}/..` to script 002, which
resolves the relative paths against it so they survive NextFlow's `work/`
execution dirs.

## execution_mode

Set in `START_HERE-user_config.yaml`:
- `local` — sequential on the head node
- `slurm` — single SLURM allocation (recommended)

## See Also

- [`../README.md`](../README.md) — workflow usage + Quick Start
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK concepts
- [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — subproject Moroz spec
