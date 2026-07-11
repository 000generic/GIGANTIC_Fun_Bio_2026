# phylonames — GIGANTIC Phylogenetic Naming System

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 04 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
Purpose: User-facing description of the phylonames subproject — what it does,
         how to run STEP_1 and (optional) STEP_2, where its outputs go, and
         which subprojects consume them.
============================================================================ -->

## Where this fits

`phylonames` is the **first** subproject you run in any GIGANTIC project.
Its output (a TSV mapping `genus_species` → `phyloname` →
`phyloname_taxonid`) is the canonical species identifier used by every
downstream subproject in this `gigantic_project-*` tree.

- Parent project landing page: [`../../README.md`](../../README.md)
- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- This subproject's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)

---

## Purpose

The phylonames subproject provides a standardized naming system for species across GIGANTIC. It downloads the NCBI taxonomy database and generates phylogenetically-informative species identifiers that encode the complete taxonomic lineage.

**This subproject MUST run first** — all other GIGANTIC subprojects depend on phylonames. See [Outputs Shared Downstream](#outputs-shared-downstream-output_to_input) below for the full consumer list.

---

## Phyloname Formats

GIGANTIC uses two distinct phyloname formats. This distinction is **critical** throughout the platform:

### `phyloname` (Standard Format)
```
Kingdom_Phylum_Class_Order_Family_Genus_species
```
**Example**: `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens`

**Usage**:
- Species identification across all GIGANTIC outputs
- Column headers and table values in TSV files
- Data integration and lookups between subprojects
- **This is the most commonly used format**

### `phyloname_taxonid` (Extended Format)
```
Kingdom_Phylum_Class_Order_Family_Genus_species___taxonID
```
**Example**: `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606`

**Usage**:
- Renaming downloaded genomic data files (guarantees uniqueness)
- NCBI taxonomy database linkage
- Cases requiring absolute taxonomic precision
- Distinguishing subspecies or strains with identical names

### Consistency Rule

Throughout GIGANTIC code and documentation:
- Use `phyloname` when referring to the standard format (no taxon ID)
- Use `phyloname_taxonid` when referring to the extended format (with `___taxonID`)
- **Never use these terms interchangeably**

---

## Numbered Unknown Clades (Kingdom6555, Family1426, etc.)

### What Are Numbered Clades?

NCBI Taxonomy is **incomplete** and represents **one hypothesis** among many about phylogenetic relationships. When NCBI lacks data for a taxonomic level, GIGANTIC generates **numbered unknown clade identifiers**.

**Example**:
```
Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

Here, `Kingdom6555` and `Phylum6554` are **not NCBI assignments** - they are GIGANTIC's solution to fill gaps while preserving phylogenetic information.

### Why This Matters

**The numbering captures shared ancestry**: All species sharing the same "first named clade below" an unknown level get the same number. This groups related species together despite missing higher taxonomy.

**Example**: All choanoflagellates might share `Kingdom6555` and `Phylum6554` because they all have "Choanoflagellata" as their first named clade below those levels.

### CRITICAL LIMITATION: Clade Splitting Artifact

When a single unknown higher-level clade actually contains **multiple** lower-level clades, GIGANTIC's numbering will **split** the real clade into multiple numbered clades (one per each lower-level clade).

**Example Scenario**:
If one unknown Kingdom actually contains Phyla A, B, and C, GIGANTIC creates:
- `Kingdom1` (for species in Phylum A)
- `Kingdom2` (for species in Phylum B)
- `Kingdom3` (for species in Phylum C)

But in reality, all belong to the **SAME** unknown Kingdom.

**Impact on Analyses**:
- If your species set includes species from **only ONE** lower-level clade → **NO PROBLEM**
- If your species set includes species from **MULTIPLE** lower-level clades that share an unknown higher clade → **PROBLEM**: OCL (Origins, Conservation, Loss) analyses will cryptically fail to capture accurate evolutionary patterns

**Solution**: If you know the correct higher-level clade names from literature, use the **user-provided phylonames** feature in STEP_2 (see below).

---

## User-Provided Phylonames (Custom Taxonomy)

### Overview

GIGANTIC allows you to override NCBI-generated phylonames with your own taxonomy based on current literature or alternative phylogenetic hypotheses. This is handled in **STEP_2-apply_user_phylonames**, which runs after STEP_1.

### Configuration

In `STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/START_HERE-user_config.yaml`:

```yaml
project:
  # Path to your custom phylonames file
  user_phylonames: "INPUT_user/user_phylonames.tsv"

  # Whether to mark user clades as UNOFFICIAL (default: true)
  mark_unofficial: true
```

### Input Format

Create a TSV file with two columns:
```
genus_species	custom_phyloname
Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

### UNOFFICIAL Suffix

By default, clades that **DIFFER** from the NCBI-derived phyloname are marked with `UNOFFICIAL`:

```
NCBI output:    Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
User provides:  Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
Final output:   HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
```

Only `Holozoa` and `Choanozoa` get marked UNOFFICIAL because they replaced the numbered clades. `Choanoflagellata`, `Craspedida`, and `Salpingoecidae` remain unmarked because they match the NCBI-derived values.

**Why UNOFFICIAL?**
- Assigning a clade to a species is a **taxonomic DECISION**
- NCBI made their official decision
- When you override specific clades, **those overrides are "unofficial"**
- Clades that match NCBI's assignment remain official (unmarked)
- The UNOFFICIAL suffix maintains transparency about which assignments came from the user

**To disable** (if you want clean phylonames without any UNOFFICIAL markers):
```yaml
mark_unofficial: false
```

---

## Field Positions (0-indexed)

| Position | Level | Example |
|----------|-------|---------|
| [0] | Kingdom | Metazoa |
| [1] | Phylum | Mollusca |
| [2] | Class | Gastropoda |
| [3] | Order | Aplysiida |
| [4] | Family | Aplysiidae |
| [5] | Genus | Aplysia |
| [6:] | species | californica |

**Extracting genus_species from phyloname**:
```python
phyloname = 'Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica'
parts = phyloname.split( '_' )
genus = parts[ 5 ]
species = '_'.join( parts[ 6: ] )  # Handles multi-word species names
genus_species = genus + '_' + species  # Result: 'Aplysia_californica'
```

---

## Directory Structure

```
phylonames/
├── README.md                                # This file
├── AI_GUIDE.md                              # AI assistant guidance (subproject level)
│
├── RUN-update_upload_to_server.sh           # Subproject-level publisher (§38)
│
├── upload_to_server/                        # Single publish destination per §38
│                                            # (auto-populated; no per-STEP upload_to_server)
│
├── output_to_input/                         # Outputs for downstream subprojects (§2)
│   ├── STEP_1-generate_and_evaluate/
│   │   └── maps/
│   │       └── [project]_map-genus_species_X_phylonames.tsv  (symlink into STEP_1 OUTPUT_pipeline)
│   ├── STEP_2-apply_user_phylonames/
│   │   └── maps/
│   │       └── [project]_map-genus_species_X_phylonames.tsv  (symlink into STEP_2 OUTPUT_pipeline)
│   └── maps/                                # Convenience landing dir; the .tsv inside is a symlink
│       └── [project]_map-genus_species_X_phylonames.tsv      (symlink, updated to whichever STEP ran last)
│
│   (no per-subproject research_notebook/ — the single project-root one
│   at gigantic_project-COPYME/research_notebook/ serves all subprojects;
│   see conventions §1, §9, §25)
│
├── STEP_1-generate_and_evaluate/
│   ├── AI_GUIDE.md                          # STEP-level AI guide
│   │
│   └── workflow-COPYME-generate_phylonames/
│       ├── README.md                        # User-facing quick start
│       ├── RUN-workflow.sh                  # Unified driver — local or SLURM via execution_mode (§29)
│       ├── START_HERE-user_config.yaml      # Project name, execution_mode, slurm_account/qos, etc.
│       ├── upload_manifest.tsv              # Server publish manifest (§38, §39)
│       ├── INPUT_user/                      # Species list (auto-copied from project default if absent)
│       │   └── species_list_example.txt     # Example species list (template)
│       ├── OUTPUT_pipeline/                 # Generated phylonames and mappings (1-output .. 5-output)
│       └── ai/                              # Internal (don't touch by hand)
│           ├── AI_GUIDE.md
│           ├── main.nf
│           ├── nextflow.config
│           ├── conda_environment.yml        # env name: aiG-phylonames (auto-created on first run)
│           ├── logs/                        # Per-run audit logs (lab notebook)
│           ├── validation/                  # Validation outputs
│           └── scripts/
│               ├── 001_ai-bash-download_ncbi_taxonomy.sh
│               ├── 002_ai-python-generate_phylonames.py
│               ├── 003_ai-python-create_species_mapping.py
│               ├── 004_ai-python-generate_taxonomy_summary.py
│               └── 005_ai-python-write_run_log.py
│
└── STEP_2-apply_user_phylonames/
    ├── AI_GUIDE.md                          # STEP-level AI guide
    │
    └── workflow-COPYME-apply_user_phylonames/
        ├── README.md                        # User-facing quick start
        ├── RUN-workflow.sh                  # Unified driver (§29)
        ├── START_HERE-user_config.yaml      # Project name, user_phylonames path, mark_unofficial, etc.
        ├── upload_manifest.tsv              # Server publish manifest
        ├── INPUT_user/                      # User-provided phylonames input (staged from project INPUT_user/phylonames/)
        │   └── user_phylonames_example.tsv  # Example (copy to user_phylonames.tsv)
        ├── OUTPUT_pipeline/                 # Final mapping with user overrides (1-output .. 3-output)
        └── ai/                              # Internal (don't touch by hand)
            ├── AI_GUIDE.md
            ├── main.nf
            ├── nextflow.config
            ├── conda_environment.yml        # env name: aiG-phylonames (shared with STEP_1)
            ├── logs/
            ├── validation/
            └── scripts/
                ├── 001_ai-python-apply_user_phylonames.py
                ├── 002_ai-python-generate_taxonomy_summary.py
                └── 003_ai-python-write_run_log.py
```

**AI lab-notebook logs**: Each workflow run creates a timestamped log in
its own `ai/logs/` directory. This documents what the workflow did, when,
with what inputs, and what it produced. Captured AI chat transcripts live
in the single project-root sandbox at
`gigantic_project-COPYME/research_notebook/research_ai/sessions/` (see
conventions §1, §9, §25).

---

## Quick Start

### Environment (automatic)

There is **no separate environment setup step**. The conda env
`aiG-phylonames` is created automatically on the first run from
`ai/conda_environment.yml`, shared by STEP_1 and STEP_2. On HiPerGator
and similar HPC systems, `RUN-workflow.sh` runs `module load conda`
first; elsewhere it expects conda on `$PATH`.

### Step 1: Edit Your Species List

**Recommended (project-wide list)**: edit the project-level default
that all subprojects can reference:
```
../../INPUT_user/species_set/species_list.txt
```

**Override for this STEP_1 run only**: place a `species_list.txt`
inside the workflow's local `INPUT_user/`:
```
STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/INPUT_user/species_list.txt
```

Format (one species per line):
```
Homo_sapiens
Aplysia_californica
Octopus_bimaculoides
```

**Note**: `RUN-workflow.sh` checks the workflow's local
`INPUT_user/species_list.txt` first; if absent, it copies the project
default from `INPUT_user/species_set/species_list.txt` into the
workflow's `INPUT_user/` at runtime so each run archives its own
snapshot.

### Step 2: Edit Configuration (Optional)

Edit `STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/START_HERE-user_config.yaml` to set your project name:

```yaml
project:
  name: "my_project"  # Change this to your project name
```

### Step 3: Run STEP_1

```bash
cd STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames
bash RUN-workflow.sh
```

The unified driver runs locally or self-submits to SLURM based on
`execution_mode` in `START_HERE-user_config.yaml` (per §29). For SLURM,
also set `slurm.account` and `slurm.qos` in that YAML.

STEP_1 will:
1. Obtain the NCBI taxonomy snapshot per `ncbi_taxonomy.source_mode`
   (default `download_latest` downloads ~2GB; `supply_path` reuses an
   existing snapshot with no download; `download_version` fetches a dated
   archive — see [NCBI Taxonomy Snapshot Source](#ncbi-taxonomy-snapshot-source-and-versioning))
2. Generate phylonames for all NCBI species (~5-10 minutes)
3. Create your project-specific mapping file
4. Generate a taxonomy summary report

### Step 4: Review Output

Your mapping file will be at:
```
output_to_input/STEP_1-generate_and_evaluate/maps/[project_name]_map-genus_species_X_phylonames.tsv
```

Review the phylonames for your species. If all look correct, you are done - STEP_2 is optional.

If you need to override any phylonames (for example, to replace numbered unknown clades with names from the literature), proceed to STEP_2.

### Step 5: Run STEP_2 (optional — user phyloname overrides)

If you have custom phylonames to apply:

1. **Stage your overrides via the project-level INPUT_user arena**
   (canonical pattern). Put the real file in your sandbox under
   `gigantic_project-COPYME/research_notebook/research_user/` (the
   single project-root sandbox per §1), then symlink it into the
   project-level `INPUT_user/phylonames/` slot:
   ```bash
   cd ../../INPUT_user/phylonames
   ln -srf ../../research_notebook/research_user/<your_path>/user_phylonames.tsv user_phylonames.tsv
   ```
   See `../../INPUT_user/AI_GUIDE.md` for the full staging rationale.
   For quick exploratory runs you can also write the file directly into
   the workflow's local `INPUT_user/`:
   ```
   STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/INPUT_user/user_phylonames.tsv
   ```

2. Edit the STEP_2 config (project name must match STEP_1):
   ```
   STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/START_HERE-user_config.yaml
   ```

3. Run STEP_2:
   ```bash
   cd STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames
   bash RUN-workflow.sh
   ```
   The unified driver runs locally or self-submits to SLURM via
   `execution_mode` in the YAML config (§29).

STEP_2 will:
1. Apply your user-provided phylonames with UNOFFICIAL marking (if enabled)
2. Generate a taxonomy summary report for the final mapping
3. Update the convenience symlink at `output_to_input/maps/` to point at
   the STEP_2 mapping (so downstream subprojects pick up the
   user-overridden version automatically)

### Output

Your final mapping file (from whichever STEP you ran last) is available via the convenience symlink:
```
output_to_input/maps/[project_name]_map-genus_species_X_phylonames.tsv
```

---

## Input Format

**Species List** (`INPUT_user/species_list.txt`):
One species per line, formatted as `Genus_species`:
```
Homo_sapiens
Aplysia_californica
Octopus_bimaculoides
Mnemiopsis_leidyi
```

Lines starting with `#` are treated as comments and ignored.

---

## Output Files

### STEP_1: Generate and Evaluate

#### NCBI Taxonomy Database

**Location**: `OUTPUT_pipeline/1-output/`

| File | Description |
|------|-------------|
| `database-ncbi_taxonomy_YYYYMMDD_HHMMSS/` | Versioned NCBI taxonomy download |
| `database-ncbi_taxonomy_latest` | Symlink to most recent download |

#### Master Phylonames Database

**Location**: `OUTPUT_pipeline/2-output/`

| File | Description |
|------|-------------|
| `phylonames` | All phylonames, one per line (standard format) |
| `phylonames_taxonid` | All phylonames with taxon ID (extended format) |
| `map-phyloname_X_ncbi_taxonomy_info.tsv` | Full mapping with all NCBI fields |
| `failed-entries.txt` | NCBI entries that couldn't be processed |
| `generation_metadata.txt` | Timestamp, counts, script version |

#### Project-Specific Mapping

**Location**: `OUTPUT_pipeline/3-output/`

| File | Description |
|------|-------------|
| `[project]_map-genus_species_X_phylonames.tsv` | Your species mapped to phylonames |

**Format** (tab-separated, 5 columns; identical shape to STEP_2's
output so downstream consumers see one schema regardless of which STEP
last produced the mapping):

1. `genus_species` — `Genus_species` or `Genus_species_subspecies`
2. `phyloname` — `Kingdom_Phylum_Class_Order_Family_Genus_species`
3. `phyloname_taxonid` — phyloname with NCBI taxon ID suffix
4. `source` — always `NCBI` for STEP_1 (STEP_2 may set `USER` for user-overridden rows)
5. `original_ncbi_phyloname` — same as `phyloname` for STEP_1 (STEP_2 preserves the original NCBI value when an override is applied)

Example rows (header line uses self-documenting parenthetical column
descriptions per gigantic_conventions §34 — abbreviated here for
readability):

```
genus_species	phyloname	phyloname_taxonid	source	original_ncbi_phyloname
Homo_sapiens	Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens	Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606	NCBI	Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
Aplysia_californica	Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica	Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica___6500	NCBI	Metazoa_Mollusca_Gastropoda_Aplysiida_Aplysiidae_Aplysia_californica
```

#### Taxonomy Summary

**Location**: `OUTPUT_pipeline/4-output/`

| File | Description |
|------|-------------|
| `taxonomy_summary.tsv` | Summary of taxonomic distribution across your species |

### STEP_2: Apply User Phylonames (Optional)

#### Final Mapping with Overrides

**Location**: `OUTPUT_pipeline/1-output/`

| File | Description |
|------|-------------|
| `final_project_mapping.tsv` | Species mapping with user phylonames applied |
| `unofficial_clades_report.tsv` | Report of which clades were marked UNOFFICIAL |

#### Taxonomy Summary

**Location**: `OUTPUT_pipeline/2-output/`

| File | Description |
|------|-------------|
| `taxonomy_summary.tsv` | Summary of taxonomic distribution (reflecting user overrides) |

---

## Scripts

### STEP_1 Scripts (001-005)

| Script | Description |
|--------|-------------|
| `001_ai-bash-download_ncbi_taxonomy.sh` | Downloads and extracts NCBI taxonomy database |
| `002_ai-python-generate_phylonames.py` | Generates phylonames for all NCBI species |
| `003_ai-python-create_species_mapping.py` | Creates project-specific genus_species to phyloname mapping |
| `004_ai-python-generate_taxonomy_summary.py` | Generates taxonomy summary report |
| `005_ai-python-write_run_log.py` | Writes timestamped run log for reproducibility |

### STEP_2 Scripts (001-003)

| Script | Description |
|--------|-------------|
| `001_ai-python-apply_user_phylonames.py` | Applies user-provided phyloname overrides with UNOFFICIAL marking |
| `002_ai-python-generate_taxonomy_summary.py` | Generates taxonomy summary reflecting user overrides |
| `003_ai-python-write_run_log.py` | Writes timestamped run log for reproducibility |

---

## Outputs Shared Downstream (`output_to_input/`)

Other GIGANTIC subprojects reference phylonames via the convenience symlink:
```
phylonames/output_to_input/maps/[project]_map-genus_species_X_phylonames.tsv
```

The `maps/` symlink points to either STEP_1 or STEP_2 output depending on which was run last:
- If only STEP_1 was run: `maps/` points to `STEP_1-generate_and_evaluate/maps/`
- If STEP_2 was also run: `maps/` points to `STEP_2-apply_user_phylonames/maps/`

**Dependent subprojects**:
- **genomesDB** - Uses phylonames for proteome file naming
- **trees_species** - Uses phylonames for clade definitions
- **trees_gene_families** - Uses phylonames for species identification
- **orthogroups** - Uses phylonames for species tracking
- **All other subprojects** - Reference species by phyloname

---

## NCBI Taxonomy Snapshot Source (and Versioning)

GIGANTIC fills gaps in NCBI taxonomy with **numbered unknown clades**
(e.g., `Kingdom6555`). Those numbers — and therefore the phylonames assigned
to your species — depend on the **exact NCBI taxonomy snapshot** used.
**Re-running against a different snapshot can change assigned phylonames**,
which would silently break every downstream subproject that already keyed on
the old phyloname. Choosing and pinning the snapshot is therefore a
reproducibility decision, controlled by `ncbi_taxonomy.source_mode` in STEP_1's
`START_HERE-user_config.yaml`:

| `source_mode` | What it does | When to use |
|---|---|---|
| `download_latest` *(default)* | Downloads the current `new_taxdump` release from NCBI | First run of a new project |
| `supply_path` | Reuses an existing snapshot directory (containing `rankedlineage.dmp`) via `taxonomy_path` — **no download** | Reproducible re-runs; pin to a fixed snapshot |
| `download_version` | Downloads a specific dated archive (`new_taxdump_YYYY-MM-DD.zip`) via `download_version` | Reproducible without keeping a local copy |

Downloaded snapshots are stored in a versioned directory
(`database-ncbi_taxonomy_YYYYMMDD_HHMMSS/`), and a `database-ncbi_taxonomy_latest`
symlink always points at the snapshot in use (downloaded or supplied).

**Why pin a snapshot?**
- NCBI regularly adds species and corrects taxonomy, so "latest" moves over time
- Pinning (`supply_path` / `download_version`) makes re-runs reproduce the same
  phylonames and numbered clades exactly
- You always know which taxonomy version generated your results (recorded in the
  snapshot's `download_metadata.txt`)

---

## Sharing Data via GIGANTIC Server

To share outputs with collaborators (per §38):

1. **Edit the per-workflow manifests** if you want to change what publishes:
   - `STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/upload_manifest.tsv`
   - `STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/upload_manifest.tsv`
2. **Run the subproject-level publisher** (single command):
   ```bash
   bash RUN-update_upload_to_server.sh
   ```
   This is a thin wrapper around the shared helper at
   `gigantic_project-COPYME/server/ai/update_upload_to_server.py`. It
   walks both STEPs' canonical `workflow-RUN_*/` dirs, reads their
   `upload_manifest.tsv`, and assembles
   `phylonames/upload_to_server/STEP_<N>-<name>/workflow-RUN_<K>-<name>/<N>-output/<file>`
   as symlinks. The data server then reads this directory.

```bash
# Preview what would be published
bash RUN-update_upload_to_server.sh --dry-run

# Actually publish
bash RUN-update_upload_to_server.sh
```

---

## Dependencies

All dependencies are provided by the `aiG-phylonames` conda environment,
shared by STEP_1 and STEP_2. It is **created automatically on first run**
by `RUN-workflow.sh` from `ai/conda_environment.yml`; you do not need
to set anything up by hand.

**Environment provides:**
- Python 3.9+ (standard library only — Python scripts have no external pip deps)
- NextFlow ≥23, <26 (pinned per project conventions §gconv)
- wget (for the NCBI taxonomy download in STEP_1)

On HPC systems, `RUN-workflow.sh` runs `module load conda` automatically
before checking for the env; elsewhere it expects `conda` on `$PATH`.

---

## Notes

- The NCBI taxonomy database is ~2GB compressed, ~1.9GB extracted
- Full phyloname generation takes ~5-10 minutes
- Generated files are large (~250MB for all phylonames, ~700MB for full mapping)
- For most projects, you only need the small project-specific mapping file
- The rankedlineage.dmp file is the primary data source for phyloname generation
- STEP_2 is optional - only needed when you want to override NCBI-derived phylonames with custom taxonomy

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
