# secretome — Per-Protein Secretome Identification

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 21 (initial; Moroz spec scoping)
AI:      Claude Code | Opus 4.7 | 2026 May 23 (STEP_1-build_evidence_table scaffold)
AI:      Claude Code | Opus 4.7 | 2026 May 25 (STEP_2-filter_secretome scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
  - `../annotations_hmms/output_to_input/BLOCK_build_annotation_database/` — long-format standardized annotation DB
  - `../annotations_hmms/output_to_input/BLOCK_signalp/` — SignalP6 predictions (signal peptides)
  - `../annotations_hmms/output_to_input/BLOCK_deeploc/` — DeepLoc 2.0 predictions (TM + subcellular localization)
  - `../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/` — Pfam domain annotations
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` — proteomes
- Outputs to (`output_to_input/`):
  - `STEP_1-build_evidence_table/` — per-species wide evidence tables
  - `STEP_2-filter_secretome/` — per-species filtered secretome tables
  - `BLOCK_secretome_per_moroz_17may2026/` — (future, when scripted)
- Downstream consumers: comparative analyses, `upload_to_server/` (shared-helper publish)

---

## Purpose

Identify the secretome (proteins exported to extracellular space) across
the species70 set, using sequential KEEPER/DROPPER filters on
signal-peptide, membrane-topology/localization, and Pfam-domain-composition
annotations from the `annotations_hmms` subproject.

Per Moroz lab specification (2026-05-17).

## Architecture — three units

| Path | Type | Status | Purpose |
|------|------|--------|---------|
| `STEP_1-build_evidence_table/` | STEP (sequential; feeds STEP_2-filter_secretome) | Implemented (validate + evidence-table builder) | Pivot the long-format `annotations_hmms` DB into one wide per-protein TSV per species |
| `STEP_2-filter_secretome/` | STEP_2 | Implemented (6 scripts: validate / 3 augmenters / filter / write_run_log) | Consume the evidence tables; augment with derived cols + orthogroups + top-10 BLAST; apply user-defined filters → per-species secretome |
| `BLOCK_secretome_per_moroz_17may2026/` | BLOCK (orthogonal — separate implementation track) | Scaffold only (awaiting upstream SignalP refresh) | Direct implementation of the Moroz 2026-05-17 spec with sequential KEEPER/DROPPER filters |

(See `AI_GUIDE.md` for the BLOCK-vs-STEP naming inconsistency and full
upstream-data table.)

## Prerequisites

- **annotations_hmms** complete (BLOCK_build_annotation_database +
  BLOCK_signalp + BLOCK_deeploc + BLOCK_interproscan with Pfam parser)
- **genomesDB** complete (proteomes for species70 phyloname headers)
- Conda envs auto-created on first run per workflow:
  - `aiG-secretome-build_evidence_table`
  - `aiG-secretome-filter_secretome`
  - `aiG-secretome-secretome_per_moroz_17may2026`
  (per-§28 strict form — three separate envs since each unit has
  distinct dependency needs)

## Quick Start

```bash
# Recommended sequence: build evidence tables, then filter
# 1. Build evidence tables (STEP_1)
cd STEP_1-build_evidence_table
cp -r workflow-COPYME-build_evidence_table workflow-RUN_1-build_evidence_table
cd workflow-RUN_1-build_evidence_table
vi START_HERE-user_config.yaml
bash RUN-workflow.sh

# 2. Filter to secretome (STEP_2)
cd ../../STEP_2-filter_secretome
cp -r workflow-COPYME-filter_secretome workflow-RUN_1-filter_secretome
cd workflow-RUN_1-filter_secretome
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
```

The Moroz-spec branch (`BLOCK_secretome_per_moroz_17may2026/`) is a
scaffold awaiting upstream SignalP refresh — see its AI_GUIDE.md before
attempting to run.

## Documentation

| File | Purpose |
|---|---|
| `AI_GUIDE.md` | Subproject concepts, Moroz spec detail, naming-inconsistency note |
| `BLOCK_*/AI_GUIDE.md` and `STEP_2-*/AI_GUIDE.md` | Per-unit AI guide |
| `BLOCK_*/workflow-COPYME-*/README.md` and `.../ai/AI_GUIDE.md` | Workflow-level docs |
| `*/workflow-COPYME-*/START_HERE-user_config.yaml` | User-editable run configuration |

## Status (2026-07-11)

- `STEP_1-build_evidence_table/` — validate + evidence-table builder
  implemented and run (70 per-species wide evidence tables).
- `STEP_2-filter_secretome/` — 6 scripts implemented and run
  (augment with derived cols / orthogroups / blastp_top10 + filter + run log);
  orthogroups sourced from `BLOCK_orthohmm_GIGANTIC` (202,994 orthogroups).
- `BLOCK_secretome_per_moroz_17may2026/` — scaffold only, awaiting fresh
  SignalP run from annotations_hmms.
- Server: STEP_1 + STEP_2 published via shared-helper wrapper
  (`RUN-update_upload_to_server.sh`) into the nested `upload_to_server/` tree.

---

## Session hygiene (per §61 in `ai/ai_FYIs/gigantic_conventions.md`)

GIGANTIC's chat-as-research-notebook convention (§9) works best with
disciplined session hygiene. Two recommendations.

### Always root at the named gigantic_project-COPYME

Every chat session for project work should be initiated rooted at the
user's renamed copy of `gigantic_project-COPYME/` — e.g.,
`gigantic_project-cephalopod_evolution/`.

**Not** at:
- `GIGANTIC/` (the framework root, reserved for framework-development
  sessions per §16)
- `subprojects/<X>/` (a subproject directory)
- `subprojects/<X>/<BLOCK_or_STEP>/workflow-COPYME-*/` (a workflow directory)
- Any other directory deeper than the named project root

Why: the renamed project copy is the canonical session root. All
project conventions, INPUT_user paths, research_notebook captures,
and AI guidance are scoped to that directory. Rooting deeper than
that scopes the AI's view too narrowly and loses cross-subproject
context (and the AI guides at lower levels assume the session was
rooted above them). Rooting at `GIGANTIC/` is reserved for
framework-development sessions per §16.

### One chat session per subproject + a side channel for small questions

For productive project work:

- **One session per subproject** you're actively working in. A session
  focused on `phylonames/` is different from one focused on
  `genomesDB/` is different from one focused on `trees_species/` —
  each maintains its own context, convention reminders, and recent
  state.
- **Continue the same session over many compactions** until it
  becomes overly reactive, muddled, or slow. Compactions are
  lossless (per §9 the full transcript is captured), so a long
  session isn't a problem until it starts feeling like one.
- **When a session goes muddled, start a fresh one** at the same
  named `gigantic_project-*/` root, focused on the same subproject,
  and bring it back up to speed (read the relevant AI_GUIDEs, recent
  commits, etc.).
- **Keep a separate "small questions" session** for random or
  cross-cutting questions (e.g., "what does this convention mean?"
  or "is this NCBI accession a GCF or GCA?"). This keeps the
  subproject sessions focused on their actual work and prevents
  context pollution.

### What this prevents

- Sessions that try to hold every subproject's state in context and
  end up confused about which one they're operating on.
- Sessions that get derailed by one-off questions and lose their
  thread on the subproject work.
- Session captures (per §9) that mix multiple unrelated subprojects
  into a single transcript, making the lab-notebook record harder
  to grep later.
