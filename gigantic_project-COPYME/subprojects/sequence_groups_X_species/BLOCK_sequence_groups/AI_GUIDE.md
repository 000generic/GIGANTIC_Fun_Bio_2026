# AI_GUIDE — BLOCK_sequence_groups (sequence_groups_X_species)

<!-- ============================================================================
AI:      Claude Code | Opus 4.8 | 2026 July 02
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../AI_GUIDE-sequence_groups_X_species.md` first for the
subproject overview and concepts. This guide covers the one block that runs the
resolver workflow.

## Where this fits

- **UP**: subproject guide [`../AI_GUIDE-sequence_groups_X_species.md`](../AI_GUIDE-sequence_groups_X_species.md); subproject [`../README.md`](../README.md); project [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- **DOWN**: workflow template [`workflow-COPYME-sequence_groups/`](workflow-COPYME-sequence_groups/) and its workflow guide [`workflow-COPYME-sequence_groups/ai/AI_GUIDE-sequence_groups_workflow.md`](workflow-COPYME-sequence_groups/ai/AI_GUIDE-sequence_groups_workflow.md)
- **IN**: producer group sets from `../../{orthogroups,annogroups,trees_gene_families,trees_gene_groups}/output_to_input/`; species-tree clades from `../../trees_species/output_to_input/`
- **OUT**: `../output_to_input/<producer>/<group_set_label>/` (downstream) and `../upload_to_server/` (data server), both via the interface layer (§2, §38)

## What this block does

`sequence_groups_X_species` has **one block**: it resolves a sequence-group set onto
the species-tree clades. A single producer-agnostic NextFlow workflow reads one group
set (via a Script 001 producer adapter) and overlays its membership onto the species
tree three ways:

| Script | Output | What |
|--------|--------|------|
| 001 adapt_sequence_group_membership | 1-output | producer → standard membership (`SequenceGroup_ID, Sequence_Identifier, Genus_Species`) |
| 002 species_tree_deconvolution | 2-output | member sequence + species counts per clade (union; scope via `deconvolution_structures`, default all 105) |
| 003 per_species_sequence_map | 3-output | member sequence identifiers per species |
| 004 composite_clades | 4-output | four algorithms + 242 detail tables (with 10 integrator catalog annotation types × 4 columns when `annotation_index` is set) |
| 006 build_annotation_index | annotation_index/ | cross-producer sequence → annotation index (runs once; gates Script 004 detail tables) |

An optional per-group `group_attributes` table is carried, opaque, onto the per-group
rows (annogroups supplies its `annogroup_map.tsv`, adding Source / Annogroup_Type /
Annotation_Definitions / …). See the workflow guide for the mechanism.

## Runs

Each run resolves the producers listed in `START_HERE-user_config.yaml` (currently
seven group sets: orthogroups; annogroups pfam / go / panther; gene_families;
gene_groups hugo_hgnc + snap_family). Copy `workflow-COPYME-sequence_groups/` to a new
`workflow-RUN_N-sequence_groups/`, edit config if needed, then `bash RUN-workflow.sh`.

Leonid (2026-07) updates in COPYME: `deconvolution_structures` (001/003/031/032 only),
`annotation_index` + Script 006 (Pfam, GO, PANTHER, Annogroups_*, Gene_Families,
Gene_Groups, Dark_Proteome, Hotspots — four columns per type on all 242 composite-clades
detail tables per producer). **RUN_4** is the first run from this template.
