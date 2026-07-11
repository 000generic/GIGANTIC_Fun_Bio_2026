<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 10
Human:   Eric Edsinger
Purpose: How to run the orthogroups_X_all_annotations integration workflow.
============================================================================ -->

# workflow — orthogroups_X_all_annotations

Builds the per-orthogroup table (member sequences + seven annotation types +
species-tree deconvolution across structures 001, 003, 031, 032). See the BLOCK
[`../README.md`](../README.md) for what the table contains and
[`../AI_GUIDE.md`](../AI_GUIDE.md) / [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for design.

## Run it

```bash
# 1. Copy this COPYME dir to a run dir (convention: workflow-RUN_1-...)
# 2. Edit START_HERE-user_config.yaml:
#      run_label, species_set_name, hmm_annotation_sources,
#      inputs.deconvolution_structures,
#      execution_mode + slurm_account/slurm_qos (if slurm)
# 3. Run:
bash RUN-workflow.sh
```

`execution_mode: slurm` self-submits the driver as a SLURM job; `local` runs it
here. `parallelism_mode: local` runs the (few) processes within the allocation.

## Prerequisites (upstream must be populated)

See `START_HERE-user_config.yaml` for the exact path of each of the seven
annotation sources plus the orthogroups spine and the clade species map. The probe
(now removed) confirmed all resolve: 70 pfam/panther/go per-species files, 76 gene
families, 2061 gene-group AGS files, 70 dark-proteome files, 64 hotspot files.

## Outputs

```
OUTPUT_pipeline/
├── 1-output/1_ai-orthogroups_X_all_annotations.tsv   # the table (headline deliverable)
└── 2-output/2_ai-validation_report.txt               # fail-fast validation (PASS/FAIL)
```

Plus symlinks under `../../output_to_input/BLOCK_orthogroups_X_all_annotations/<run_label>/`.

## Resources

The build holds the protein→orthogroup map (~1.4M members) plus per-sequence
aggregates for all seven annotation types, so it is memory-bound. Defaults:
4 cpus / 128 GB / 12 h (edit `cpus`, `memory_gb`, `time_hours` in the config).

## Notes

- This is a COPYME template. If you run it in place, clear NextFlow cache between
  code changes: `rm -rf work .nextflow .nextflow.log*` then re-run without `-resume`.
