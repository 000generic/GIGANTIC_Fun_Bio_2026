# workflow-COPYME-build_evidence_table

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 23 (workflow scaffold)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_secretome_evidence_table (logically STEP_1)
- Parent (subproject): [`../../README.md`](../../README.md) — secretome overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/` + `INPUT_user/proteome_manifest.tsv`
- Outputs to: `../../output_to_input/BLOCK_secretome_evidence_table/`
- Downstream STEP: `../../STEP_2-filter_secretome/workflow-COPYME-filter_secretome/`
- 3 scripts (validate / build_evidence_table / `write_run_log` per §45)
- Conda env: `aiG-secretome-build_evidence_table`

---

Builds one wide per-protein **evidence table** TSV per species, pivoting from
the long-format standardized annotation database produced by
`annotations_hmms/BLOCK_build_annotation_database`. Each row in the output is
one protein. Each column group is one annotation tool's evidence for that
protein. Downstream code filters the evidence table into different secretome
variants ( strict, permissive, consensus, etc. ) with simple TSV queries —
no re-running of upstream tools required.

## Workflow inputs

Edit `START_HERE-user_config.yaml`. The workflow reads:

| Source | Path | Purpose |
|---|---|---|
| species manifest | `INPUT_user/proteome_manifest.tsv` | List of phylonames to process + paths to canonical proteome FASTAs |
| annotation database root | `START_HERE-user_config.yaml: annotation_database_dir` | Root of the long-format standardized DB produced by `BLOCK_build_annotation_database` ( contains `database_<name>/gigantic_annotations-database_<name>-<phyloname>.tsv` files ) |

## Workflow outputs

For each species in the manifest:
- `OUTPUT_pipeline/2-output/<phyloname>_evidence_table.tsv` — one row per protein, wide columns per annotation tool
- `OUTPUT_pipeline/2-output/2_ai-log-build_evidence_table_<phyloname>.log` — per-species build log

After successful completion, `RUN-workflow.sh` populates
`../../output_to_input/BLOCK_secretome_evidence_table/` with stable symlinks
to each per-species TSV for downstream subprojects.

## How to run

```
bash RUN-workflow.sh
```

When `execution_mode: "slurm"` in the config, `RUN-workflow.sh` self-submits.

## See also

- `ai/AI_GUIDE-build_evidence_table_workflow.md` — workflow execution detail
- `../AI_GUIDE-secretome_evidence_table.md` — BLOCK overview + schema
- `../../AI_GUIDE.md` — subproject overview
