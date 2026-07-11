<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 09
Human:   Eric Edsinger
Purpose: User-facing runbook for the annotations_X_orthogroups workflow.
Scope:   workflow-COPYME-annotations_X_orthogroups.
============================================================================ -->

# Workflow: annotations_X_orthogroups

Integrates **pfam annogroups** with **orthogroups**, focused on
**non-bilaterian-metazoan** orthogroups. Produces two tables.

## Where this fits

- Parent (BLOCK): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Inputs (all from upstream `output_to_input/`, set in `START_HERE-user_config.yaml`):
  pfam annogroups — map + membership read directly from the `annogroups` subproject
  (`annogroups/output_to_input/BLOCK_build_annogroups`),
  orthogroups (`orthogroups/BLOCK_orthohmm_GIGANTIC`),
  Bilateria + Metazoa species sets (`trees_species`)
- Outputs: `../../../output_to_input/BLOCK_annotations_X_orthogroups/<run_label>/`

## What you get

- **Table 1 — annogroups X orthogroups** (`OUTPUT_pipeline/3-output/`): one row
  per **kept annogroup**. An annogroup is kept when at least one of the
  orthogroups its member proteins fall into is **qualifying** (zero bilaterians
  AND ≥1 non-bilaterian metazoan); annogroups with no qualifying orthogroup are
  dropped. All of a kept annogroup's orthogroups are reported, grouped by the four
  composition classes (non_bilaterian_metazoan, non_metazoan_only, bilaterian_only,
  mixed_with_bilaterian), with per-class counts and ID lists, plus the annogroup's
  pfam accessions/definitions.
- **Table 2 — non-bilaterian-metazoan orthogroups** (`OUTPUT_pipeline/2-output/`):
  one row per **qualifying** orthogroup (no bilaterians, ≥1 non-bilaterian
  metazoan; non-metazoan unicells may ride along).
- **Supporting** (`OUTPUT_pipeline/1-output/`): every orthogroup classified into
  one of the four composition classes (the basis for both tables).

The research question: *which pfam annotation groups are represented in
orthogroups present in non-bilaterian metazoans but absent from bilaterians?*

## Join model

The annogroup↔orthogroup link is **shared member proteins** (full GIGANTIC IDs).
Each protein belongs to one annogroup per type, and at most one orthogroup. Member species are split three ways using two
`trees_species` clades (Bilateria `C103` ⊂ Metazoa `C082`): **bilaterian** (in
Bilateria), **non-bilaterian metazoan** (in Metazoa, not Bilateria), **non-metazoan**
(not in Metazoa; unicellular outgroups). A **qualifying** orthogroup has zero
bilaterians and ≥1 non-bilaterian metazoan. This is a **structure-independent**
integration (annogroup membership, orthogroup membership, and the clade species
sets are all invariant across the 105 species-tree structures), so there is no
per-structure fan-out.

## Quick start

```bash
cd workflow-COPYME-annotations_X_orthogroups   # (copy to workflow-RUN_N for a real run)
# 1. Edit START_HERE-user_config.yaml: run_label, species_set_name,
#    annogroup_types, execution_mode (+ slurm_account/slurm_qos if slurm),
#    input paths, bilateria_clade_id_name + metazoa_clade_id_name
# 2. Run:
bash RUN-workflow.sh
```

## Inputs / Outputs

| | Path | Notes |
|---|---|---|
| In | `inputs.annogroups_dir/<species_set>/<source>/2_ai-<source>-annogroup_membership.tsv` | annogroup member `Sequence_IDs` (from the annogroups subproject) |
| In | `inputs.annogroups_dir/<species_set>/<source>/2_ai-<source>-annogroup_map.tsv` | annogroup type + pfam accessions/definitions (from the annogroups subproject) |
| In | `inputs.orthogroups_file` | headerless orthogroup membership |
| In | `inputs.clade_species_mappings` (+ `bilateria_clade_id_name`, `metazoa_clade_id_name`) | Bilateria + Metazoa species sets |
| Out | `OUTPUT_pipeline/1-output/1_ai-orthogroups-species_composition.tsv` | all orthogroups classified |
| Out | `OUTPUT_pipeline/2-output/2_ai-nonbilaterian_metazoan_orthogroups.tsv` | Table 2 |
| Out | `OUTPUT_pipeline/3-output/3_ai-annogroups_X_orthogroups.tsv` | Table 1 |
| Out | `OUTPUT_pipeline/4-output/4_ai-validation_report.txt` | fail-fast validation (§36) |

## See also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — pipeline wiring + execution detail
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK output schema + join model
