# AI_GUIDE — sequence_groups_X_species

**For AI assistants**: Read `../../AI_GUIDE-project.md` first for the GIGANTIC
overview, directory structure, and general patterns. This guide covers the
`sequence_groups_X_species` subproject; the workflow guide
(`BLOCK_sequence_groups/workflow-COPYME-sequence_groups/ai/AI_GUIDE-sequence_groups_workflow.md`)
covers running it.

| User needs… | Go to… |
|---|---|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| What this subproject is, concepts, troubleshooting | This file |
| Running the workflow | `BLOCK_sequence_groups/.../ai/AI_GUIDE-sequence_groups_workflow.md` |

## Purpose

This subproject **resolves a sequence-group set onto the species-tree clades**. It
is a generic, producer-agnostic species-tree *overlay* tool: given any group of
sequences with member species, it computes where those members fall on the tree —
composite clades, per-clade deconvolution, and a per-species sequence map.

It deliberately does **not** build groups. Producers do that (`annogroups`,
`orthogroups`, gene families). This subproject reads their output.

## Key concepts

- **Sequence group**: producer-agnostic grouping of protein sequences (orthogroup,
  annogroup, gene family). One run resolves ONE group set.
- **Standard membership** (the one interchange format):
  `SequenceGroup_ID  Sequence_Identifier  Genus_Species`. Script 001 (the adapter)
  produces it from a producer's native output; every downstream script reads only it.
- **The three overlays** (all from the standard membership + `trees_species` clades):
  - **deconvolution** (002): member sequence + species counts per clade (union over
    105 structures; per-structure layout optional via `emit_per_structure`).
  - **per-species map** (003): member sequence ids per species (wide form).
  - **composite clades** (004): four algorithms (exact / absent / core_urclade /
    core_early_clade) over member species. Engine lives in `utils_sequence_groups.py`;
    building-block clades are configured in `START_HERE-user_config.yaml` and curated
    in `INPUT_user/composite_clades_manifest.tsv`.
- **`group_set_label`**: namespaces a run's outputs (e.g. `species70_X_OrthoHMM`),
  so different group sets coexist under `output_to_input/<group_set_label>/`.
- **Rule 6**: a clade's species set is identical in every structure it appears in, so
  composite/per-species are structure-independent and the deconvolution union is
  computed once.

## Relationship to OCL (annotations_X_ocl / orthogroups_X_ocl)

OCL is a *different* operation (origin / conservation / loss inference). These
overlays answer "where on the tree are the members", which OCL does NOT compute.
Historically `annotations_X_ocl` embeds copies of the deconvolution + composite
(legacy); the long-term home is here. `orthogroups_X_ocl` stays a pure OCL engine —
its composite/deconvolution come from THIS subproject.

## Adding a producer

1. Add a reader branch in `001_ai-python-adapt_sequence_group_membership.py`'s
   `PRODUCER_READERS` (it must yield `(SequenceGroup_ID, Sequence_Identifier,
   Genus_Species)`; reuse `U.genus_species_from_full_id` to parse species from a
   GIGANTIC `-n_<phyloname>` id).
2. Point `inputs.producer_membership` + `producer` in the config at the new producer.
3. Nothing else changes.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `unknown producer '...'` (001) | `producer` not in `PRODUCER_READERS` | add a reader branch or fix the config value |
| `member ids had no parseable Genus_species` (001) | member ids lack `-n_<phyloname>` | confirm the producer emits GIGANTIC ids |
| `membership species are not tree tips` (002) | group set's species ≠ the species tree | confirm `species_set_name` matches the orthogroup/annogroup build and the clade mappings |
| `full-coverage clade count != Sequence/Species_Count` (002) | a member species mapped to the wrong clade | a real integrity failure — investigate the clade mappings |
| composite counts all zero | `composite_clades` clade_id_names wrong for the structure | check `reference_structure` + the `C###_Name` ids against the clade mappings |

## Key files

| File | What | User edits? |
|---|---|---|
| `BLOCK_sequence_groups/workflow-COPYME-sequence_groups/START_HERE-user_config.yaml` | group set, producer, inputs, composite clades | **yes** |
| `.../INPUT_user/composite_clades_manifest.tsv` | which composite clades to report | **yes** |
| `.../ai/scripts/001…004` | adapter + three overlays | rarely |
| `.../ai/scripts/utils_sequence_groups.py` | composite engine + clade/phyloname helpers | rarely |
