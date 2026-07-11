# AI Guide: Phylonames Workflow (STEP_1)

**For AI Assistants**: This guide covers STEP_1 workflow execution. For concepts (numbered clades, user phylonames, 2-STEP architecture), see `../../../AI_GUIDE.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE.md` (project root).

**Location**: `gigantic_project-*/subprojects/phylonames/STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Workflow Naming Convention

GIGANTIC uses a **COPYME/RUN naming system** for workflows:

| Type | Naming Pattern | Description |
|------|----------------|-------------|
| **COPYME** (template) | `workflow-COPYME-[name]` | The template workflow - NOT numbered. Only ONE COPYME per workflow type. |
| **RUN** (instance) | `workflow-RUN_XX-[name]` | Numbered copies for actual runs. Each run gets its own directory. |

**Examples:**
- `workflow-COPYME-generate_phylonames` - The template (this directory)
- `workflow-RUN_01-generate_phylonames` - First run instance
- `workflow-RUN_02-generate_phylonames` - Second run instance

**To create a new run:**
```bash
# From the STEP_1 directory (STEP_1-generate_and_evaluate/)
cp -r workflow-COPYME-generate_phylonames workflow-RUN_01-generate_phylonames
cd workflow-RUN_01-generate_phylonames
# Edit config, add inputs, then run
```

**Key Principle**: COPYME stays clean as the template. All actual work happens in RUN_XX directories.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE.md` (project root) |
| Phylonames concepts | `../../../AI_GUIDE.md` |
| Running the STEP_1 workflow | This file |

---

## Workflow Directory Structure

```
workflow-COPYME-generate_phylonames/
│
├── README.md                    # User-facing quick start
├── RUN-workflow.sh              # Unified driver: bash RUN-workflow.sh
│                                # (self-submits to SLURM if execution_mode: slurm; §29)
├── START_HERE-user_config.yaml  # Project name + execution_mode + SLURM options
├── upload_manifest.tsv          # Server publish manifest (§38, §39)
│
├── INPUT_user/                  # Species list resolved at runtime (see override design below)
│   └── species_list.txt         # Species to process (override or auto-copied default)
│
├── OUTPUT_pipeline/             # All outputs
│   ├── 1-output/                # NCBI taxonomy database (versioned dir + 'latest' symlink)
│   ├── 2-output/                # Master phylonames for all NCBI species (phylonames, phylonames_taxonid, NCBI info mapping)
│   ├── 3-output/                # Project-specific mapping ([project]_map-genus_species_X_phylonames.tsv)
│   └── 4-output/                # Taxonomy summary (Markdown + HTML)
│
└── ai/                          # Internal — users don't touch by hand
    ├── AI_GUIDE.md              # THIS FILE
    ├── main.nf                  # NextFlow workflow definition
    ├── nextflow.config          # NextFlow config (params, retry, etc.)
    ├── conda_environment.yml    # env name: aiG-phylonames (auto-created on first run)
    ├── logs/                    # Per-run audit logs (lab notebook)
    ├── validation/              # Validation outputs (created on run)
    └── scripts/
        ├── 001_ai-bash-download_ncbi_taxonomy.sh
        ├── 002_ai-python-generate_phylonames.py
        ├── 003_ai-python-create_species_mapping.py
        ├── 004_ai-python-generate_taxonomy_summary.py
        └── 005_ai-python-write_run_log.py
```

---

## User Workflow

### Step 1: Add Species

**Default**: Edit project-wide species list (used by all workflows):
```bash
# From workflow directory
nano ../../../../../INPUT_user/species_set/species_list.txt
```

**Override**: To use a different species set for this workflow only, place a `species_list.txt` in this workflow's `INPUT_user/`:
```bash
nano INPUT_user/species_list.txt
```

**Priority**: `RUN-workflow.sh` checks workflow `INPUT_user/species_list.txt` first (override). If not present, it copies the project-level default.

**Format**:
```
# Comments start with #
Homo_sapiens
Aplysia_californica
Octopus_bimaculoides
```

