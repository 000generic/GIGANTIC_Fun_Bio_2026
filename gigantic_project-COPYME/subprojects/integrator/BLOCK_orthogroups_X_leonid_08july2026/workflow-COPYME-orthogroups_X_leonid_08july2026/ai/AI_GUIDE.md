<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 08
Human:   Eric Edsinger
Purpose: Level-3 workflow guide — running orthogroups_X_leonid_08july2026.
============================================================================ -->

# AI_GUIDE — orthogroups_X_leonid_08july2026 (workflow)

**For AI assistants**: Read the BLOCK guide ([`../../AI_GUIDE.md`](../../AI_GUIDE.md))
first for the join design and output schema. This guide focuses on execution.

## Pipeline (main.nf)

```
build_leonid_table (001) ──► validate_results (002) ──► write_run_log (003)
```

All three carry `label 'local'`; with `parallelism_mode: local` they run inside the
driver allocation. Paths are resolved by each script from
`../START_HERE-user_config.yaml` (relative to the workflow dir; §5).

## Scripts (ai/scripts/)

| Script | Runs | Reads | Writes |
|--------|------|-------|--------|
| `001_ai-python-build_leonid_table.py` | once | orthogroups spine; annogroup map+feature membership (pfam/go/panther); clade species map (selected structures) | `1-output/1_ai-orthogroups_X_leonid.tsv` |
| `002_ai-python-validate_results.py` | once | the 001 table + input orthogroup count | `2-output/2_ai-validation_report.txt` |
| `003_ai-python-write_run_log.py` | once | — | `ai/logs/run_*.log` |
| `utils_orthogroups_X_leonid.py` | — | shared helpers (config, path resolution, phyloname→Genus_species, header index, delimiters) | — |

## Config knobs (START_HERE-user_config.yaml)

- `run_label`, `species_set_name`
- `annotation_sources` — ordered list of annogroup sources → paired
  `<Display>_Accessions` / `<Display>_Names` columns (default pfam, go, panther)
- `inputs.deconvolution_structures` — the species-tree structures to deconvolve
  across (default 001, 003, 031, 032)
- `inputs.{orthogroups_file, annogroups_dir, clade_species_mappings}`
- `cpus` / `memory_gb` / `time_hours` — SLURM job + local executor sizing
- `execution_mode` (local | slurm), `slurm_account`, `slurm_qos`,
  `parallelism_mode` (local | slurm), `resume`

## How the columns are built (Script 001)

1. Load the clade map filtered to the selected structures → non-redundant clade
   union (root→tips), per-clade species sets, which structures each clade is in,
   the species tips, and the full-coverage (root) clades. Rule-6 validated.
2. Load orthogroups → ordered `(OG, members)` list + `sequence → OG` map.
3. Per source: read the map's feature rows → `accession → name`; stream the
   feature membership, aggregating per OG the non-redundant accession set.
4. Write one row per OG: fixed columns, per-source accessions + aligned names,
   then per-clade member-sequence counts (member counted in every ancestor clade).

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CRITICAL ERROR: required input not found` | upstream `output_to_input/` not populated, or path wrong | populate the upstream BLOCK; check the `inputs.*` paths |
| `... selected structure(s) not found` | a `deconvolution_structures` id is not in the clade map | fix the structure ids (`structure_001` form) |
| `... member ... is not a tree tip` | orthogroups and the clade map are different species sets | align `species_set_name` / the clade map to the orthogroups run |
| `... annotated sequence(s) absent from the orthogroups` | annogroups and orthogroups built on different proteomes/IDs | check both use the same species set; offenders written to `1-output/1_ai-<source>-sequences_absent_from_orthogroups.tsv` |
| `... name ... contains ' // '` | an annotation name contains the NAME delimiter | investigate that name; pick a different `NAME_DELIM` in `utils`; do not silently strip (research integrity) |
| out-of-memory | membership files are large | raise `memory_gb` (default 64) |
| stale results after editing scripts | NextFlow cache | `rm -rf work .nextflow .nextflow.log*`, re-run without `-resume` |

## Fail-fast philosophy (§36)

Producing this table wrong (a dropped annotation, a miscounted clade) would be a
research-integrity failure, so every scenario above is a hard `sys.exit(1)`, never a
warning-and-continue. `validate_results` re-derives the checks from the output file
so a bug in 001 cannot hide behind shared code.
