# AI Guide: STEP_1-build_evidence_table

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
- Outputs TO: `../output_to_input/STEP_1-build_evidence_table/` — one wide TSV per species
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
| 002 | `build_evidence_table.py` | Pivot the long-format standardized annotation database → one wide per-protein evidence table per species |
| 003 | `write_run_log.py` | Timestamped run log per §45 |

## Status

Operational. All three scripts are implemented. Script 002
(`build_evidence_table.py`) pivots the long-format standardized annotation
database (consumed from `annotations_hmms/output_to_input/`) into one wide
per-protein evidence table per species, augmented with the full DeepLoc
probability vector. Latest run: `workflow-RUN_1-build_evidence_table`
(70 species).

## Naming Note

This unit is named `STEP_1-build_evidence_table` because its output is the
required input to `STEP_2-filter_secretome` — a sequential dependency that
per §41 + memory `feedback_block_vs_step_semantics` calls for a `STEP_`
prefix. It was originally scaffolded as `BLOCK_secretome_evidence_table`
and has since been renamed to `STEP_1-build_evidence_table`.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — subproject overview + Moroz spec detail
- [`workflow-COPYME-build_evidence_table/README.md`](workflow-COPYME-build_evidence_table/README.md) — workflow usage
- [`workflow-COPYME-build_evidence_table/ai/AI_GUIDE.md`](workflow-COPYME-build_evidence_table/ai/AI_GUIDE.md) — workflow execution
- `../STEP_2-filter_secretome/AI_GUIDE.md` — downstream STEP that consumes evidence tables
