# BLOCK_sequence_groups

The one block of `sequence_groups_X_species`: it **resolves a sequence-group set
onto the species-tree clades**.

A single NextFlow workflow reads one group set (via a producer adapter) and overlays
its membership onto the species tree three ways — deconvolution, per-species map, and
composite clades.

```
workflow-COPYME-sequence_groups/    # the template (copy to a RUN dir to run)
└── ai/scripts/
    ├── 001 adapt_sequence_group_membership   producer -> standard membership
    ├── 002 species_tree_deconvolution        sequence + species counts per clade
    ├── 003 per_species_sequence_map          member sequence ids per species
    ├── 004 composite_clades                  4 algorithms over member species
    ├── 005 write_run_log
    └── utils_sequence_groups.py              composite engine + clade/phyloname helpers
```

**Run it**: copy `workflow-COPYME-sequence_groups/` to
`workflow-RUN_N-sequence_groups/`, edit `START_HERE-user_config.yaml`
(group set, producer, inputs), then `bash RUN-workflow.sh`.

See `../README.md` for the concept and `../AI_GUIDE-sequence_groups_X_species.md`
for the AI guide.
