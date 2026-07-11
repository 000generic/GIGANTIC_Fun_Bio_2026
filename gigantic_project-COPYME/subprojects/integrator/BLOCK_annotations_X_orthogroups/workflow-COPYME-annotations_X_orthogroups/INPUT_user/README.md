<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 09
Human:   Eric Edsinger
Purpose: Describe the user inputs staged for the annotations_X_orthogroups
         integration workflow.
============================================================================ -->

# INPUT_user — annotations_X_orthogroups

This workflow integrates *already-produced* upstream outputs (pfam annogroups +
orthogroups + the Bilateria clade species set). It needs **no user-supplied
data files** — there is no manifest to edit.

Everything is read from sibling subprojects' `output_to_input/` directories,
with the paths set in `../START_HERE-user_config.yaml`:

- **Annogroups** (map + membership) — read directly from the `annogroups` subproject:
  `annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`
  (`2_ai-<source>-annogroup_map.tsv` + `2_ai-<source>-annogroup_membership.tsv`)
- **Orthogroups** — `orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv`
- **Bilateria species set** — `trees_species/output_to_input/BLOCK_permutations_and_features/Species_Clade_Species_Mappings/`

The only choices you make are in `../START_HERE-user_config.yaml`:
`run_label`, `annogroup_types` (default `feature`, `combination`, `architecture`,
`absent` — `absent` is the useful pfam-dark state row here), the input paths,
the `bilateria_clade_id_name` (default `C103_Bilateria`), and execution settings.

See the workflow `ai/AI_GUIDE.md` for the full input contract.
