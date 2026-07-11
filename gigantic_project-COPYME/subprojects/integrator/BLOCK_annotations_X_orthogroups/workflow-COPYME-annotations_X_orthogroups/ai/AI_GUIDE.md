<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 09
Human:   Eric Edsinger
Purpose: Workflow execution AI guide for annotations_X_orthogroups.
Scope:   workflow-COPYME-annotations_X_orthogroups (execution detail).
============================================================================ -->

# AI Guide: annotations_X_orthogroups Workflow

**For AI Assistants**: Read the BLOCK guide (`../../AI_GUIDE.md`) and the
subproject guide (`../../../AI_GUIDE.md`) first. This file focuses on running
the workflow.

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Outputs to: `../../../output_to_input/BLOCK_annotations_X_orthogroups/<run_label>/`

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| integrator concepts + join model | `../../../AI_GUIDE.md` |
| BLOCK concepts + output schema | `../../AI_GUIDE.md` |
| Running the workflow | This file |

## Pipeline (5 NextFlow processes)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 001 | `classify_orthogroups.py` | `classify_orthogroups` | Classify every orthogroup into 4 classes (`bilaterian_only` / `mixed_with_bilaterian` / `non_bilaterian_metazoan` / `non_metazoan_only`) via the Bilateria (`C103`) + Metazoa (`C082`) species sets → `1-output/`; fail-fast if the clade row or inputs are missing |
| 002 | `build_nonbilaterian_orthogroups.py` | `build_nonbilaterian_orthogroups` | Table 2 — filter the composition table to `non_bilaterian_metazoan` (qualifying) → `2-output/` |
| 003 | `build_annogroup_X_orthogroups.py` | `build_annogroup_X_orthogroups` | Table 1 — join annogroup membership onto the protein→orthogroup map; keep annogroups with ≥1 non-bilaterian-metazoan (qualifying) orthogroup → `3-output/` |
| 004 | `validate_results.py` | `validate_results` | Cross-checks (class validity, Table 2 count, Table 1 arithmetic + referential integrity + keep-rule); fail-fast (§36) → `4-output/` |
| 005 | `write_run_log.py` | `write_run_log` | Run log → `ai/logs/` (§45) |
| — | `utils_integrator.py` | — | Shared helpers (config, GIGANTIC-ID parsing, header indexing, `DELIM`) |

Wiring (`main.nf`): `classify_orthogroups` runs once; its readiness broadcasts to
`build_nonbilaterian_orthogroups` and `build_annogroup_X_orthogroups` (both depend
only on it). A `.mix().collect()` barrier ensures both tables are written before
`validate_results`, then `write_run_log`. No per-structure fan-out — this is a
structure-independent integration.

## NextFlow Strict-DSL Posture

`main.nf` avoids top-level `def` / `import` / `workflow.onComplete`. Parameters
come from `-params-file START_HERE-user_config.yaml` (universal GIGANTIC
YAML→params pattern); SLURM account/qos + cpus/memory_gb flow through to
`nextflow.config` as `params.*`. Conda env pins `nextflow>=23.0,<26.0`.

## execution_mode and parallelism_mode

`START_HERE-user_config.yaml`:
- `execution_mode`: where the driver runs — `local` or `slurm` (self-submits via
  `sbatch --wrap`).
- `parallelism_mode`: how processes dispatch — `local` (default; the handful of
  processes run within the allocation) or `slurm` (one SLURM job per process).

This BLOCK is light (dict joins over the orthogroup + annogroup tables; the
protein→orthogroup map of ~1.4M proteins dominates memory). `execution_mode: slurm`
with `parallelism_mode: local` is the natural choice.

## Common failure modes

| Error | Cause | Solution |
|-------|-------|----------|
| `clade '...' not found in mapping file` (001) | `bilateria_clade_id_name` / `metazoa_clade_id_name` / `clade_reference_structure` wrong | Check `awk -F'\t' '$2 ~ /^C103/' <mappings>` resolves a row |
| `orthogroups file not found` (001/003) | `inputs.orthogroups_file` wrong/empty | Verify `orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv` |
| `annogroup membership file not found` (003) | annogroups subproject not run, or `annogroups_dir` wrong | Verify `2_ai-<source>-annogroup_membership.tsv` exists under `<annogroups_dir>/<species_set>/<source>/` (see annogroups subproject) |
| `annogroup map not found` (003) | `annogroups_dir`/`species_set`/`source` wrong | `ls <annogroups_dir>/<species_set>/<source>/` |
| validation FAIL (004) | class/arithmetic/referential mismatch | Read `4-output/4_ai-validation_report.txt`; investigate the offending table |

## Diagnostic commands

```bash
# Composition class distribution
cut -f7 OUTPUT_pipeline/1-output/1_ai-orthogroups-species_composition.tsv | tail -n +2 | sort | uniq -c

# Table row counts
wc -l OUTPUT_pipeline/2-output/*.tsv OUTPUT_pipeline/3-output/*.tsv

# Validation verdict
grep -A2 Status OUTPUT_pipeline/4-output/4_ai-validation_report.txt

# Downstream symlinks created
ls -la ../../../output_to_input/BLOCK_annotations_X_orthogroups/*/
```

## NextFlow cache reset

```bash
rm -rf work .nextflow .nextflow.log* slurm_logs
bash RUN-workflow.sh   # fresh, no -resume
```

## Validated first-run reference (species70_pfam_X_OrthoHMM)

An end-to-end run (2026-06-09) produced: 202,994 orthogroups classified
(121,403 bilaterian_only / 12,200 mixed_with_bilaterian / 31,092
non_bilaterian_metazoan [qualifying] / 38,299 non_metazoan_only); Table 2 =
31,092 rows; 73,954 annogroups read (feature+combination+architecture+absent) → 3,214 kept; validation PASS.
Treat as an order-of-magnitude sanity reference, not a guarantee.

## See also

- [`../README.md`](../README.md) — runbook + I/O
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — output table schema + join model
- [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — integrator join model + annogroups subproject inputs
