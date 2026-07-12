# sequence_groups_X_species

**Resolve any sequence-group set onto the species-tree clades.**

This subproject answers one question, for any kind of group of protein sequences:
**where do each group's members fall on the species tree?** It does not create
groups — it *consumes* groups that other subprojects produce and overlays their
membership onto the species tree's clades.

## What is a "sequence group"?

A sequence group is producer-agnostic — any grouping of protein sequences:

| Producer | Sequence group | Grouped by |
|---|---|---|
| `orthogroups` | orthogroup (e.g. `OG000123`) | orthology (OrthoHMM / OrthoFinder / Broccoli) |
| `annogroups` | annogroup (e.g. `annogroup_pfam_PF00069`) | shared annotation |
| `trees_gene_families` / `trees_gene_groups` | gene family / group | curated homology |

Each producer is read through a small **adapter** (Script 001) into one STANDARD
membership table:

```
SequenceGroup_ID    Sequence_Identifier    Genus_Species
```

Everything downstream reads only that table, so the overlays are identical for
every producer. Adding a producer = add a reader branch in Script 001; nothing
else changes.

## The three overlays

For one group set + the `trees_species` clade structure, it produces:

1. **Species-tree deconvolution** (`2-output/`) — per group, the count of member
   **sequences** and member **species** within every non-redundant clade across all
   105 species-tree structures (a full-coverage root clade equals the group's totals).
2. **Per-species sequence map** (`3-output/`) — per group, the member sequence
   identifiers broken out by species (the wide form of the standard membership).
3. **Composite clades** (`4-output/`) — per group, *which clades its members span*,
   classified by four algorithms: `exact`, `absent`, `core_urclade`, `core_early_clade`
   (see the workflow config / `INPUT_user/composite_clades_manifest.tsv`).

These are structure-independent (member species are stable across structures,
GIGANTIC Rule 6); the deconvolution union lays every clade across the 105 trees out
as columns.

## Where it sits in the GIGANTIC DAG

```
   trees_species ─────────────┐  (species-tree clades)
                              ▼
   annogroups ──┐
   orthogroups ─┼──► sequence_groups_X_species ──► integrator, server, downstream
   gene families┘     (composite / deconvolution / per-species)
```

It is **downstream** of both the group producers and `trees_species`, and feeds
consumers that need "where on the tree" answers. (This is why it is its own
subproject, not a block inside `trees_species` — the foundation stays pure-upstream.)

## Structure

```
sequence_groups_X_species/
├── BLOCK_sequence_groups/
│   └── workflow-COPYME-sequence_groups/   # the workflow (copy to a RUN dir to run)
├── output_to_input/<group_set_label>/    # published overlays for downstream
└── upload_to_server/                     # curated overlays for the GIGANTIC server
```

Run by copying `workflow-COPYME-sequence_groups/` to a `workflow-RUN_N-sequence_groups/`,
editing `START_HERE-user_config.yaml` (group set, producer, inputs), and running
`bash RUN-workflow.sh`. One run resolves one group set, namespaced by
`group_set_label` (e.g. `species70_X_OrthoHMM`).

**For AI assistants**: read `../../AI_GUIDE-project.md` first for the GIGANTIC
overview, then `AI_GUIDE-sequence_groups_X_species.md` here for this subproject.
