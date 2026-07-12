#!/bin/bash
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Run ambiguous_nodes_X_annogroups projection (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC integrator - BLOCK_ambiguous_nodes_X_annogroups
################################################################################
#
# PURPOSE:
# Collapse the annogroups species-tree DECONVOLUTION (per-clade member-protein
# counts) to ONLY the AMBIGUOUS NODES (clades present in some but not all
# structures), in three structure scopes (one / some / all), for each annotation
# source (pfam, go, panther). Pure column projection — no count recomputed.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml:
#    - run_label, species_set_name
#    - annotation_sources ("all" or a subset like [ pfam ])
#    - structure_scopes.{all, one, some}  (one_structure_id; some structure_ids
#      and/or selected_structures_file)
#    - execution_mode ("local" or "slurm"); if slurm, slurm_account + slurm_qos
# 2. Verify the upstream annogroups output_to_input is populated:
#    - annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/
#        4_ai-<source>-annogroup_tree_counts-all_structures.tsv
#        annogroup_tree_counts_per_structure/4_ai-<source>-annogroup_tree_counts-structure_NNN.tsv
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-BLOCK conda env from ai/conda_environment.yml
# 2. Runs the pipeline:
#    001: resolve ambiguous nodes + structure scopes (1-output)
#    002: project annogroups onto ambiguous-node columns, per scope (2-output)
#    003: validate results (strict fail-fast)
#    004: write run log
# 3. Creates output_to_input symlinks for downstream consumers
#
# OUTPUT:
#   OUTPUT_pipeline/1-output/<source>/   ambiguous-node registry + structure sets
#   OUTPUT_pipeline/2-output/<source>/{all,one,some}/   projected tables
#   OUTPUT_pipeline/3-output/            validation report
#   ../../output_to_input/BLOCK_ambiguous_nodes_X_annogroups/<run_label>/
################################################################################

echo "========================================================================"
echo "GIGANTIC integrator - ambiguous_nodes_X_annogroups"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read flat YAML keys (no Python dependency)
# ============================================================================
read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")
RUN_LABEL=$(read_config "run_label" "")
SPECIES_SET=$(read_config "species_set_name" "")

# Workflow directory name (used below to build output_to_input symlink targets).
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# ============================================================================
# SLURM self-submission (if execution_mode=slurm and not already in a job)
# ============================================================================
if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""
    SLURM_CPUS=$(read_config "cpus" "2")
    SLURM_MEM=$(read_config "memory_gb" "16")
    SLURM_TIME=$(read_config "time_hours" "2")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs
    SBATCH_ARGS="--job-name=integrator_ambiguous_nodes_X_annogroups"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/integrator_ambiguous_nodes_X_annogroups-%j.log"
    [ -n "${SLURM_ACCOUNT}" ] && SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
    [ -n "${SLURM_QOS}" ] && SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"

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

# ============================================================================
# Activate conda env (on-demand creation)
# ============================================================================
ENV_NAME="aiG-integrator-ambiguous_nodes_X_annogroups"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y; CREATE_EXIT=$?
    else
        conda env create -f "${ENV_YML}" -y; CREATE_EXIT=$?
    fi
    if [ $CREATE_EXIT -ne 0 ]; then
        echo "ERROR: Failed to create conda environment '${ENV_NAME}' (exit ${CREATE_EXIT})"
        echo "If a partial env was left behind: mamba env remove -n ${ENV_NAME} -y"
        exit 1
    fi
    echo "Environment '${ENV_NAME}' created."
    echo ""
fi

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available! Install in env or 'module load nextflow'."
        exit 1
    fi
    echo "Using NextFlow from system module"
else
    echo "NextFlow available"
fi
echo ""

# ============================================================================
# Validate prerequisites
# ============================================================================
echo "Validating prerequisites..."
[ -f "START_HERE-user_config.yaml" ] || { echo "ERROR: START_HERE-user_config.yaml not found!"; exit 1; }
echo "  [OK] Configuration file found"
echo ""
echo "Configuration:"
echo "  Run Label   : ${RUN_LABEL}"
echo "  Species Set : ${SPECIES_SET}"
echo ""

INTEGRATOR_AI="${SCRIPT_DIR}/../../ai"
mkdir -p OUTPUT_pipeline
python3 "${INTEGRATOR_AI}/write_workflow_run_timestamp.py" --output-pipeline OUTPUT_pipeline

# ============================================================================
# Run NextFlow pipeline
# ============================================================================
echo "Running NextFlow pipeline..."
echo ""

RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

PARALLELISM_MODE=$(read_config "parallelism_mode" "local")
case "${PARALLELISM_MODE}" in
    slurm) PROFILE_FLAG="-profile standard" ;;
    local) PROFILE_FLAG="-profile local" ;;
    *)
        echo "ERROR: unknown parallelism_mode: '${PARALLELISM_MODE}' (valid: 'slurm' | 'local')"
        exit 1
        ;;
esac
echo "  parallelism_mode: ${PARALLELISM_MODE} (nextflow ${PROFILE_FLAG})"

# Universal GIGANTIC YAML->params pattern: pass the YAML directly via
# -params-file (NextFlow loads it natively, populating params.X.Y.Z).
nextflow run ai/main.nf ${RESUME_FLAG} ${PROFILE_FLAG} \
    -params-file START_HERE-user_config.yaml

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input (downstream consumers)
# ============================================================================
# Real files live in OUTPUT_pipeline/{1,2}-output/. Mirror them (minus the
# numeric N-output prefix) under a run_label-namespaced subdir so downstream
# paths are stable: <run_label>/<source>/<registry files> and
# <run_label>/<source>/<scope>/<projected table>.
echo ""
echo "Creating symlinks for downstream consumers..."

SHARED_DIR="../../output_to_input/BLOCK_ambiguous_nodes_X_annogroups/${RUN_LABEL}"
find "${SHARED_DIR}" -mindepth 1 -delete 2>/dev/null || true
mkdir -p "${SHARED_DIR}"
python3 "${INTEGRATOR_AI}/link_stable_output_to_input_symlinks.py" \
    --output-pipeline OUTPUT_pipeline \
    --shared-dir "${SHARED_DIR}" \
    --workflow-relative "../../../BLOCK_ambiguous_nodes_X_annogroups/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline" \
    --preserve-subdirs --strip-stage-prefix
SYMLINK_COUNT=$(find "${SHARED_DIR}" -type l 2>/dev/null | wc -l)
echo "  output_to_input/BLOCK_ambiguous_nodes_X_annogroups/${RUN_LABEL}/ -> ${SYMLINK_COUNT} symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Projection complete."
echo "  Run Label: ${RUN_LABEL}"
echo "  Downstream: ../../output_to_input/BLOCK_ambiguous_nodes_X_annogroups/${RUN_LABEL}/"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
