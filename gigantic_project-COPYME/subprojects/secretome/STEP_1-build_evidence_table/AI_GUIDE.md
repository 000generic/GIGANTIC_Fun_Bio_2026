# AI Guide: BLOCK_secretome_evidence_table

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 23 (workflow scaffold)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — secretome overview + naming inconsistency note
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-build_evidence_table/`](workflow-COPYME-build_evidence_table/)
- This BLOCK's workflow guide: [`workflow-COPYME-build_evidence_table/ai/AI_GUIDE.md`](workflow-COPYME-build_evidence_table/ai/AI_GUIDE.md)
- Reads FROM:
  - `../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/` — long-format standardized DB
  - `INPUT_user/proteome_manifest.tsv` — list of phylonames + proteome FASTA paths
- Outputs TO: `../output_to_input/BLOCK_secretome_evidence_table/` — one wide TSV per species
- Downstream STEP: `../STEP_2-filter_secretome/` consumes the evidence tables
- 3 scripts (validate / build_evidence_table / `write_run_log` per §45)
- Conda env: `aiG-secretome-build_evidence_table`

---

## Purpose

Pivot the long-format standardized annotation database produced by
`annotations_hmms/BLOCK_build_annotation_database` into ONE wide
per-protein evidence-table TSV per species.

- **Input layout** (long): many rows per protein, one per annotation event
  (Phyloname, Sequence_Identifier, Domain_Start, Domain_Stop, Database_Name,
  Annotation_Identifier, Annotation_Details).
- **Output layout** (wide): one row per protein, column groups per tool
  (SignalP evidence, DeepLoc probabilities, Pfam domains, etc.).

The wide layout lets `STEP_2-filter_secretome/` apply simple TSV-query
filters without re-running upstream tools.

## Pipeline (3 scripts)

| # | Script | Function |
|---|--------|----------|
| 001 | `validate_proteome_manifest.py` | Validate `INPUT_user/proteome_manifest.tsv`; pair each phyloname with its proteome path |
| 002 | `build_evidence_table.py` | (Substantive pivot) — STUB / pending finalization |
| 003 | `write_run_log.py` | Timestamped run log per §45 |

## Status (2026-05-26)

Validate + run-log implemented. Script 002 (`build_evidence_table.py`)
is designed but pending finalization — the upstream tool BLOCKs
(annotations_hmms) had to settle first before the column shape could
be locked in.

## Naming Note

This unit is named `BLOCK_secretome_evidence_table` but is logically
STEP_1 — its output is the required input to `STEP_2-filter_secretome`.
Per §41 + memory `feedback_block_vs_step_semantics`, sequential-dependency
units should be named `STEP_*`. Renaming is out of scope for the docs
pass; flagged in the subproject AI_GUIDE for future cleanup.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — subproject overview + Moroz spec detail
- [`workflow-COPYME-build_evidence_table/README.md`](workflow-COPYME-build_evidence_table/README.md) — workflow usage
- [`workflow-COPYME-build_evidence_table/ai/AI_GUIDE.md`](workflow-COPYME-build_evidence_table/ai/AI_GUIDE.md) — workflow execution
- `../STEP_2-filter_secretome/AI_GUIDE.md` — downstream STEP that consumes evidence tables