### Step 2: Set Project Name

Edit `START_HERE-user_config.yaml`:
```yaml
project:
  name: "my_project"  # Change this
```

### Step 3: Run

**Local** (default):
```bash
bash RUN-workflow.sh
```

**SLURM**: Edit `START_HERE-user_config.yaml`, set `execution_mode: "slurm"` and
fill in `slurm_account` / `slurm_qos`, then:
```bash
bash RUN-workflow.sh   # self-submits to SLURM
```

---

## SLURM Execution Details

When `execution_mode: "slurm"`, `RUN-workflow.sh` self-submits to SLURM by
reading these keys from `START_HERE-user_config.yaml`:

| YAML key | Default | Notes |
|----------|---------|-------|
| `slurm_account` | `your_account` | **Must edit** |
| `slurm_qos` | `your_qos` | **Must edit** |
| `cpus` | `2` | NextFlow JVM concurrency |
| `memory_gb` | `8` | Honor HiPerGator 7.5 GB/CPU rule if scaling up |
| `time_hours` | `2` | First run ~15min, subsequent <1min |

**Check job status**: `squeue -u $USER`

**View logs**: `cat slurm_logs/phylonames_STEP_1-*.log`

---

## Expected Runtime

| Scenario | Duration |
|----------|----------|
| First run (download + generate) | ~15 minutes |
| Subsequent runs (mapping only) | < 1 minute |

---

## Output Files

### OUTPUT_pipeline/ Contents

| Directory | Contents |
|-----------|----------|
| `1-output/` | NCBI taxonomy database (~2GB) |
| `2-output/phylonames` | All NCBI phylonames (~2.5M lines) |
| `2-output/phylonames_taxonid` | All phylonames with taxon IDs |
| `2-output/map-phyloname_X_ncbi_taxonomy_info.tsv` | Complete NCBI mapping |
| `3-output/[project]_map-genus_species_X_phylonames.tsv` | **Your project mapping** |
| `4-output/[project]_taxonomy_summary.md` | Taxonomy summary (Markdown) |
| `4-output/[project]_taxonomy_summary.html` | Taxonomy summary (HTML) |

### Downstream Location

```
../../output_to_input/STEP_1-generate_and_evaluate/maps/[project]_map-genus_species_X_phylonames.tsv
```

This is the canonical STEP_1 output location. A convenience symlink also exists at:

```
../../output_to_input/maps/[project]_map-genus_species_X_phylonames.tsv
```

This is what other subprojects read.

---

## Verification Commands

```bash
# Did species list copy from INPUT_user?
head INPUT_user/species_list.txt

# Did NCBI download complete?
ls -lh OUTPUT_pipeline/1-output/

# Did master phylonames generate?
wc -l OUTPUT_pipeline/2-output/phylonames

# Did project mapping create?
head OUTPUT_pipeline/3-output/*_map-genus_species_X_phylonames.tsv

# Did taxonomy summary generate?
ls OUTPUT_pipeline/4-output/

# Is symlink in place at STEP_1 location?
ls -la ../../output_to_input/STEP_1-generate_and_evaluate/maps/

# Is convenience symlink in place?
ls -la ../../output_to_input/maps/
```

---

## Troubleshooting

### NOTINNCBI Species in Output

Species not found in NCBI taxonomy are **never dropped**. They are included in the
output with NOTINNCBI placeholder phylonames:

```
Chromosphaera_perkinsii  NOTINNCBI_NOTINNCBI_NOTINNCBI_NOTINNCBI_NOTINNCBI_Chromosphaera_perkinsii  NOTINNCBI_...___0
```

**What to do**:
1. **Check spelling**: `Homo_sapiens` not `Homo sapeins` (use underscore, not space)
2. **Check NCBI**: The species may use a different name (check ncbi.nlm.nih.gov/taxonomy)
3. **Run STEP_2**: Create user phylonames with proper taxonomy and run the STEP_2 workflow
   to apply overrides on top of this STEP_1 output

