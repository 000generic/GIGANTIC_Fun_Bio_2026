<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: Workflow runbook for orthogroups_ocl_X_features.
Scope:   workflow-COPYME-orthogroups_ocl_X_features.
============================================================================ -->

# Workflow: orthogroups_ocl_X_features

## Where this fits

- Parent (BLOCK): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This workflow's AI execution guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from sibling subprojects' `output_to_input/` (paths in `START_HERE-user_config.yaml`)
- Outputs to `../../output_to_input/BLOCK_orthogroups_ocl_X_features/<run_label>/`

## Purpose

Integrate OCL orthogroup analysis (per species-tree structure) with dark
proteome / hotspot / secretome per-gene features. Produces three tables per
structure (integrated summary, block-state expanded, gene drill-down) plus a
shared gene→feature lookup.

## Usage

This is the **COPYME template**. For a real run, copy it to a `workflow-RUN_N-*`
sibling, edit the config, and run there (per §35):

```bash
cp -r workflow-COPYME-orthogroups_ocl_X_features workflow-RUN_1-orthogroups_ocl_X_features
cd workflow-RUN_1-orthogroups_ocl_X_features

# 1. Edit START_HERE-user_config.yaml:
#    - run_label (mirror the OCL run, e.g. species70_X_OrthoHMM)
#    - species_set_name
#    - execution_mode: "local" or "slurm"  (+ slurm_account / slurm_qos if slurm)
#    - inputs.* paths (verify each upstream output_to_input/ is populated)
# 2. Edit INPUT_user/structure_manifest.tsv (structure IDs; 001..105)
# 3. Run (single entry point for local or SLURM):
bash RUN-workflow.sh
```

On first run the conda env `aiG-integrator-orthogroups_ocl_X_features` is
created on-demand from `ai/conda_environment.yml`.

## Inputs

| Input | Source |
|-------|--------|
| OCL orthogroup summary + path_states (per structure) | `ocl_phylogenetic_structures/output_to_input/BLOCK_orthogroups_X_ocl/<run_label>/structure_NNN/` |
| dark proteome (per species) | `dark_proteomes/output_to_input/BLOCK_classify_dark_proteome/dark_proteome/` |
| hotspots (per species) | `hotspots/output_to_input/BLOCK_identify_hotspots/hotspots/` |
| secretome filtered (per species) | `secretome/output_to_input/STEP_2-filter_secretome/` |
| secretome evidence (per species) | `secretome/output_to_input/STEP_1-build_evidence_table/` |
| structures to integrate | `INPUT_user/structure_manifest.tsv` |

## Outputs

```
OUTPUT_pipeline/
├── _shared/1-output/
│   ├── 1_ai-gene_feature_lookup.tsv
│   └── 1_ai-feature_availability_summary.tsv
└── structure_NNN/
    ├── 2-output/2_ai-structure_NNN_orthogroups-integrated_summary.tsv   (Table 1)
    ├── 3-output/3_ai-structure_NNN_block_states-integrated_expanded.tsv (Table 2)
    ├── 4-output/4_ai-structure_NNN_genes-integrated_drilldown.tsv       (Table 3)
    └── 5-output/5_ai-structure_NNN-validation_report.txt
```

After a successful run, clean (infix-free) symlinks are created in
`../../output_to_input/BLOCK_orthogroups_ocl_X_features/<run_label>/structure_NNN/`.

## NextFlow cache reset (after editing scripts/config)

```bash
rm -rf work .nextflow .nextflow.log* slurm_logs
bash RUN-workflow.sh
```

Do NOT use `-resume` after script changes — stale cache can mask a fix
(`resume: false` is the default in the config).

## See also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — process list, execution modes, failure modes
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK concepts + output table schema
