<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: Subproject-level AI guide for integrator — concepts, join model,
         conventions, and pointers into the first BLOCK.
Scope:   The integrator subproject (all BLOCKs).
============================================================================ -->

# AI_GUIDE — integrator

**For AI Assistants**: Read `../../AI_GUIDE.md` first (GIGANTIC overview) and
`../../ai/ai_FYIs/gigantic_conventions.md` for conventions. This guide covers
the `integrator` subproject: a downstream subproject that combines other
subprojects' outputs into integrated tables.

## Where this fits

- Parent project landing page: [`../../README.md`](../../README.md)
- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Subproject README: [`README.md`](README.md)
- BLOCKs:
  - [`BLOCK_orthogroups_ocl_X_features/AI_GUIDE.md`](BLOCK_orthogroups_ocl_X_features/AI_GUIDE.md) — OCL orthogroups × dark/hotspot/secretome (per structure)
  - [`BLOCK_annotations_X_orthogroups/AI_GUIDE.md`](BLOCK_annotations_X_orthogroups/AI_GUIDE.md) — pfam annogroups × orthogroups, non-bilaterian-metazoan focus (structure-independent; reads annogroup map + membership directly from the `annogroups` subproject)
  - [`BLOCK_species_X_all_annotations/AI_GUIDE.md`](BLOCK_species_X_all_annotations/AI_GUIDE.md) — per-species proteome (spine = one row per protein) × every per-gene annotation + per-structure orthogroup/annogroup OCL columns
  - [`BLOCK_ambiguous_nodes_X_annogroups/AI_GUIDE.md`](BLOCK_ambiguous_nodes_X_annogroups/AI_GUIDE.md) — annogroups species-tree deconvolution collapsed to ONLY the ambiguous nodes (clades present in some but not all structures), in one/some/all structure scopes, per source (pfam, go, panther); pure column projection of the annogroups deconvolution (`ambiguous_nodes_X_*` series, first member)
  - [`BLOCK_orthogroups_X_leonid_08july2026/AI_GUIDE.md`](BLOCK_orthogroups_X_leonid_08july2026/AI_GUIDE.md) — one row per OrthoHMM orthogroup × non-redundant Pfam/GO/PANTHER annotations (from annogroup feature membership) × species-tree deconvolution (per-clade/per-species member-sequence counts across structures 001, 003, 031, 032); a Leonid request (structure-independent)
- Reads FROM (per `BLOCK_orthogroups_ocl_X_features`):
  - `../ocl_phylogenetic_structures/output_to_input/BLOCK_orthogroups_X_ocl/<run_label>/` (OCL orthogroup summary + path_states, per structure)
  - `../dark_proteomes/output_to_input/BLOCK_classify_dark_proteome/dark_proteome/`
  - `../hotspots/output_to_input/BLOCK_identify_hotspots/hotspots/`
  - `../secretome/output_to_input/STEP_2-filter_secretome/` (+ `STEP_1-build_evidence_table/`)
- Outputs TO: `output_to_input/BLOCK_orthogroups_ocl_X_features/<run_label>/`
- Downstream consumers: comparative analyses, `upload_to_server/` (browsable by Eric + Leonid Moroz)

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| Conventions (§1–§61) | `../../ai/ai_FYIs/gigantic_conventions.md` |
| Subproject overview | `README.md` |
| Subproject concepts (this file) | This file |
| OCL-features BLOCK concepts | `BLOCK_orthogroups_ocl_X_features/AI_GUIDE.md` |
| annogroups×orthogroups BLOCK concepts | `BLOCK_annotations_X_orthogroups/AI_GUIDE.md` |
| per-species all-annotations BLOCK concepts | `BLOCK_species_X_all_annotations/AI_GUIDE.md` |
| ambiguous-nodes × annogroups BLOCK concepts | `BLOCK_ambiguous_nodes_X_annogroups/AI_GUIDE.md` |
| orthogroups × Leonid table BLOCK concepts | `BLOCK_orthogroups_X_leonid_08july2026/AI_GUIDE.md` |
| Running a BLOCK | `BLOCK_<name>/workflow-COPYME-*/ai/AI_GUIDE.md` |

## What integrator does

`integrator` is a **BLOCK-type** subproject (§41): each BLOCK independently
integrates a specific combination of upstream subproject outputs into combined
tables. It produces no new primary biology — it joins existing per-gene and
per-orthogroup results so cross-cutting questions can be asked in one table.

## The integration model (first BLOCK)

The OCL orthogroup analysis is the **spine**; per-gene features are layered onto
each orthogroup through its member sequence IDs.

