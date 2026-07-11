<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 08
Human:   Eric Edsinger
Purpose: AI guide for BLOCK_orthogroups_X_leonid_08july2026 — the join design,
         the output table, upstream dependencies, and fail-fast checks.
============================================================================ -->

# AI_GUIDE — BLOCK_orthogroups_X_leonid_08july2026

**For AI assistants**: Read the subproject guide ([`../AI_GUIDE.md`](../AI_GUIDE.md))
first for the integrator concepts and join models, and the project guide
([`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)) for the GIGANTIC overview. This
guide covers this BLOCK's specific design.

| User needs… | Go to… |
|-------------|--------|
| GIGANTIC overview, conventions | `../../../AI_GUIDE.md` |
| Integrator concepts, join models | `../AI_GUIDE.md` |
| This BLOCK's design + outputs | This file |
| Running the workflow | `workflow-COPYME-orthogroups_X_leonid_08july2026/ai/AI_GUIDE.md` |

## Why this BLOCK exists

A direct request from Leonid (2026-07-08): one analysis-ready table, **one row per
OrthoHMM orthogroup**, that pairs each orthogroup's members and their non-redundant
Pfam/GO/PANTHER annotations with a **per-clade / per-species member-count
deconvolution** across a chosen set of species-tree structures (001, 003, 031, 032).

It is a **structure-independent** integration (orthogroup membership, annogroup
membership, and per-clade species sets are all invariant across structures), so
there is no per-structure fan-out — a handful of singleton processes.

## The join

Three upstream sources, joined on the **full GIGANTIC sequence identifier** and on
**Genus_species** (parsed from each member's `-n_<phyloname>`):

```
orthogroups (spine: OG -> member sequence IDs)
      │  member sequence ID
      ├──────────────► annogroups FEATURE membership (pfam/go/panther)
      │                    -> per-orthogroup non-redundant accessions (+ names from map)
      │  member -n_phyloname -> Genus_species
      └──────────────► clade species sets (trees_species, selected structures)
                           -> per-clade / per-species member-sequence counts
```

## Output table (1-output/1_ai-orthogroups_X_leonid.tsv)

Fixed columns: `Orthogroup_ID`, `Sequence_IDs` (comma), `Member_Sequence_Count`,
`Is_Singleton`. Then per source (in `annotation_sources` order): `<Display>_Accessions`
(comma) and `<Display>_Names` (delimited by ` // `; §34 deviation — names may contain
commas, semicolons, and pipes, so a multi-character separator with zero collisions is
used; the build fails fast if any name contains ` // `). Then the deconvolution
columns: one per non-redundant clade/species across the selected structures, ordered
root → tips.

Display labels: `pfam→Pfam`, `go→GO`, `panther→PANTHER`.

## Deconvolution (the annogroups Script 004 pattern, restricted to 4 structures)

- A `clade_id_name` identifies a fixed topologically-structured species set
  (GIGANTIC Rule 6). Its member-sequence count for an orthogroup is therefore
  identical in every selected structure it appears in → the union of clades is
  **non-redundant**; each column is computed once.
- Each clade column's header records which of the selected structures the clade
  appears in (`present in structures 001,031 of 4 selected`).
- A member is counted in **every** ancestor clade of its species, so a
  full-coverage (root) clade totals the orthogroup's `Member_Sequence_Count`, and
  the species (tip) columns sum to it — both are validated.

## Upstream dependencies (all via output_to_input, §2)

| Source | Path (relative to the workflow dir) | Used for |
|--------|--------------------------------------|----------|
| orthogroups | `../../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv` | spine + members |
| annogroups | `../../../annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/2_ai-<source>-annogroup_{map,membership}.tsv` | Pfam/GO/PANTHER accessions + names |
| trees_species | `../../../trees_species/output_to_input/BLOCK_permutations_and_features/Species_Clade_Species_Mappings/9_ai-clade_species_mappings-all_structures.tsv` | clade → species sets |

## Pipeline

| Script | Does |
|--------|------|
| `001_ai-python-build_leonid_table.py` | builds the whole table (annotations + deconvolution) → 1-output |
| `002_ai-python-validate_results.py` | independent fail-fast cross-checks → 2-output |
| `003_ai-python-write_run_log.py` | §45 run log → ai/logs |

## Fail-fast checks (§36) — a silent artifact here is a research-integrity failure

Script 001 exits 1 on: missing inputs; a Rule-6 violation (a `clade_id_name` with
different species across the selected structures); a member species that is not a
tree tip (would be silently uncounted); a full-coverage clade whose count ≠ the
member count; an annotated (membership) sequence absent from the orthogroups (a
silently dropped annotation — offenders are written before exit); or an annotation
name containing the `;` NAME delimiter. Script 002 re-checks the output table
independently (row count, member/sequence-count agreement, singleton flag,
deconvolution completeness, accession/name alignment).

## Conda environment

`aiG-integrator-orthogroups_X_leonid_08july2026` (python + pyyaml + nextflow;
created on-demand by `RUN-workflow.sh`).

## Notes / caveats

- Includes **all** orthogroups, singletons included (167,558 of 202,994 are
  singletons); `Is_Singleton` + `Member_Sequence_Count` make them easy to filter.
- Annotation coverage depends on the annogroups build; orthogroups whose members
  have no feature for a source get empty annotation cells (correct, not an error).
