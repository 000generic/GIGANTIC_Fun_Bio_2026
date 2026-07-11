<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 10
Human:   Eric Edsinger
Purpose: User-facing overview of BLOCK_orthogroups_X_all_annotations.
============================================================================ -->

# BLOCK_orthogroups_X_all_annotations

An integration BLOCK that produces a **single table with one row per OrthoHMM
orthogroup**, combining the orthogroup's member sequences with **seven annotation
types** and a **species-tree deconvolution** across structures 001, 003, 031, 032.

## What it produces

`OUTPUT_pipeline/1-output/1_ai-orthogroups_X_all_annotations.tsv` — one row per orthogroup:

| Column(s) | Meaning |
|-----------|---------|
| `Orthogroup_ID` | OrthoHMM orthogroup identifier (e.g. `OG000000`) |
| `Sequence_IDs` | comma-delimited full GIGANTIC member protein IDs |
| `Member_Sequence_Count` | number of member sequences |
| `Is_Singleton` | `yes` if one member else `no` |
| **per type ×7** | `<Type>_Species_Count`, `<Type>_Sequence_Count`, `<Type>_Identifiers` (comma), `<Type>_Names` (` // `) |
| …clade / species columns… | one column per **non-redundant** clade or species across structures 001/003/031/032; each cell = count of member sequences within that clade |

The seven annotation types (in column order): **Pfam, GO, PANTHER, Gene_Families,
Gene_Groups, Dark_Proteome, Hotspots**. For each type:

- `<Type>_Species_Count` — non-redundant number of species (Genus_species) among
  member sequences carrying ≥1 annotation of that type
- `<Type>_Sequence_Count` — number of member sequences carrying ≥1 annotation
- `<Type>_Identifiers` — comma-delimited non-redundant identifiers
- `<Type>_Names` — ` // `-delimited names aligned to the identifiers

## What each type's identifier / name is

| Type | Identifier | Name | Join |
|------|-----------|------|------|
| Pfam | `PF#####` | domain description | full GIGANTIC sequence id |
| GO | `GO:#######` | GO term name | full GIGANTIC sequence id |
| PANTHER | `PTHR#####` | family description | full GIGANTIC sequence id |
| Gene_Families | family slug | family slug (no separate name table) | full GIGANTIC sequence id (in AGS FASTA) |
| Gene_Groups | `gg<N>` (or `snap_family`) | HGNC group name | full GIGANTIC sequence id (in AGS FASTA) |
| Dark_Proteome | `DARK` / `ANNOTATED` | fired annotation-source axes (or `none`) | full GIGANTIC sequence id |
| Hotspots | `Hotspot_ID` | *(blank — hotspots have no human name)* | (Genus_species, bare gene id) |

**Why ` // ` for names.** Human-readable names frequently contain commas (e.g.
"positive regulation of transcription, DNA-templated"), semicolons, or pipes — so
no single reserved character is a safe separator. The `*_Names` columns use the
multi-character delimiter **` // `** (space slash slash space), which has zero
collisions across the species70 names — a deliberate, flagged §34 deviation. The
build fails fast if any name ever contains ` // `. The `*_Identifiers` columns stay
strictly comma-delimited and §34-compliant.

**Species-tree deconvolution.** The clade columns are the union of clades (internal
nodes) and species (tips) across the four selected structures. Because a
`clade_id_name` identifies a fixed topologically-structured species set (Rule 6),
the same clade has the same member-sequence count in every structure it appears in
— so the union is non-redundant, and each header records which structures the clade
appears in. Column order: largest clade (a root, count = member count) → tips.

## Important caveats (research integrity)

- **Dark proteome** input currently reads from the classify RUN's
  `OUTPUT_pipeline/3-output` (all 70 species). The subproject's `output_to_input`
  only exposes one species; ideally it is re-published with all 70. See the config.
- **Hotspots cover 64 of 70 species** (6 lack gene coordinates). Members of those 6
  species have hotspot coverage of 0 by construction, not "tested absent."
- **Gene families** have no central name table, so the slug is used as both the
  identifier and the name.
- **Hotspots** have no human-readable name, so `Hotspots_Names` is intentionally blank.

## Quick start

```bash
cd workflow-COPYME-orthogroups_X_all_annotations
# edit START_HERE-user_config.yaml (run_label, slurm_account/qos, structures)
bash RUN-workflow.sh
```

Outputs land in `OUTPUT_pipeline/` and are symlinked to
`../../output_to_input/BLOCK_orthogroups_X_all_annotations/<run_label>/`.

For the join design, data flow, and troubleshooting, see [`AI_GUIDE.md`](AI_GUIDE.md).
