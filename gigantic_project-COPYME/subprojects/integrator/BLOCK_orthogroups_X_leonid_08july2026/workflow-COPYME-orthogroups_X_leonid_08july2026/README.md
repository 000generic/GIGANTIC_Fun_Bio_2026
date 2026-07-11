<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 08
Human:   Eric Edsinger
Purpose: How to run the orthogroups_X_leonid_08july2026 integration workflow.
============================================================================ -->

# workflow — orthogroups_X_leonid_08july2026

Builds the per-orthogroup table (member sequences + Pfam/GO/PANTHER annotations +
species-tree deconvolution across structures 001, 003, 031, 032). See the BLOCK
[`../README.md`](../README.md) for what the table contains and
[`../AI_GUIDE.md`](../AI_GUIDE.md) / [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for design.

## Run it

```bash
# 1. Copy this COPYME dir to a run dir (convention: workflow-RUN_1-...)
#    (optional but recommended so the template stays clean)
# 2. Edit START_HERE-user_config.yaml:
#      run_label, species_set_name, annotation_sources,
#      inputs.deconvolution_structures,
#      execution_mode + slurm_account/slurm_qos (if slurm)
# 3. Run:
bash RUN-workflow.sh
```

`execution_mode: slurm` self-submits the driver as a SLURM job; `local` runs it
here. `parallelism_mode: local` runs the (few) processes within the allocation.

## Prerequisites (upstream output_to_input must be populated)

- `orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv`
- `annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`
  (`2_ai-<source>-annogroup_map.tsv` + `2_ai-<source>-annogroup_membership.tsv`)
  for each `annotation_sources` entry (default pfam, go, panther)
- `trees_species/output_to_input/BLOCK_permutations_and_features/Species_Clade_Species_Mappings/9_ai-clade_species_mappings-all_structures.tsv`

## Outputs

```
OUTPUT_pipeline/
├── 1-output/1_ai-orthogroups_X_leonid.tsv   # the table (headline deliverable)
└── 2-output/2_ai-validation_report.txt      # fail-fast validation (PASS/FAIL)
```

Plus symlinks under `../../output_to_input/BLOCK_orthogroups_X_leonid_08july2026/<run_label>/`.

## Resources

The build holds the protein→orthogroup map (~1.4M members) and streams three large
annogroup membership files, so it is memory-bound. Defaults: 4 cpus / 64 GB / 8 h
(edit `cpus`, `memory_gb`, `time_hours` in the config).

## Notes

- This is a COPYME template. If you run it in place, clear NextFlow cache between
  code changes: `rm -rf work .nextflow .nextflow.log*` then re-run without `-resume`.
