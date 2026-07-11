<!-- ============================================================================
AI:      Claude (Cursor) | Opus 4.8 | 2026 July 08
Human:   Eric Edsinger
Purpose: User-facing overview of BLOCK_orthogroups_X_leonid_08july2026.
============================================================================ -->

# BLOCK_orthogroups_X_leonid_08july2026

A one-off integration BLOCK (requested by Leonid, 2026-07-08) that produces a
**single table with one row per OrthoHMM orthogroup**, combining the orthogroup's
member sequences, its non-redundant Pfam/GO/PANTHER annotations, and a
**species-tree deconvolution** across structures 001, 003, 031, and 032.

## What it produces

`OUTPUT_pipeline/1-output/1_ai-orthogroups_X_leonid.tsv` — one row per orthogroup:

| Column | Meaning |
|--------|---------|
| `Orthogroup_ID` | OrthoHMM orthogroup identifier (e.g. `OG000000`) |
| `Sequence_IDs` | comma-delimited full GIGANTIC member protein IDs |
| `Member_Sequence_Count` | number of member sequences |
| `Is_Singleton` | `yes` if one member else `no` |
| `Pfam_Accessions` / `Pfam_Names` | non-redundant Pfam accessions (comma) + names (` // `) |
| `GO_Accessions` / `GO_Names` | non-redundant GO IDs (comma) + names (` // `) |
| `PANTHER_Accessions` / `PANTHER_Names` | non-redundant PANTHER accessions (comma) + names (` // `) |
| …clade / species columns… | one column per **non-redundant** clade or species across structures 001/003/031/032; each cell = count of the orthogroup's member sequences within that clade |

**Why two columns per annotation source.** The `*_Accessions` columns are strictly
comma-delimited (GIGANTIC §34). Human-readable **names** frequently contain commas
(e.g. "positive regulation of transcription, DNA-templated") and a few contain a
semicolon (e.g. Pfam PF13720 "Udp N-acetylglucosamine O-acyltransferase; Domain 2")
or a pipe — so no single reserved character is a safe separator. The paired
`*_Names` columns therefore use the multi-character delimiter **` // `** (space
slash slash space), which has zero collisions across the species70 pfam/go/panther
names — a deliberate, flagged §34 deviation. The build fails fast if any name ever
contains ` // `.

**Species-tree deconvolution.** The clade columns are the union of all clades
(internal nodes) and species (tips) seen across the four selected structures.
Because a `clade_id_name` identifies a fixed topologically-structured species set
(GIGANTIC Rule 6), the same clade has the same member-sequence count in every
structure it appears in — so the union is non-redundant, and each column header
records which of the four structures the clade appears in. Column order runs from
the largest clade (a tree root, whose count equals the member count) down to the
species tips.

## Annotation source

Pfam/GO/PANTHER are taken from the validated **annogroups** subproject
FEATURE-type membership (one feature annogroup per distinct accession a sequence
carries), keyed on the full GIGANTIC sequence identifier — identical IDs to the
orthogroup members, so the join is exact. A sequence with no feature for a source
simply contributes nothing (empty cell), which is the correct non-redundant result.

## Quick start

```bash
cd workflow-COPYME-orthogroups_X_leonid_08july2026
# edit START_HERE-user_config.yaml (run_label, slurm_account/qos, structures)
bash RUN-workflow.sh
```

Outputs land in `OUTPUT_pipeline/` and are symlinked to
`../../output_to_input/BLOCK_orthogroups_X_leonid_08july2026/<run_label>/`.

For the join design, the data flow, and troubleshooting, see
[`AI_GUIDE.md`](AI_GUIDE.md).
