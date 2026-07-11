# AI Guide: build_evidence_table Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 23 (workflow scaffold)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK_secretome_evidence_table
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — secretome overview
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from: `../../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/` + `../INPUT_user/proteome_manifest.tsv`
- Outputs to: `../../../output_to_input/BLOCK_secretome_evidence_table/` (symlinks from `../OUTPUT_pipeline/`)
- 3 scripts (validate / build_evidence_table / `write_run_log` per §45)
- Conda env: `aiG-secretome-build_evidence_table`

---

## Pipeline (3 NextFlow processes)

| # | Script | Function |
|---|--------|----------|
| 001 | `validate_proteome_manifest.py` | Validate manifest; fail-fast on missing proteomes |
| 002 | `build_evidence_table.py` | Pivot long-format DB → wide per-protein evidence table per species (STUB — pending finalization) |
| 003 | `write_run_log.py` | Timestamped run log per §45 |

## Status

Script 002 (`build_evidence_table.py`) is the substantive piece and is
**not yet finalized** — it was designed in 2026 May but column shape
depends on the upstream tool BLOCK output formats being settled. Check
the script header or the main.nf comment for current status.

## execution_mode

Set in `START_HERE-user_config.yaml`:
- `local` — sequential on the head node
- `slurm` — single SLURM allocation (recommended)
- `slurm_burst` — per-species fan-out to burst QOS

## See Also

- [`../README.md`](../README.md) — workflow usage + Quick Start
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK concepts
- [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — subproject Moroz spec
