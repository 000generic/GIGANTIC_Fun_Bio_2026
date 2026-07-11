# AI_GUIDE — resolve_groups workflow

**For AI assistants**: Read the subproject guide
(`../../../AI_GUIDE-sequence_groups_X_species.md`) first for concepts. This guide
focuses on RUNNING the workflow.

## What it does (one group set)

```
006 build_annotation_index (once) -> annotation_index/6_ai-sequence_annotation_index.tsv
001 adapt_membership   producer native output -> 1-output/1_ai-<label>-sequence_group_membership.tsv
        │  (the standard membership; everything below reads only this)
        ├─► 002 species_tree_deconvolution -> 2-output/  (sequence + species counts per clade; union tables)
        ├─► 003 per_species_sequence_map   -> 3-output/  (member sequence ids per species)
        └─► 004 composite_clades           -> 4-output/  (per-group + summary + 242 detail tables w/ annotations)
005 write_run_log -> ai/logs/
```
006 runs once and gates 004 (annotation columns on detail tables). 002/003/004 run in parallel after 001.

## Run

```bash
cp -r workflow-COPYME-resolve_groups workflow-RUN_N-resolve_groups
cd workflow-RUN_N-resolve_groups
# edit START_HERE-user_config.yaml: group_set_label, producer, inputs, composite_clades
export TMPDIR=/tmp        # avoids a stale TMPDIR on compute nodes
bash RUN-workflow.sh      # local, or self-submits to SLURM if execution_mode: slurm
```

Outputs land in `OUTPUT_pipeline/{1,2,3,4}-output/`; downstream symlinks in
`../../output_to_input/<group_set_label>/`.

## Config knobs (START_HERE-user_config.yaml)

| Key | Meaning |
|---|---|
| `group_set_label` | namespaces outputs, e.g. `species70_X_OrthoHMM` |
| `producer` | which adapter Script 001 uses (`orthogroups`, …) |
| `inputs.producer_membership` | the producer's native membership file |
| `inputs.clade_species_mappings` | trees_species clade→species (all structures) |
| `inputs.composite_clades_manifest` | `INPUT_user/composite_clades_manifest.tsv` |
| `composite_clades` | building-block clade groups + scope |
| `emit_per_structure` | also write the per-structure deconvolution re-layout (default false; the union holds all clades) |
| `deconvolution_structures` | restrict Script 002 clade columns to these structures only (default `[]` = all 105; Leonid uses 001/003/031/032) |
| `annotation_index` | paths for Script 006 (PFAM/PANTHER/GO annogroups + gene_families/gene_groups dirs); required for annotated detail tables |
| `execution_mode` | `local` or `slurm` (then set `slurm_account`/`slurm_qos`) |

## Common errors

| Error | Fix |
|---|---|
| `unknown producer '...'` | add a reader branch in Script 001 or fix `producer` |
| `membership species are not tree tips` | `species_set_name` / clade mappings don't match the group set's species |
| `full-coverage clade count != …` | real integrity failure — investigate clade mappings (do NOT suppress) |
| composite counts all zero | `composite_clades` clade ids wrong for `reference_structure` |
| NextFlow uses stale scripts | clear `work/ .nextflow/ .nextflow.log*` and re-run without `-resume` |

## Notes

- The workflow is single-task per script (not per-structure / per-source); it
  resolves ONE group set per run. Run it again with a different `group_set_label`
  for another set (e.g. a different orthology method).
- Per gigantic conventions: `export TMPDIR=/tmp` before `bash RUN-workflow.sh` on SLURM.
