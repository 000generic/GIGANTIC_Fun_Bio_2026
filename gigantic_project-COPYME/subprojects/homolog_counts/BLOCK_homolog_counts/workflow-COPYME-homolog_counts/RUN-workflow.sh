#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 20 | Purpose: Run homolog_counts pipeline (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC homolog_counts - BLOCK homolog_counts Pipeline
################################################################################
#
# PURPOSE:
# Produce per-species70 homolog count tables from upstream GIGANTIC subprojects
# (orthogroups/BLOCK_orthohmm, trees_gene_groups, trees_gene_families).
#
# USAGE:
#   bash RUN-workflow.sh
#
# Execution mode is read from START_HERE-user_config.yaml:
#   execution_mode: "local"  -> runs the pipeline here (current shell)
#   execution_mode: "slurm"  -> self-submits as a SLURM job, then re-enters
#                                this script on the compute node
#
# This unified pattern replaces the older two-file (RUN-workflow.sh +
# RUN-workflow.sbatch) approach.
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml:
#    - execution_mode ("local" or "slurm")
#    - inputs paths
#    - if slurm: slurm_account, slurm_qos
# 2. Verify upstream subprojects have populated their output_to_input/
#
# WHAT THIS DOES:
# 1. Optionally self-submits as a SLURM job (when execution_mode is "slurm")
# 2. Auto-creates the conda env aiG-homolog_counts-homolog_counts from
#    ai/conda_environment.yml on first run (mamba preferred; conda fallback)
# 3. Runs 8 NextFlow processes (001 first, then 002-004 counts in parallel,
#    then 006 short-header rewrites per count, then 005 run log)
# 4. Creates symlinks for downstream subprojects in output_to_input/BLOCK_homolog_counts/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC homolog_counts Pipeline"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Resolve script directory and cd into workflow root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# YAML config helper
# ============================================================================
# Reads top-level YAML keys via grep (no Python dependency). Returns value for
# key $1 or default $2 if missing.

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================
# Self-submits as a SLURM job so all work (conda env creation, NextFlow
# pipeline) runs on a compute node -- never on the login node.

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "16")
    SLURM_TIME=$(read_config "time_hours" "4")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=homolog_counts"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/homolog_counts-%j.log"

    if [ -n "${SLURM_ACCOUNT}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
    fi
    if [ -n "${SLURM_QOS}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"
    fi

    echo "Submitting with: sbatch ${SBATCH_ARGS}"
    sbatch ${SBATCH_ARGS} --wrap="bash $(realpath $0)"

    echo ""
    echo "Job submitted. Check slurm_logs/ for output."
    exit 0
fi

if [ -n "${SLURM_JOB_ID}" ]; then
    echo "Running inside SLURM job ${SLURM_JOB_ID}"
else
    echo "Execution mode: local"
fi
echo ""

# After this point, exit on any error
set -e

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# The environment is created automatically on first run from the yml spec
# colocated at ai/conda_environment.yml. mamba is preferred (much faster);
# conda is the fallback if mamba is not available.

ENV_NAME="aiG-homolog_counts-homolog_counts"
ENV_YML="ai/conda_environment.yml"

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo ""
    echo "On HPC (HiPerGator): module load conda"
    echo "Otherwise: install conda from https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create environment on-demand if it does not exist
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    echo ""
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        echo "Make sure you are running from a valid GIGANTIC workflow directory."
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
        CREATE_EXIT=$?
    else
        conda env create -f "${ENV_YML}" -y
        CREATE_EXIT=$?
    fi
    if [ $CREATE_EXIT -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to create conda environment '${ENV_NAME}' (exit code $CREATE_EXIT)"
        echo "Check the error messages above and verify the spec at: ${ENV_YML}"
        echo ""
        echo "If a partial env was left behind, remove it before retrying:"
        echo "  mamba env remove -n ${ENV_NAME} -y"
        exit 1
    fi
    echo ""
    echo "Environment '${ENV_NAME}' created successfully."
    echo ""
fi

# Activate the environment
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

# Ensure NextFlow is available (conda env or system module)
if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo ""
        echo "ERROR: NextFlow not available!"
        echo "  Install via conda env or load: module load nextflow"
        exit 1
    fi
    echo "Using NextFlow from system module"
else
    echo "NextFlow available"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# (Detailed input-path validation happens in main.nf at pipeline start.)

echo ""

# ============================================================================
# Run NextFlow Pipeline
# ============================================================================

echo "Running NextFlow pipeline..."
echo ""

RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# Universal GIGANTIC YAML->params pattern: pass the YAML directly via
# -params-file. NextFlow loads YAML natively; all keys (cpus, memory_gb,
# inputs.*, output.*, project.*, etc.) flow through automatically.

nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config \
    -params-file START_HERE-user_config.yaml

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directory
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks at the subproject root expose stable filenames to downstream
# subprojects: ../../output_to_input/BLOCK_homolog_counts/

echo ""
echo "Publishing outputs to output_to_input/..."

# Determine workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_homolog_counts"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -maxdepth 1 -type l -delete 2>/dev/null

ln -sf "../../BLOCK_homolog_counts/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/1_ai-species70_alphabetical_phylonames.tsv" \
    "${SUBPROJECT_SHARED_DIR}/species70_alphabetical_phylonames.tsv"
ln -sf "../../BLOCK_homolog_counts/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/2_ai-counts-orthogroups_orthohmm.tsv" \
    "${SUBPROJECT_SHARED_DIR}/counts-orthogroups_orthohmm.tsv"
ln -sf "../../BLOCK_homolog_counts/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/3_ai-counts-trees_gene_groups.tsv" \
    "${SUBPROJECT_SHARED_DIR}/counts-trees_gene_groups.tsv"
ln -sf "../../BLOCK_homolog_counts/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/4_ai-counts-trees_gene_families.tsv" \
    "${SUBPROJECT_SHARED_DIR}/counts-trees_gene_families.tsv"

echo "  Created symlinks in output_to_input/BLOCK_homolog_counts/"

echo ""
echo "========================================================================"
echo "SUCCESS! homolog_counts pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 8-output/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_homolog_counts/"
echo ""
echo "Next: Review count tables, then curate selected files into upload_to_server/"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
