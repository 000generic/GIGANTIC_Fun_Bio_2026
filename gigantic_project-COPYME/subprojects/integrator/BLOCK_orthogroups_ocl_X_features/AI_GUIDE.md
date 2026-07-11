<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: BLOCK-level AI guide for BLOCK_orthogroups_ocl_X_features — the
         integration design, output tables, and per-script pipeline.
Scope:   BLOCK_orthogroups_ocl_X_features.
============================================================================ -->

# AI Guide: BLOCK_orthogroups_ocl_X_features

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — integrator overview + join model
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-orthogroups_ocl_X_features/`](workflow-COPYME-orthogroups_ocl_X_features/)
- This BLOCK's workflow guide: [`workflow-COPYME-orthogroups_ocl_X_features/ai/AI_GUIDE.md`](workflow-COPYME-orthogroups_ocl_X_features/ai/AI_GUIDE.md)
- Reads FROM:
  - `../../ocl_phylogenetic_structures/output_to_input/BLOCK_orthogroups_X_ocl/<run_label>/structure_NNN/` — `4_ai-orthogroups-complete_ocl_summary.tsv` (spine) + `4_ai-path_states-per_orthogroup_per_species.tsv` (Table 2)
  - `../../dark_proteomes/output_to_input/BLOCK_classify_dark_proteome/dark_proteome/`
  - `../../hotspots/output_to_input/BLOCK_identify_hotspots/hotspots/`
  - `../../secretome/output_to_input/STEP_2-filter_secretome/` + `../../secretome/output_to_input/STEP_1-build_evidence_table/`
- Outputs TO: `../output_to_input/BLOCK_orthogroups_ocl_X_features/<run_label>/`
- Conda env: `aiG-integrator-orthogroups_ocl_X_features`

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../AI_GUIDE.md` |
| Conventions | `../../../ai/ai_FYIs/gigantic_conventions.md` |
| integrator concepts + join model | `../AI_GUIDE.md` |
| BLOCK concepts (this file) | This file |
| Running the workflow | `workflow-COPYME-orthogroups_ocl_X_features/ai/AI_GUIDE.md` |

## What this BLOCK does

For each phylogenetic species-tree structure, it integrates the OCL
orthogroup analysis with three per-gene feature sources (dark proteome,
hotspots, secretome), keyed on each orthogroup's member sequence IDs. See
`../AI_GUIDE.md` for the full join model, join keys, structure-invariance, and
species-set policy.

## Output tables (per structure)

Three tables per structure, written under
`OUTPUT_pipeline/structure_NNN/`:

### Table 1 — integrated orthogroup summary (`2-output/`)
One row per (structure, orthogroup): OCL spine columns (origin block/state/path,
conservation/loss/continued-absence counts, species count) + member
`Sequence_IDs` + per-source `*_Integration_Count`, `*_Integration_Sequence_IDs`,
and `*_Members_Available_Count` (the count's denominator, for transparency).

### Table 2 — block-state expanded (`3-output/`)
One row per (structure, orthogroup, phylogenetic block-state), carrying the
orthogroup's integration **counts** on each block where the orthogroup has a
**meaningful** state: **O = Origin, P = Conservation, L = Loss**. Lets a user
ask "at the node where this orthogroup originated / is conserved / was lost,
how many member genes integrate with each source?"

> **Counts-only (size decision, 2026-06-04, user-approved)**: Table 2 carries
> the integration *counts* (+ member count + availability) per block-state, NOT
> the sequence-ID list cells. Repeating the full member-ID lists on every
> block-state row produced ~20 GB/structure (~2 TB across 105). The actual IDs
> live once-per-orthogroup in Table 1 and per-gene in Table 3 — join on
> `Orthogroup_ID` to recover them for any block-state row.

> **Design decision (documented, revisitable)**: inherited-absence states
> **A** and **X** are intentionally **excluded** — the orthogroup is absent on
> those blocks, so there are no member genes to integrate. If absence rows are
> wanted later, add them in Script 003.

### Table 3 — gene-level drill-down (`4-output/`)
One row per (structure, orthogroup, member gene): the gene's `Is_Dark` /
`In_Hotspot` / `Hotspot_ID` / `Is_Secreted` plus the secretome **evidence**
columns (SignalP call/probability, DeepLoc Extracellular/Transmembrane, Pfam
counts), carrying the orthogroup's origin block/state for context. This is
where the richer per-gene evidence lives (Table 1/2 keep count + ID-list cells).

A structure-invariant gene→feature lookup
(`OUTPUT_pipeline/_shared/1-output/1_ai-gene_feature_lookup.tsv`) and a
per-species availability summary are built once and feed all three tables.

## Pipeline (6 scripts + utils)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 001 | `build_feature_lookup.py` | `build_feature_lookup` (singleton) | Build the structure-invariant gene→feature lookup + availability summary; fail-fast if no source has data |
| 002 | `build_integrated_summary.py` | `build_integrated_summary` (per structure) | Table 1 — join lookup onto the OCL orthogroup summary |
| 003 | `build_block_state_expanded.py` | `build_block_state_expanded` (per structure) | Table 2 — explode Table 1 across O/P/L block-states from OCL path_states |
| 004 | `build_gene_drilldown.py` | `build_gene_drilldown` (per structure) | Table 3 — one row per member gene with features + evidence |
| 005 | `validate_results.py` | `validate_results` (per structure) | Cross-check tables (counts vs id-lists vs availability; Table 3 row total; Table 2 referential integrity); fail-fast per §36 |
| 006 | `write_run_log.py` | `write_run_log` | Timestamped run log per §45 |
| — | `utils_integrator.py` | — | Shared helpers (config, ID parsing, header indexing, `DELIM`) |

Scripts are sequential per structure but parallel across structures (NextFlow
manages this); the `_shared` lookup is built once and gates the per-structure
fan-out.

## Delimiter

In-column sequence-ID lists use **bare commas** (`,`) per §34.

## See also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — integrator join model, join keys, OCL path_states exposure + symlink repair note
- [`workflow-COPYME-orthogroups_ocl_X_features/ai/AI_GUIDE.md`](workflow-COPYME-orthogroups_ocl_X_features/ai/AI_GUIDE.md) — workflow execution
