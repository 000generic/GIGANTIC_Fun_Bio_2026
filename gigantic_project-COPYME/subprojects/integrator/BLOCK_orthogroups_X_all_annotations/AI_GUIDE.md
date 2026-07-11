<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 10
Human:   Eric Edsinger
Purpose: AI guide for BLOCK_orthogroups_X_all_annotations — the join design,
         the output table, upstream dependencies, and fail-fast checks.
============================================================================ -->

# AI_GUIDE — BLOCK_orthogroups_X_all_annotations

**For AI assistants**: Read the subproject guide ([`../AI_GUIDE.md`](../AI_GUIDE.md))
first for integrator concepts and join models, and the project guide
([`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)) for the GIGANTIC overview. This
guide covers this BLOCK's specific design.

| User needs… | Go to… |
|-------------|--------|
| GIGANTIC overview, conventions | `../../../AI_GUIDE.md` |
| Integrator concepts, join models | `../AI_GUIDE.md` |
| This BLOCK's design + outputs | This file |
| Running the workflow | `workflow-COPYME-orthogroups_X_all_annotations/ai/AI_GUIDE.md` |

## Why this BLOCK exists

One analysis-ready table, **one row per OrthoHMM orthogroup**, that pairs each
orthogroup's members with, for **seven annotation types**, the non-redundant
species count, sequence count, identifiers, and names of members carrying that
annotation — plus a **per-clade / per-species member-count deconvolution** across
species-tree structures 001, 003, 031, 032.

It is a **structure-independent** integration (orthogroup membership and all
per-sequence annotations are invariant across structures), so there is no
per-structure fan-out — a handful of singleton processes.

## The join

The spine is the orthogroups table (OG → member sequence IDs). Each annotation
type is joined onto member sequences and aggregated to the orthogroup:

```
orthogroups (spine: OG -> member sequence IDs)
      │  full GIGANTIC sequence id
      ├──► Pfam / PANTHER  (BLOCK_interproscan_parsed per-species: Accession + Description)
      ├──► GO              (BLOCK_interproscan raw col13 GO terms + go_id_to_name)
      ├──► Gene_Families   (invert AGS FASTAs: family slug)
      ├──► Gene_Groups     (invert AGS FASTAs: gg<N> + HGNC name)
      ├──► Dark_Proteome   (per-sequence Status DARK/ANNOTATED + sources)
      │  (Genus_species, bare gene id)
      ├──► Hotspots        (invert per-region member gene lists -> Hotspot_IDs)
      │  member -n_phyloname -> Genus_species
      └──► clade species sets (trees_species, selected structures)
                           -> per-clade / per-species member-sequence counts
```

## Output table (1-output/1_ai-orthogroups_X_all_annotations.tsv)

Fixed columns: `Orthogroup_ID`, `Sequence_IDs` (comma), `Member_Sequence_Count`,
`Is_Singleton`. Then, for each type in order (Pfam, GO, PANTHER, Gene_Families,
Gene_Groups, Dark_Proteome, Hotspots): `<Type>_Species_Count`,
`<Type>_Sequence_Count`, `<Type>_Identifiers` (comma), `<Type>_Names` (` // `;
blank for Hotspots). Then the deconvolution columns, root → tips.

## Fail-fast policy (§36) — a silent artifact here is a research-integrity failure

- **STRICT (exit 1) for Pfam/GO/PANTHER**: these annotations are over the same
  species70 proteomes as the orthogroups, so an annotated sequence absent from the
  orthogroups is a silently dropped annotation — offenders are written to
  `1-output/1_ai-<source>-sequences_absent_from_orthogroups.tsv` and the build exits.
- **LOG-AND-SKIP (never silent) for Gene_Families/Gene_Groups/Dark_Proteome/Hotspots**:
  AGS files may legitimately include sequences outside species70; hotspots cover
  64/70 species. Non-orthogroup members are counted and reported in the run log.
- Also exit 1 on: missing inputs; Rule-6 clade violation; a member species not a
  tree tip; a full-coverage clade count ≠ member count; any name containing ` // `.

Script 002 re-checks the output table independently (row count, member/sequence
agreement, singleton flag, deconvolution completeness, per-type count ranges and
coverage consistency, identifier/name alignment).

## Upstream dependencies (see START_HERE-user_config.yaml for exact paths)

| Source | Used for |
|--------|----------|
| orthogroups `BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv` | spine + members (202,994 OGs) |
| annotations_hmms `BLOCK_interproscan_parsed/{pfam,panther}` | Pfam/PANTHER accessions + names |
| annotations_hmms `BLOCK_interproscan` + `reference_go/go_id_to_name.tsv` | GO ids + names |
| trees_gene_families `output_to_input` AGS FASTAs | gene family membership |
| trees_gene_groups `output_to_input` AGS + HGNC metadata | gene group membership |
| dark_proteomes classify RUN `3-output` | per-sequence DARK/ANNOTATED status |
| hotspots `output_to_input/BLOCK_identify_hotspots/hotspots` | hotspot regions (64/70 species) |
| trees_species clade→species mappings | deconvolution |

## Pipeline

| Script | Does |
|--------|------|
| `001_ai-python-build_annotations_table.py` | builds the whole table (7 types + deconvolution) → 1-output |
| `002_ai-python-validate_results.py` | independent fail-fast cross-checks → 2-output |
| `003_ai-python-write_run_log.py` | §45 run log → ai/logs |

## Conda environment

`aiG-integrator-orthogroups_X_all_annotations` (python + pyyaml + nextflow;
created on-demand by `RUN-workflow.sh`).

## Notes / caveats

- Includes **all** orthogroups, singletons included; `Is_Singleton` +
  `Member_Sequence_Count` make them easy to filter.
- Coverage caveats: dark proteome read from a RUN dir (not output_to_input);
  hotspots 64/70 species; gene-family slug = id = name; hotspot names blank.
