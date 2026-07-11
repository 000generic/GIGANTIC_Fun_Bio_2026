<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: BLOCK-level AI guide for BLOCK_species_X_all_annotations — the spine,
         the per-source join keys, the output schema, and the per-script pipeline.
Scope:   BLOCK_species_X_all_annotations.
============================================================================ -->

# AI Guide: BLOCK_species_X_all_annotations

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — integrator overview
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-species_X_all_annotations/`](workflow-COPYME-species_X_all_annotations/)
- This BLOCK's workflow guide: [`workflow-COPYME-species_X_all_annotations/ai/AI_GUIDE.md`](workflow-COPYME-species_X_all_annotations/ai/AI_GUIDE.md)
- Outputs TO: `../output_to_input/BLOCK_species_X_all_annotations/<run_label>/`
- Conda env: `aiG-integrator-species_X_all_annotations`

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../AI_GUIDE.md` |
| Conventions | `../../../ai/ai_FYIs/gigantic_conventions.md` |
| integrator concepts + join model | `../AI_GUIDE.md` |
| BLOCK concepts (this file) | This file |
| Running the workflow | `workflow-COPYME-species_X_all_annotations/ai/AI_GUIDE.md` |

## What this BLOCK does

Builds a **per-species proteome annotation table**: one row per protein
sequence, with every per-gene feature GIGANTIC produces joined onto it. Unlike
the sibling BLOCKs (whose spine is the orthogroup), the spine here is the
**proteome** — the genomesDB STEP_4 per-species sequence table (sequence id +
amino acid sequence). It produces no new biology; it gathers existing per-gene
results into one wide table per species so a protein can be inspected across all
annotation axes at once.

## The spine and the join keys (verified against real data)

Spine: `genomesDB STEP_4` `<phyloname>-T1-proteome-sequence_table.tsv`
(columns `Phyloname`, `Gigantic_Protein_Identifier`, `Sequence_Length`,
`Protein_Sequence`). The `Gigantic_Protein_Identifier` is the per-protein join
key (`g_<gene>-t_<rna>-p_<protein>-n_<phyloname>`).

| Source | output_to_input read path | Join key | Coverage |
|---|---|---|---|
| gene_sizes | `gene_sizes/.../gene_vs_protein/species64_gigantic_gene_metrics/` | **bare `g_` field + species** | 64/70 |
| hotspots | `hotspots/BLOCK_identify_hotspots/hotspots/` | **bare `g_` field + species** (hotspot→members inverted) | 64/70 |
| one_direction_homologs (nr) | `one_direction_homologs/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/` | full GIGANTIC ID | 70 |
| annotations_hmms | `annotations_hmms/BLOCK_build_annotation_database/annotation_databases/database_{pfam,go,panther}/` | full GIGANTIC ID (multi-row→list) | 70 |
| annogroups | `annogroups/BLOCK_build_annogroups/<species_set>/{pfam,go,panther}/2_ai-<source>-annogroup_membership.tsv` | full GIGANTIC ID (direct) | 70 |
| orthogroups | `orthogroups/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv` | full GIGANTIC ID (OG→members inverted) | 70 |
| secretome | `secretome/STEP_1-build_evidence_table/` | full GIGANTIC ID | 70 |
| trees_gene_groups AGS | `trees_gene_groups/.../gene_groups-hugo_hgnc/STEP_1.../16_ai-ags-*.aa` | full GIGANTIC ID in FASTA headers | 2,060 groups |
| trees_gene_families AGS | `trees_gene_families/output_to_input/<family>/STEP_1.../16_ai-ags-*.aa` | full GIGANTIC ID in FASTA headers | 76 families |
| dark_proteomes | `dark_proteomes/BLOCK_classify_dark_proteome/dark_proteome/` | full GIGANTIC ID | 70 |
| **orthogroup OCL** (per structure) | `ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/<run>/<structure>/` | sequence → Orthogroup_ID → OCL | per structure |
| **annogroup OCL** (per structure) | `ocl_phylogenetic_structures/BLOCK_annotations_X_ocl/<run>/<structure>/` | sequence → pfam annogroup → OCL | **pfam only**, per structure |

## Two phases (structure-invariant vs structure-dependent)

Only the OCL inference depends on the species-tree structure; everything else is
invariant. So:

- **Phase 1 (Script 001, once)** → `1-output/_shared/<phyloname>-proteome_annotations-base.tsv`.
  Spine + all invariant columns.
- **Phase 2 (Script 002, per structure)** → `2-output/<structure>/<phyloname>-proteome_all_annotations.tsv`.
  The base columns **plus** that structure's orthogroup-OCL and annogroup-OCL
  columns (full wide table per structure). The structure set is user-chosen
  (`structures: all` or a list).

