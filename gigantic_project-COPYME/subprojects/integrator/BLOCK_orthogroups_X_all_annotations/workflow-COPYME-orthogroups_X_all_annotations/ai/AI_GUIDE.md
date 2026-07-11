<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 10
Human:   Eric Edsinger
Purpose: Level-3 workflow guide — running orthogroups_X_all_annotations.
============================================================================ -->

# AI_GUIDE — orthogroups_X_all_annotations (workflow)

**For AI assistants**: Read the BLOCK guide ([`../../AI_GUIDE.md`](../../AI_GUIDE.md))
first for the join design and output schema. This guide focuses on execution.

## Pipeline (main.nf)

```
build_annotations_table (001) ──► validate_results (002) ──► write_run_log (003)
```

All three carry `label 'local'`; with `parallelism_mode: local` they run inside the
driver allocation. Paths are resolved by each script from
`../START_HERE-user_config.yaml` (relative to the workflow dir; §5).

## Scripts (ai/scripts/)

| Script | Runs | Reads | Writes |
|--------|------|-------|--------|
| `001_ai-python-build_annotations_table.py` | once | orthogroups spine; pfam/panther/GO per-sequence; gene family/group AGS; dark proteome; hotspots; clade species map | `1-output/1_ai-orthogroups_X_all_annotations.tsv` |
| `002_ai-python-validate_results.py` | once | the 001 table + input orthogroup count | `2-output/2_ai-validation_report.txt` |
| `003_ai-python-write_run_log.py` | once | — | `ai/logs/run_*.log` |
| `utils_orthogroups_X_all_annotations.py` | — | shared helpers (config, path resolution, phyloname→Genus_species, header index, delimiters) | — |

## Config knobs (START_HERE-user_config.yaml)

- `run_label`, `species_set_name`
- `hmm_annotation_sources` — ordered HMM sources (default pfam, go, panther)
- `inputs.deconvolution_structures` — species-tree structures (default 001,003,031,032)
- `inputs.*` — the seven annotation-source paths + `orthogroups_file` + `clade_species_mappings`
- `cpus` / `memory_gb` / `time_hours` — SLURM job + local executor sizing
- `execution_mode` (local | slurm), `slurm_account`, `slurm_qos`,
  `parallelism_mode` (local | slurm), `resume`

## How the columns are built (Script 001)

1. Load the clade map filtered to the selected structures → non-redundant clade
   union (root→tips), per-clade species sets, tips, full-coverage clades. Rule-6 validated.
2. Load orthogroups → ordered `(OG, members)` list + `sequence → OG` map.
3. For each of the seven types, aggregate per OG: identifier set, {id: name},
   annotated-sequence set (→ Sequence_Count), annotated-species set (→ Species_Count).
   Pfam/GO/PANTHER are STRICT (exit on non-orthogroup sequence); gene families/groups,
   dark, and hotspots LOG-AND-SKIP non-orthogroup members.
4. Write one row per OG: fixed columns, four columns per type, then per-clade
   member-sequence counts (member counted in every ancestor clade).

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CRITICAL ERROR: required input not found` | upstream not populated, or path wrong | check the `inputs.*` paths |
| `... selected structure(s) not found` | a `deconvolution_structures` id not in the clade map | fix the ids (`structure_001` form) |
| `... member ... is not a tree tip` | orthogroups and clade map are different species sets | align `species_set_name` / clade map to the orthogroups run |
| `... annotated sequence(s) absent from the orthogroups` (Pfam/GO/PANTHER) | annotations and orthogroups built on different proteomes/IDs | check both use the same species set; offenders in `1-output/1_ai-<source>-sequences_absent_from_orthogroups.tsv` |
| high `non-orthogroup member(s) skipped` for AGS/dark/hotspots | expected if AGS include out-of-set sequences; investigate if unexpectedly large | inspect the run log counts |
| `... name ... contains ' // '` | a name contains the NAME delimiter | investigate; change `NAME_DELIM` in `utils`; never silently strip |
| out-of-memory | large per-sequence aggregates | raise `memory_gb` (default 128) |
| stale results after editing scripts | NextFlow cache | `rm -rf work .nextflow .nextflow.log*`, re-run without `-resume` |

## Fail-fast philosophy (§36)

Producing this table wrong (a dropped annotation, a miscounted clade) would be a
research-integrity failure. Pfam/GO/PANTHER coverage gaps are hard `sys.exit(1)`;
AGS/dark/hotspot non-orthogroup members are counted and reported (never silently
dropped). `validate_results` re-derives checks from the output file so a bug in 001
cannot hide behind shared code.
