<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 08
Human:   Eric Edsinger
Purpose: Describe the user inputs for the orthogroups_X_leonid_08july2026 workflow.
============================================================================ -->

# INPUT_user — orthogroups_X_leonid_08july2026

This workflow integrates *already-produced* upstream outputs (OrthoHMM orthogroups
+ pfam/go/panther annogroups + the species-tree clade species sets). It needs
**no user-supplied data files** — there is no manifest to edit.

Everything is read from sibling subprojects' `output_to_input/` directories, with
the paths set in `../START_HERE-user_config.yaml`:

- **Orthogroups** — `orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv`
  (headerless: `OG_ID` then tab-delimited member full GIGANTIC IDs).
- **Annogroups** (map + feature membership) — read from the `annogroups` subproject:
  `annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`
  (`2_ai-<source>-annogroup_map.tsv` + `2_ai-<source>-annogroup_membership.tsv`)
  for each source in `annotation_sources` (default `pfam`, `go`, `panther`).
- **Clade species sets** — `trees_species/output_to_input/BLOCK_permutations_and_features/Species_Clade_Species_Mappings/9_ai-clade_species_mappings-all_structures.tsv`

The only choices you make are in `../START_HERE-user_config.yaml`: `run_label`,
`species_set_name`, `annotation_sources`, `inputs.deconvolution_structures`
(default `structure_001`, `structure_003`, `structure_031`, `structure_032`), the
input paths, and execution settings.

See the workflow `ai/AI_GUIDE.md` for the full input contract and column layout.
