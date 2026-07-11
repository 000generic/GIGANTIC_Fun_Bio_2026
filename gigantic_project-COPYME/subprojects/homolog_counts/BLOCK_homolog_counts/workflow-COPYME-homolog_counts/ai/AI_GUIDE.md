# AI_GUIDE: homolog_counts workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 22 (initial; in commit 8486969 sweep)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../../`](../../) — BLOCK_homolog_counts (the only BLOCK)
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — Level 2 concepts + schema
- Parent (subproject README): [`../../../README.md`](../../../README.md)
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from:
  - `../../../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/`
  - `../../../../trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/`
  - `../../../../trees_gene_families/output_to_input/`
  - species70 phyloname map (`../INPUT_user/`)
- Outputs to: `../../../output_to_input/BLOCK_homolog_counts/` (symlinks from `../OUTPUT_pipeline/`)
- 6 scripts (001 validate / 002-004 count three sources / 005 `write_run_log` per §45 / 006 rewrite column headers)
- Conda env: `aiG-homolog_counts-homolog_counts`

---

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE.md`) first. This guide focuses on running the workflow.

## Quick Reference

| User needs… | Go to… |
|---|---|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| Subproject concepts, output schema, path portability | `../../../AI_GUIDE.md` |
| Running the workflow | This file |

## Quick Start

1. Edit `START_HERE-user_config.yaml` at the workflow root:
   - Set `execution_mode:` to `"local"` (run here) or `"slurm"` (submit as job)
   - If `"slurm"`: set `slurm_account:` and `slurm_qos:`
   - Verify the four `inputs:` paths (species70 phyloname map + 3 upstream `output_to_input/` directories)
2. Run: `bash RUN-workflow.sh`

A single entrypoint handles both modes. When `execution_mode: "slurm"`, `RUN-workflow.sh` self-submits to SLURM via `sbatch --wrap` and re-enters itself on the compute node. This replaces the older two-file (`.sh` + `.sbatch`) pattern.

On first run, the conda env `aiG-homolog_counts-homolog_counts` is auto-created from `ai/conda_environment.yml` using `mamba` (preferred) or `conda` (fallback). Subsequent runs activate the existing env.

## Pipeline Steps

| # | Script | Purpose | Primary output |
|---|---|---|---|
| 1 | `001_ai-python-validate_species70_manifest.py` | Validate phyloname map; emit canonical alphabetical phyloname column order | `1-output/1_ai-species70_alphabetical_phylonames.tsv` |
| 2 | `002_ai-python-count-orthogroups_orthohmm.py` | Count orthogroups per species | `2-output/2_ai-counts-orthogroups_orthohmm.tsv` |
| 3 | `003_ai-python-count-trees_gene_groups.py` | Count HGNC gene group homologs per species | `3-output/3_ai-counts-trees_gene_groups.tsv` |
| 4 | `004_ai-python-count-trees_gene_families.py` | Count curated gene family homologs per species | `4-output/4_ai-counts-trees_gene_families.tsv` |
| 5 | `005_ai-python-write_run_log.py` | Write timestamped run log to `ai/logs/` and `5-output/` | `5-output/5_ai-run_log.md` |
| 6 | `006_ai-python-rewrite_species_column_headers.py` | Rewrite the 70 phyloname columns to short human-readable species labels; runs once per source count TSV | `6-/7-/8-output/*-short_species_headers.tsv` |

Scripts 002-004 are independent of each other and may run in parallel under NextFlow. All three read the canonical species70 column order from script 001's output to guarantee identical column shape across source TSVs. Script 006 runs three times (once per source count TSV, each downstream of its counter) writing short-header variants to `6-output/` (orthogroups), `7-output/` (gene groups), and `8-output/` (gene families). Script 005 (`write_run_log`) runs last, after all counts and header rewrites, per §45.

Path handling: `main.nf` passes `--workflow-root ${projectDir}/..` to scripts 001-004; each resolves its relative upstream input path against that absolute root so the paths survive execution inside NextFlow's `work/` task dir.

## Output Layout

```
workflow-COPYME-homolog_counts/
├── OUTPUT_pipeline/
│   ├── 1-output/1_ai-species70_alphabetical_phylonames.tsv
│   ├── 2-output/2_ai-counts-orthogroups_orthohmm.tsv
│   ├── 3-output/3_ai-counts-trees_gene_groups.tsv
│   ├── 4-output/4_ai-counts-trees_gene_families.tsv
│   ├── 5-output/5_ai-run_log.md
│   ├── 6-output/6_ai-counts-orthogroups_orthohmm-short_species_headers.tsv
│   ├── 7-output/7_ai-counts-trees_gene_groups-short_species_headers.tsv
│   └── 8-output/8_ai-counts-trees_gene_families-short_species_headers.tsv
└── ai/logs/<timestamp>_run_log.md
```

After successful run, `RUN-workflow.sh` creates symlinks from `../../output_to_input/BLOCK_homolog_counts/counts-<source>.tsv` → the corresponding `<N>-output/<N>_ai-counts-<source>.tsv`. Downstream subprojects can read stable paths regardless of run number.

## Verification Commands

```bash
# Column-count sanity (3 fixed + 70 species = 73)
head -1 OUTPUT_pipeline/2-output/2_ai-counts-orthogroups_orthohmm.tsv | tr '\t' '\n' | wc -l
head -1 OUTPUT_pipeline/3-output/3_ai-counts-trees_gene_groups.tsv   | tr '\t' '\n' | wc -l
head -1 OUTPUT_pipeline/4-output/4_ai-counts-trees_gene_families.tsv | tr '\t' '\n' | wc -l

# Identical species column order across all three sources
for f in OUTPUT_pipeline/{2,3,4}-output/*-counts-*.tsv; do
  head -1 "$f" | cut -f4-
done | sort -u | wc -l   # Expected: 1

# Row-count sanity
wc -l OUTPUT_pipeline/{2,3,4}-output/*-counts-*.tsv

# Symlinks created
ls -la ../../output_to_input/BLOCK_homolog_counts/
```

## Common Errors

| Error | Cause | Solution |
|---|---|---|
| `species70_phyloname_map: file not found` | Path moved or `/blue/` not mounted on host | Confirm path resolves: `ls -l <path>`; if running outside `/blue/`, mount or copy the map |
| Column count != 73 in any output | One counting script used a stale species order | Reset cache and re-run from script 001: `rm -rf work .nextflow .nextflow.log*; bash RUN-workflow.sh` |
| `species column order differs across sources` | Script 001 was skipped or its output edited | Rerun fresh; never edit `1_ai-species70_alphabetical_phylonames.tsv` by hand |
| `aiG-homolog_counts-homolog_counts: env exists with conflicts` | Partial previous create | `mamba env remove -n aiG-homolog_counts-homolog_counts -y` then re-run |
| Empty count TSV (one source) | Upstream `output_to_input/` not populated | Run upstream subproject first; verify its `output_to_input/` contains expected files |
| `mamba: command not found` and `conda: command not found` | Conda module not loaded (HPC) | `module load conda` before running, or run from a node where conda is on PATH |
| SLURM job submitted but pipeline doesn't run | `execution_mode: "slurm"` set without `slurm_account` / `slurm_qos` | Edit `START_HERE-user_config.yaml`, set both, then re-run |

## NextFlow Cache Reset

Before re-running after edits to scripts or config:

```bash
rm -rf work .nextflow .nextflow.log* slurm_logs
bash RUN-workflow.sh
```

Do NOT use `-resume` after script changes — stale cached scripts can mask the fix.

## Server Upload

Publishing to the GIGANTIC server uses the shared-helper mechanism (matching orthogroups / annotations_hmms / sequence_groups_X_species):

- This workflow ships a per-workflow `upload_manifest.tsv` (at the workflow root, next to `START_HERE-user_config.yaml`) listing the files to publish with self-documenting `display_label` / `description` / `order` columns. It travels with the workflow into each `workflow-RUN_*` dir.
- From the subproject root, run `bash RUN-update_upload_to_server.sh`. This thin wrapper calls `../../server/ai/update_upload_to_server.py`, which reads the newest `workflow-RUN_*/upload_manifest.tsv` and symlinks the files into `upload_to_server/BLOCK_homolog_counts/workflow-RUN_*/<N>-output/`, pruning superseded runs.
