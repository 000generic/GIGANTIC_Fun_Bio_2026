# AI_GUIDE: homolog_counts

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 22 (initial; in commit 8486969 sweep)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — GIGANTIC overview + general patterns
- Subproject README: [`README.md`](README.md)
- BLOCK template: [`BLOCK_homolog_counts/workflow-COPYME-homolog_counts/`](BLOCK_homolog_counts/workflow-COPYME-homolog_counts/)
- Workflow AI guide: [`BLOCK_homolog_counts/workflow-COPYME-homolog_counts/ai/AI_GUIDE.md`](BLOCK_homolog_counts/workflow-COPYME-homolog_counts/ai/AI_GUIDE.md)
- Reads FROM:
  - `../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/` — orthogroup IDs
  - `../trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/` — gene group names
  - `../trees_gene_families/output_to_input/` — gene family names
  - species70 phyloname map (from genomesDB / phylonames)
- Outputs TO: `output_to_input/BLOCK_homolog_counts/` — wide TSV per source (Feature_ID × 70 species columns)
- Downstream consumers: GIGANTIC server (`upload_to_server/`), comparative analysis pipelines
- `one_direction_homologs` intentionally excluded (axis mismatch — per-query NCBI top hits don't map to "homolog group × species" cleanly)

---

**For AI Assistants**: Read the project-level guide (`../../AI_GUIDE.md`) first for GIGANTIC overview, directory structure, and general patterns. This guide covers the `homolog_counts` subproject specifically.

## Quick Reference

| User needs… | Go to… |
|---|---|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| Subproject overview | `README.md` |
| Subproject concepts, output schema | This file |
| Running the workflow | `BLOCK_homolog_counts/workflow-COPYME-homolog_counts/ai/AI_GUIDE.md` |

## Purpose

Counts homologs per species70 species across multiple upstream GIGANTIC subprojects, producing one wide TSV per source. Each TSV is keyed on a source-specific feature group (orthogroup, gene group, or gene family) with counts per species70 species.

These tables are produced for local analysis AND for hosting on the GIGANTIC server via `upload_to_server/`.

## Subproject Structure

```
homolog_counts/
├── AI_GUIDE.md
├── README.md
├── output_to_input/                              # symlink hub for downstream subprojects
│   └── BLOCK_homolog_counts/                     # populated by RUN-workflow.sh
├── upload_to_server/                             # curated counts for the GIGANTIC server
└── BLOCK_homolog_counts/
    └── workflow-COPYME-homolog_counts/
        ├── START_HERE-user_config.yaml           # USER edits this before running
        ├── RUN-workflow.sh                       # unified entrypoint: local or SLURM via execution_mode in YAML
        ├── INPUT_user/
        └── ai/
            ├── main.nf
            ├── nextflow.config
            ├── conda_environment.yml             # auto-created on first run
            ├── AI_GUIDE.md
            └── scripts/
                ├── 001_ai-python-validate_species70_manifest.py
                ├── 002_ai-python-count-orthogroups_orthohmm.py
                ├── 003_ai-python-count-trees_gene_groups.py
                ├── 004_ai-python-count-trees_gene_families.py
                ├── 005_ai-python-write_run_log.py    (canonical final per §45)
                └── 006_ai-python-rewrite_species_column_headers.py    (post-pipeline header normalization)
```

Single BLOCK because the work is independently runnable — no internal sequential phases. Each counting script is independent of the others; only script 001 (manifest validation) must run first to produce the canonical species70 column order shared across all count TSVs.

## Upstream Sources

| Source | Subproject `output_to_input/` path | Feature_ID unit |
|---|---|---|
| OrthoHMM orthogroups | `orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/` | orthogroup ID |
| HGNC gene groups | `trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/` | gene group name |
| Curated gene families | `trees_gene_families/output_to_input/` | gene family name |

`one_direction_homologs` is intentionally **excluded** — its feature axis is per-query NCBI top hits, which does not map cleanly to "homolog group × species" counts. Adding it would require a different table schema and was deferred during scoping.

## Output Schema

Each counting script writes ONE wide TSV with this column order:

| # | Column | Description |
|---|---|---|
| 1 | `Feature_ID (...)` | Source-specific group identifier (orthogroup ID / gene group name / gene family name) |
| 2 | `Total_Count (...)` | Sum across all 70 species |
| 3 | `Total_Species_Count (...)` | Number of species with count ≥1 |
| 4–73 | per-species counts | 70 columns, ordered alphabetically by phyloname |

Species column order is derived ONCE by script 001 from `species70_map-genus_species_X_phylonames.tsv` (sorted alphabetically by the phyloname field, NOT genus_species). All counting scripts read this canonical order to guarantee identical column order across source TSVs.

Headers follow GIGANTIC self-documenting convention: `Header_ID (description with spaces)`.

## Path Portability

`START_HERE-user_config.yaml` inputs use relative paths (`../../../<subproject>/output_to_input/...`) to sibling subprojects, matching the orthohmm convention. The workflow code reads these from YAML — no main.nf edits needed.

## Server Hosting

The per-source count TSVs are hosted on the GIGANTIC server via the shared-helper pattern (matching `annotations_hmms` / `orthogroups` / `sequence_groups_X_species`):

- Each workflow ships a per-workflow `upload_manifest.tsv` (at the workflow root) with self-documenting `display_label` / `description` / `order` columns; it travels into each `workflow-RUN_*` dir.
- `RUN-update_upload_to_server.sh` at the subproject root is a thin wrapper that calls `../../server/ai/update_upload_to_server.py`, which publishes the newest `workflow-RUN_*` into a nested tree under `upload_to_server/BLOCK_homolog_counts/workflow-RUN_*/<N>-output/` and prunes superseded runs.

## Where to Look Next

- `BLOCK_homolog_counts/workflow-COPYME-homolog_counts/ai/AI_GUIDE.md` — workflow execution
- `BLOCK_homolog_counts/workflow-COPYME-homolog_counts/START_HERE-user_config.yaml` — edit before running

---

## Session hygiene (per §61)

For productive project work:
- **Root every chat session at this named `gigantic_project-*/` directory**.
  Not at `GIGANTIC/` (framework root, reserved for framework dev per §16),
  not at `subprojects/<X>/`, not at a `workflow-COPYME-*/` dir, not at
  any directory deeper than the named project root.
- **One chat session per subproject** you're actively working in — keeps
  context focused and prevents cross-subproject confusion.
- **Continue the same session over many compactions** (lossless per §9)
  until it becomes muddled or slow; then start fresh in a new session,
  same root, same subproject focus.
- **Keep a separate "small questions" session** for one-off questions
  so subproject sessions stay focused.

See `ai/ai_FYIs/gigantic_conventions.md` §61 for the full rationale.
