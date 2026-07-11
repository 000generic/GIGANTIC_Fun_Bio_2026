# AI_GUIDE: secretome

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 21 (initial; Moroz spec scoping)
AI:      Claude Code | Opus 4.7 | 2026 May 23 (STEP_1-build_evidence_table scaffold)
AI:      Claude Code | Opus 4.7 | 2026 May 25 (STEP_2-filter_secretome scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — GIGANTIC overview + general patterns
- Subproject README: [`README.md`](README.md)
- Three units (two sequential STEPs + one independent BLOCK):
  - [`STEP_1-build_evidence_table/`](STEP_1-build_evidence_table/) — pivots annotation DB to per-protein evidence tables (feeds STEP_2)
  - [`STEP_2-filter_secretome/`](STEP_2-filter_secretome/) — applies filters to STEP_1 evidence tables → per-species secretome
  - [`BLOCK_secretome_per_moroz_17may2026/`](BLOCK_secretome_per_moroz_17may2026/) — Moroz lab spec implementation (independent BLOCK; scaffold only, awaiting upstream data)
- Reads FROM:
  - `../annotations_hmms/output_to_input/BLOCK_build_annotation_database/` — long-format standardized annotation DB
  - `../annotations_hmms/output_to_input/BLOCK_signalp/` — SignalP6 predictions
  - `../annotations_hmms/output_to_input/BLOCK_deeploc/` — DeepLoc 2.0 predictions
  - `../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/` — Pfam annotations
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` — proteomes
- Outputs TO (`output_to_input/`):
  - `STEP_1-build_evidence_table/` — per-species evidence tables (one wide TSV per species)
  - `STEP_2-filter_secretome/` — per-species filtered secretome tables
  - `BLOCK_secretome_per_moroz_17may2026/` — (future, when scripted)
- Downstream consumers: comparative analyses, `upload_to_server/` (shared-helper publish; see Server Hosting)
  - **integrator** — `../integrator/BLOCK_orthogroups_ocl_X_features/` reads
    `output_to_input/STEP_2-filter_secretome/` (filtered-secretome membership →
    `Is_Secreted`) and `output_to_input/STEP_1-build_evidence_table/`
    (SignalP / DeepLoc / Pfam evidence columns for the gene-level drill-down),
    joining onto OCL orthogroups by full GIGANTIC sequence ID. See
    `../integrator/AI_GUIDE.md`.

## Unit naming (STEP vs BLOCK)

`STEP_1-build_evidence_table/` and `STEP_2-filter_secretome/` are a
sequential pair: STEP_1's output is the required input to STEP_2, so both
carry `STEP_` prefixes per §41 + memory `feedback_block_vs_step_semantics`
(STEPs are sequentially-dependent; BLOCKs are independently-runnable). The
evidence-table unit was originally scaffolded as `BLOCK_secretome_evidence_table`
and has since been renamed to `STEP_1-build_evidence_table` to reflect this.

`BLOCK_secretome_per_moroz_17may2026/` is a separate (orthogonal)
experimental implementation of the Moroz spec — it's a true BLOCK
(no STEP dependency).

---

**For AI Assistants**: Read the project-level guide (`../../AI_GUIDE.md`) first for GIGANTIC overview, directory structure, and general patterns. This guide covers the `secretome` subproject specifically.

> **Build location note** (May 2026): This subproject was developed initially at `~/secretome/` because `/blue/` was out of space. Contents are now in this canonical location (`gigantic_project-COPYME/subprojects/secretome/`). As of the July 2026 modernization, all `START_HERE-user_config.yaml` files use **relative** upstream paths (resolved against the workflow root via `--workflow-root`, matching `resolve_groups`); the old absolute paths have been removed.

## Quick Reference

| User needs… | Go to… |
|---|---|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| Subproject overview | `README.md` |
| Subproject concepts (this file) | This file |
| Build evidence table (STEP_1) | `STEP_1-build_evidence_table/AI_GUIDE.md` |
| Filter to secretome (STEP_2) | `STEP_2-filter_secretome/AI_GUIDE.md` |
| Moroz 2026-05-17 spec implementation | `BLOCK_secretome_per_moroz_17may2026/AI_GUIDE.md` |
| Running build_evidence_table workflow | `STEP_1-build_evidence_table/workflow-COPYME-build_evidence_table/ai/AI_GUIDE.md` |
| Running filter_secretome workflow | `STEP_2-filter_secretome/workflow-COPYME-filter_secretome/ai/AI_GUIDE.md` |
| Running per_moroz workflow (scaffold only) | `BLOCK_secretome_per_moroz_17may2026/workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE.md` |

## Purpose

Identify the secretome (proteins exported to extracellular space) across the species70 set, using sequential KEEPER/DROPPER filters on signal-peptide, membrane-topology/localization, and Pfam-domain-composition annotations. Each script's KEEPER output is the input to the next script.

This is the first BLOCK of the subproject: `BLOCK_secretome_per_moroz_17may2026` — defined per Moroz lab specification on 2026-05-17.

## Status (as of 2026-05-21)

**Scaffold only — no scripts written yet.** Awaiting two pieces of data from `annotations_hmms` before scripting can resume:

| Upstream | Status | Notes |
|---|---|---|
| **SignalP6** on species70 | 🟡 Pipeline rerunning at `~/temporary_annotations/BLOCK_signalp/` (SLURM job `32899825`, moroz-b burst, fast mode, started 2026-05-21 03:58 — pending on a SLURM reservation until ~08:29 today, then 9-wide parallel for ~70 species) | Previous attempt produced 2/70 species. Awaiting fresh full-coverage output. |
| **DeepLoc 2.0** on species70 | ✅ Complete, 70/70 species | Lives at `/blue/.../annotations_hmms/output_to_input/BLOCK_deeploc/*_deeploc_predictions.csv` |
| **InterProScan Pfam** on species70 | ✅ Complete, 70/70 species | Lives at `/blue/.../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/pfam-<phyloname>.tsv` |
| ~~**TMBed** on species70~~ | ❌ Abandoned — DeepLoc replaces it (better fit: predicts TM probability **and** cell-membrane/extracellular localization in one tool) | Original TMBed run failed due to `transformers<5` incompatibility with `tmbed 1.0.2`. Not pursued. |

## Pipeline Logic (Moroz spec, 2026-05-17)

Sequential KEEPER/DROPPER filters. Each script's KEEPER output is the next script's input.

| # | Script | Filter | KEEPER definition | DROPPER definition |
|---|---|---|---|---|
| 001 | SignalP6 signal peptide | `Sec/SPI` only (classical secretory) | protein has SignalP6 prediction = `Sec/SPI` | no SignalP prediction OR `Sec/SPII` (lipoprotein) OR `Tat/SPI` (Tat) |
| 002 | DeepLoc TM / localization | replaces the originally-spec'd TMBed step | low `Transmembrane` probability AND/OR high `Extracellular` probability (exact thresholds TBD with user when scripting resumes) | high TM probability OR localized away from secretory path |
| 003 | Pfam domain composition (strict) | unchanged from original spec | (unique Pfam accessions = 1 AND total Pfam hits ≤ 4) OR (unique Pfam accessions = 2 AND total Pfam hits = 2) | everything else (e.g., 5+ copies of one domain; 3+ unique domains; mixed like 2-of-A + 1-of-B) |
| 004–010 | TBD | TBD | TBD | TBD |

### Decisions captured 2026-05-20/21

- **Build location**: `~/secretome/` (typo `secreteome` corrected to `secretome`); will rsync into `gigantic_project-COPYME/subprojects/secretome/` once `/blue/` space is restored.
- **First BLOCK name**: `BLOCK_secretome_per_moroz_17may2026`.
- **SignalP keeper type**: `Sec/SPI` only.
- **TM/membrane tool**: DeepLoc 2.0 (replaces TMBed). Reason: DeepLoc gives TM probability AND specific compartment probabilities (Cell membrane, Extracellular, Cytoplasm, Nucleus, ER, Golgi, etc.), which matches the original "cell membrane only" intent natively. TMBed only predicts per-residue TM topology — no localization — and is currently broken in the shared conda env.
- **Pfam edge cases**: Strict interpretation (1–4 of one OR exactly 2 different).

### Known open questions (revisit when scripting resumes)

1. **DeepLoc thresholds** for Script 002: choose probability cutoffs for `Transmembrane` (e.g., < 0.5) and `Extracellular` (e.g., ≥ 0.5). Also decide if "Cell membrane only" is a separate downstream track or just a secondary annotation column.
2. **SignalP `SP_Probability` anomaly**: a 2-species sample from the prior partial run showed all rows with probability ~0.0001 despite `Prediction = SP`. Verify on the new fresh run that values look biologically plausible (e.g., median ≥ 0.5 for keepers). If they still look strange, investigate SignalP run config.
3. **DeepLoc `Signals` column** has signal-peptide info too — decide whether SignalP6 remains canonical or whether DeepLoc's signal-peptide call is used as a cross-check.
4. **Pfam hit overlap**: multiple HMM hits at overlapping residue ranges for the same accession — count as 1 or N for the "≤ 4 copies" rule?

## Subproject Structure

```
secretome/
├── AI_GUIDE.md
├── README.md
├── output_to_input/                                          # symlink hub for downstream subprojects
│   └── BLOCK_secretome_per_moroz_17may2026/                  # populated by RUN-workflow.sh
├── upload_to_server/                                         # curated outputs for the GIGANTIC server (shared-helper nested tree)
└── BLOCK_secretome_per_moroz_17may2026/
    └── workflow-COPYME-secretome_per_moroz_17may2026/
        ├── START_HERE-user_config.yaml                       # USER edits this before running
        ├── RUN-workflow.sh                                   # unified entrypoint: local or SLURM via execution_mode in YAML
        ├── INPUT_user/                                       # user-supplied inputs (manifests, FASTAs, ...)
        └── ai/
            ├── main.nf
            ├── nextflow.config
            ├── conda_environment.yml                         # auto-created on first run
            ├── AI_GUIDE.md
            └── scripts/                                      # NNN_ai-python-*.py (to be defined)
```

Single BLOCK because the work is independently runnable — no internal sequential phases. Multi-BLOCK structure can be added later if the subproject grows (e.g., `BLOCK_secretome_per_moroz_17may2026`, `BLOCK_<later_analysis>/`).

## Upstream Sources

| Source | Path (absolute, current build phase) | Format / key columns | Used by |
|---|---|---|---|
| species70 proteome FASTAs | `/blue/.../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes/<phyloname>-T1-proteome.aa` | FASTA; headers `g_<gene>-t_<rna>-p_<protein>-n_<phyloname>` | Script 001 (parse identifiers) |
| species70 phyloname map | `/blue/.../phylonames/output_to_input/STEP_1-generate_and_evaluate/maps/species70_map-genus_species_X_phylonames.tsv` | TSV: `genus_species`, `phyloname`, `phyloname_taxonid` | All scripts (canonical species order) |
| SignalP6 predictions | (post-rerun) `~/temporary_annotations/BLOCK_signalp/workflow-COPYME-run_signalp/OUTPUT_pipeline/2-output/<phyloname>_signalp_predictions.tsv` → eventually `/blue/.../annotations_hmms/output_to_input/BLOCK_signalp/` | TSV: `Protein_Identifier`, `Prediction` (Sec/SPI \| Sec/SPII \| Tat/SPI), `Cleavage_Site_Position`, `SP_Probability` | Script 001 |
| DeepLoc 2.0 predictions | `/blue/.../annotations_hmms/output_to_input/BLOCK_deeploc/<phyloname>_deeploc_predictions.csv` | CSV: `Protein_ID`, `Localizations`, `Signals`, `Membrane types`, `Cytoplasm`, `Nucleus`, `Extracellular`, `Cell membrane`, `Mitochondrion`, `Plastid`, `Endoplasmic reticulum`, `Lysosome/Vacuole`, `Golgi apparatus`, `Peroxisome`, `Peripheral`, `Transmembrane`, `Lipid anchor`, `Soluble` | Script 002 |
| InterProScan Pfam | `/blue/.../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/pfam-<phyloname>.tsv` | TSV (multi-row per protein): `Protein_Identifier`, `MD5`, `Sequence_Length`, `Analysis_Database` (Pfam), `Accession` (PF#####), `Description`, `Match_Start`, `Match_End`, `Score_Or_Evalue`, … | Script 003 |

## Output Schema

TODO — define once table outputs are specified (column headers must follow GIGANTIC self-documenting convention: `Header_ID (description with spaces)`).

## Path Portability

Two ways inputs can be specified in `START_HERE-user_config.yaml`:

| Build phase | Path style |
|---|---|
| Under `~/secretome/` (current) | Absolute `/blue/moroz/share/.../` |
| Inside `gigantic_project-COPYME/subprojects/secretome/` (post-rsync) | Relative `../../../<subproject>/output_to_input/...` |

The workflow code reads these from YAML — no `main.nf` edits needed when switching path styles.

## Server Hosting

Server publishing uses the **shared-helper pattern** (matches `resolve_groups`
and `homolog_counts`):

- Each workflow carries its own `upload_manifest.tsv` (in the
  `workflow-COPYME-*` template; it travels into every `workflow-RUN_*` copy).
  - STEP_1 publishes the per-species evidence tables + validated manifest.
  - STEP_2 publishes the per-species secretome tables + validated filter
    manifest (the collaborator-facing deliverable).
- The subproject-root `RUN-update_upload_to_server.sh` is a thin wrapper around
  the shared helper `../../server/ai/update_upload_to_server.py`. Run it from
  the subproject root:

  ```bash
  bash RUN-update_upload_to_server.sh            # publish
  bash RUN-update_upload_to_server.sh --dry-run  # preview
  ```

- The helper discovers every `workflow-RUN_*/upload_manifest.tsv`, publishes
  **only the most recent RUN per step**, and materializes a nested tree:
  `upload_to_server/<STEP>/workflow-RUN_*/N-output/<file>` (superseded runs and
  stale symlinks are pruned automatically). Do NOT hand-edit
  `upload_to_server/` — it is rebuilt from the manifests.

## Where to Look Next

- `BLOCK_secretome_per_moroz_17may2026/workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE.md` — workflow execution
- `BLOCK_secretome_per_moroz_17may2026/workflow-COPYME-secretome_per_moroz_17may2026/START_HERE-user_config.yaml` — edit before running

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