**Diagnose**:
```bash
# Show your species list
cat INPUT_user/species_list.txt

# Check for NOTINNCBI entries in output (should match input species count)
grep "NOTINNCBI" OUTPUT_pipeline/3-output/*_map*.tsv

# Count lines in output (should match input species count)
wc -l OUTPUT_pipeline/3-output/*_map*.tsv
```

### "Download failed"

**Causes**: Network issue, firewall, NCBI maintenance

**Solutions**:
```bash
# Test connectivity
ping google.com
curl -I ftp.ncbi.nlm.nih.gov

# Try again (often resolves itself)
bash RUN-workflow.sh
```

### "No database directory"

**Cause**: Script 001 didn't complete

**Solution**: Run download first:
```bash
bash ai/scripts/001_ai-bash-download_ncbi_taxonomy.sh
```

### "Permission denied"

**Solution**:
```bash
chmod +x RUN-workflow.sh
chmod +x ai/scripts/*.sh
```

### SLURM job hangs at "Running NextFlow pipeline..."

**Cause**: Insufficient resource allocation. NextFlow's JVM can hang indefinitely on SLURM compute nodes when allocated too few CPUs or too little RAM (e.g., 2 CPUs / 8 GB). The same workflow runs fine locally because the login node has ample resources.

**Solution**: Scale up `cpus` and `memory_gb` in `START_HERE-user_config.yaml` together, honoring the HiPerGator rule of ~7.5 GB RAM per CPU (e.g., 10 CPUs / 75 GB). On other HPC systems, check your cluster's RAM-per-CPU ratio and adjust accordingly.

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-workflow.sh
```

---

## Script Pipeline

| Script | Does | Creates |
|--------|------|---------|
| 001 | Obtains NCBI taxonomy snapshot per `ncbi_taxonomy.source_mode` (`download_latest` / `supply_path` / `download_version`) | `database-ncbi_taxonomy_latest` (+ snapshot dir) |
| 002 | Generates ALL phylonames | `2-output/phylonames`, `2-output/phylonames_taxonid` |
| 003 | Creates project mapping | `3-output/[project]_map-*.tsv` |
| 004 | Generates taxonomy summary | `4-output/[project]_taxonomy_summary.md/.html` |
| 005 | Writes run log | Research notebook log entry |

**Reproducibility note (script 001):** GIGANTIC numbered clades (`Kingdom6555`,
etc.) depend on the exact NCBI snapshot. For reproducible re-runs, set
`ncbi_taxonomy.source_mode: "supply_path"` (reuse a fixed snapshot dir
containing `rankedlineage.dmp`) or `"download_version"` (a dated archive) in
`START_HERE-user_config.yaml`. The default `download_latest` always fetches the
current release, which moves over time.

---

## Manual Execution (for debugging)

```bash
cd workflow-COPYME-generate_phylonames

# Run scripts individually
# Script 001 now takes flags (normally supplied by main.nf from the yaml params):
bash ai/scripts/001_ai-bash-download_ncbi_taxonomy.sh \
    --source-mode download_latest \
    --workflow-dir .
# (or: --source-mode supply_path --taxonomy-path /path/to/snapshot --workflow-dir .)
python3 ai/scripts/002_ai-python-generate_phylonames.py
python3 ai/scripts/003_ai-python-create_species_mapping.py \
    --species-list INPUT_user/species_list.txt \
    --output OUTPUT_pipeline/3-output/my_project_map.tsv
```

---

## After Successful Run

1. **Verify output**: `head ../../output_to_input/maps/*_map*.tsv`
2. **Review taxonomy summary**: Check `OUTPUT_pipeline/4-output/` for NOTINNCBI species or numbered clades that need attention
3. **If overrides needed**: Run **STEP_2** to apply user-defined phylonames on top of STEP_1 output
4. **If no overrides needed**: Other subprojects can read directly from `../../output_to_input/maps/`
5. **Next subproject**: Guide user to `genomesDB`