## Coverage & NA policy (zero silent artifacts, per `AI_BEHAVIOR.md`)

Every protein in the spine becomes a row. Where a source does not cover a
species (gene_sizes/hotspots = 64/70) or a protein, the cell is `NA` and a
per-axis `*_Available` flag records the gap — never a silent drop. annogroup
**OCL** is currently pfam-only (`species70_pfam`); the go/panther annogroup
membership IS present (so the membership columns are populated) but their OCL is
not run, so go/panther annogroup-OCL is out of scope and pfam annogroup-OCL is
the only OCL annogroup axis.

## Delimiters

- Comma (`,`) — simple ID/count lists with no internal commas (GO terms,
  annogroup IDs, orthogroup-OCL event counts, AGS names).
- Semicolon (`;`) — composite entries whose text may contain commas (nr hit
  headers, Pfam/PANTHER `accession description` entries, annogroup-OCL
  phylogenetic paths). Matches the annogroups subproject's `;`-for-substructure
  precedent.

## Output schema

### Base table (`1-output/_shared/`, invariant)
`Sequence_Identifier`, `Phyloname`, `Genus_Species`, `Sequence_Length`,
`Protein_Sequence`; `Gene_Size_BP`/`CDS_Size_BP`/`Protein_Size_AA` (+
`Gene_Sizes_Available`); `In_Hotspot`/`Hotspot_IDs`/`Hotspot_Paralog_Counts` (+
`Hotspots_Available`); `Top_3_NR_Hits`; `Pfam_Annotations`, `InterPro_GO_Terms`,
`PANTHER_GO_Terms`, `PANTHER_Families` (+ `Annotations_HMMs_Available`);
`Annogroups_Pfam`, `Annogroups_GO`, `Annogroups_PANTHER`; `Orthogroup_ID`,
`Orthogroup_Member_Protein_Count`, `Orthogroup_Species_Count`;
`Secretome_SignalP_Call`/`_Probability`/`Secretome_DeepLoc_Localization` (+
`Secretome_Available`); `Gene_Group_AGS_Memberships`,
`Gene_Family_AGS_Memberships`; `Dark_Status` (+ `Dark_Proteome_Available`).

### Per-structure wide table (`2-output/<structure>/`)
All base columns, then: `Structure_ID`;
`Orthogroup_OCL_Origin_Phylogenetic_Block`/`_Block_State`/`_Path`,
`Orthogroup_OCL_Conservation_Events`/`_Loss_Events`/`_Continued_Absence_Events`;
`Annogroup_Pfam_OCL_IDs` + parallel
`Annogroup_Pfam_OCL_Origin_Phylogenetic_Blocks`/`_Paths`/
`_Conservation_Events`/`_Loss_Events`/`_Continued_Absence_Events` (all-types
annogroups, parallel lists).

## Pipeline (5 scripts + utils)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 000 | `resolve_structures.py` | `resolve_structures` | Resolve `structures` (all \| list) → `structures.txt`; fail-fast verify each structure's OCL summaries exist |
| 001 | `build_invariant_base.py` | `build_invariant_base` | Phase 1 — join every invariant per-gene feature onto the spine → `1-output/_shared/` |
| 002 | `build_per_structure_tables.py` | `build_per_structure_tables` | Phase 2 (fan-out) — append a structure's orthogroup + annogroup OCL columns → `2-output/<structure>/` |
| 003 | `validate_results.py` | `validate_results` | Base header/uniqueness/species-containment/availability-flag consistency + per-structure row-count/OCL-referential checks; fail-fast (§36) |
| 004 | `write_run_log.py` | `write_run_log` | Timestamped run log (§45) |
| — | `utils_species_X_all_annotations.py` | — | Shared helpers (config, GIGANTIC-ID parsing, header indexing, nr-hit formatting, `DELIM`/`SUBDELIM`/`NA`) |

## Research-integrity guards (Script 002 / 003)

- A non-NA `Orthogroup_ID` whose orthogroup is absent from the structure's OCL
  summary → **fail-fast** (membership and the OCL run are out of sync; never a
  silent NA).
- An annogroup ID with no OCL row (OCL coverage lagging membership) → recorded
  `NA` in its parallel slot **and counted/printed** (visible, not hidden).
- Validation B3 verifies every row's `Sequence_Identifier` resolves to its own
  species (no cross-species join contamination); B4 verifies that when a source
  flag is `no`, that source's columns are all `NA` (no leakage).

## See also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — integrator subproject overview
- [`workflow-COPYME-species_X_all_annotations/ai/AI_GUIDE.md`](workflow-COPYME-species_X_all_annotations/ai/AI_GUIDE.md) — workflow execution detail