- **Spine**: `BLOCK_orthogroups_X_ocl` gives, per species-tree structure, one
  row per orthogroup with Origin block/state, Conservation/Loss/Continued-Absence
  event counts, and the member `Sequence_IDs`.
- **Bridge**: each orthogroup's `Sequence_IDs` (full GIGANTIC IDs) are looked up
  in the three feature sources.

### Join keys (verified against real data)

| Feature source | Key against the OCL member ID | Notes |
|---|---|---|
| dark_proteome | full GIGANTIC ID (exact) | `Full_GIGANTIC_Gene_ID` == OCL `Sequence_IDs` member |
| secretome | full GIGANTIC ID (exact) | `Protein_Identifier` == OCL member; T1 = 1 protein/gene |
| hotspots | `( Genus_species, source_gene_field )` | hotspot member IDs are the bare gene field, unique only within a species; derive `g_` field + phyloname from the OCL member ID |

### Structure-invariance (efficiency)

Orthogroup membership does NOT change with tree structure — only the OCL
inference does. So the per-gene feature lookup is built **once**
(Script 001 → `OUTPUT_pipeline/_shared/`) and joined to all per-structure OCL
summaries.

### Species-set policy: union + availability flags

Feature sources cover different species (e.g. hotspots needs user-prepared gene
coordinates, so fewer species). integrator includes every species present in
any source and marks per-axis availability — a member from a species missing a
source is recorded `NA`, never silently dropped (per `AI_BEHAVIOR.md`
zero-tolerance for silent artifacts).

## Upstream dependency: OCL path_states exposure

The block-state table (Table 2) needs the OCL per-block states, which live in
`4_ai-path_states-per_orthogroup_per_species.tsv`. As of 2026-06-04 the
`orthogroups_X_ocl` workflow exposes this file in its `output_to_input/`
alongside the orthogroup summary (its `RUN-workflow.sh` symlink step was
extended). If a future OCL run does not expose path_states, Table 2 fails fast
with a clear message.

> **Repair note (2026-06-04)**: when wiring this up, all 210
> `orthogroups_X_ocl/output_to_input/` symlinks were found broken — they pointed
> at the pre-rename `BLOCK_ocl_analysis` target from before the 2026-05-29 OCL
> reorg. They were regenerated to the correct `BLOCK_orthogroups_X_ocl` target
> (no pipeline re-run; the `OUTPUT_pipeline` files already existed in
> `workflow-RUN_1`). Other consumers of that `output_to_input/` had been
> silently receiving dead links since the rename.

## Conda env

`aiG-integrator-orthogroups_ocl_X_features` (per §28; single-BLOCK short form
would be `aiG-integrator` per §53, but the explicit per-BLOCK form is used so
future BLOCKs each get their own env). Auto-created on first
`RUN-workflow.sh`.

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `OCL summary not found for structure_NNN` | `ocl_orthogroups_dir`/run_label wrong, or that structure not produced | Verify `ls ../ocl_phylogenetic_structures/output_to_input/BLOCK_orthogroups_X_ocl/<run_label>/structure_NNN/` |
| `OCL path_states not found` | OCL run didn't expose path_states | Re-run OCL `RUN-workflow.sh` (now exposes it) or check the symlink |
| Broken OCL input links | OCL `output_to_input` symlinks stale (pre-rename target) | Regenerate them (see repair note above) |
| All-`NA` features for many species | Species-set mismatch with feature subprojects | Check `_shared/1-output/1_ai-feature_availability_summary.tsv` |
| Memory pressure in per-structure tasks | Large gene lookup loaded per task | Bump `memory_gb` in `START_HERE-user_config.yaml` (drives SLURM + local-executor memory) |

## Questions to ask the user

| Situation | Ask |
|-----------|-----|
| First run | "Which OCL run_label / species set should integrator read? (default species70_X_OrthoHMM)" |
| Structure subset | "Integrate all 105 structures, or a subset in the structure manifest?" |
| Species mismatch | "Some species lack hotspots/secretome — proceed with union + availability flags (default)?" |

---

## Session hygiene (per §61)

- **Root every chat session at the named `gigantic_project-*/` directory** —
  not at `GIGANTIC/`, not at `subprojects/<X>/`, not at a workflow dir.
- **One chat session per subproject**; continue across compactions (lossless
  per §9) until muddled, then start fresh at the same root.
- **Keep a separate "small questions" session** for one-off questions.

See `../../ai/ai_FYIs/gigantic_conventions.md` §61 for the full rationale.
