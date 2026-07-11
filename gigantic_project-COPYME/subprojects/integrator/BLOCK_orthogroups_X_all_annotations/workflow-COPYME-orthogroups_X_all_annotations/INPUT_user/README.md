<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 10
Human:   Eric Edsinger
Purpose: Describe the user inputs for the orthogroups_X_all_annotations workflow.
============================================================================ -->

# INPUT_user — orthogroups_X_all_annotations

This workflow integrates *already-produced* upstream outputs (OrthoHMM orthogroups
plus seven annotation types). It needs **no user-supplied data files** — there is
no manifest to edit.

Everything is read from sibling subprojects, with paths set in
`../START_HERE-user_config.yaml`:

- **Orthogroups** (spine) — `orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv`
- **Pfam / PANTHER** — `annotations_hmms/output_to_input/BLOCK_interproscan_parsed/{pfam,panther}/`
- **GO** — `annotations_hmms/output_to_input/BLOCK_interproscan/` + `.../GO_reference/go_id_to_name.tsv`
- **Gene families** — `trees_gene_families/output_to_input/<family>/**/16_ai-ags-*.aa`
- **Gene groups** — `trees_gene_groups/output_to_input/gene_groups-*/**/16_ai-ags-*.aa` + HGNC metadata
- **Dark proteome** — `dark_proteomes/.../classify_dark_proteome-species70/OUTPUT_pipeline/3-output/`
- **Hotspots** — `hotspots/output_to_input/BLOCK_identify_hotspots/hotspots/` (64/70 species)
- **Clade species sets** — `trees_species/.../9_ai-clade_species_mappings-all_structures.tsv`

The only choices you make are in `../START_HERE-user_config.yaml`: `run_label`,
`species_set_name`, `hmm_annotation_sources`, `inputs.deconvolution_structures`
(default `structure_001`, `structure_003`, `structure_031`, `structure_032`), the
input paths, and execution settings.

See the workflow `ai/AI_GUIDE.md` for the full input contract and column layout.
