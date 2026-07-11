#!/bin/bash
# AI: Claude (Cursor) | Opus 4.8 | 2026 July 08 | Purpose: Run orthogroups_X_all_annotations integration (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC integrator - BLOCK_orthogroups_X_all_annotations
################################################################################
#
# PURPOSE:
# Build ONE table with one row per OrthoHMM orthogroup:
#   Orthogroup_ID | Sequence_IDs | Member_Sequence_Count | Is_Singleton
#   | for each of Pfam/GO/PANTHER/Gene_Families/Gene_Groups/Dark_Proteome/Hotspots:
#       <Type>_Species_Count | <Type>_Sequence_Count | <Type>_Identifiers | <Type>_Names
#   | species-tree deconvolution columns (per-clade / per-species member counts)
#     across structures 001, 003, 031, 032.
# Structure-independent — a handful of singleton processes, no per-structure fan-out.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml:
#    - run_label, species_set_name, hmm_annotation_sources
#    - inputs.deconvolution_structures (default: 001, 003, 031, 032)
#    - execution_mode ("local" or "slurm"); if slurm, slurm_account + slurm_qos
#    - the seven annotation-source input paths + clade_species_mappings
# 2. Verify upstream output_to_input/ are populated (see START_HERE-user_config.yaml
#    for the full list of source paths for each of the seven annotation types).
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-BLOCK conda env from ai/conda_environment.yml
# 2. Runs the pipeline:
#    001: build the all-annotations table       (1-output)
#    002: validate results (strict fail-fast)   (2-output)
#    003: write run log
# 3. Creates output_to_input symlinks for downstream consumers
#
# OUTPUT:
#   OUTPUT_pipeline/1-output/   the all-annotations table
#   OUTPUT_pipeline/2-output/   validation report
#   ../../output_to_input/BLOCK_orthogroups_X_all_annotations/<run_label>/
################################################################################

echo "========================================================================"
echo "GIGANTIC integrator - orthogroups_X_all_annotations"
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
    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "64")
    SLURM_TIME=$(read_config "time_hours" "8")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs
    SBATCH_ARGS="--job-name=integrator_orthogroups_X_all_annotations"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/integrator_orthogroups_X_all_annotations-%j.log"
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
ENV_NAME="aiG-integrator-orthogroups_X_all_annotations"
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
# Real files live in OUTPUT_pipeline/{1,2}-output/. Expose the headline table
# (+ the validation report) under a run_label-namespaced subdir so downstream
# paths are stable.
echo ""
echo "Creating symlinks for downstream consumers..."

SHARED_DIR="../../output_to_input/BLOCK_orthogroups_X_all_annotations/${RUN_LABEL}"
mkdir -p "${SHARED_DIR}"

# Remove stale table symlinks from previous runs
for old in "${SHARED_DIR}"/*.tsv; do
    [ -L "$old" ] && rm -f "$old"
done

declare -A TABLE_MAP=(
    ["1-output/1_ai-orthogroups_X_all_annotations.tsv"]="1_ai-orthogroups_X_all_annotations.tsv"
    ["2-output/2_ai-validation_report.txt"]="2_ai-validation_report.txt"
)
for src_rel in "${!TABLE_MAP[@]}"; do
    clean_name="${TABLE_MAP[$src_rel]}"
    if [ -f "OUTPUT_pipeline/${src_rel}" ]; then
        ln -sf "../../../BLOCK_orthogroups_X_all_annotations/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/${src_rel}" \
            "${SHARED_DIR}/${clean_name}"
    fi
done

SYMLINK_COUNT=$(find "${SHARED_DIR}" -type l 2>/dev/null | wc -l)
echo "  output_to_input/BLOCK_orthogroups_X_all_annotations/${RUN_LABEL}/ -> ${SYMLINK_COUNT} symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Integration complete."
echo "  Run Label: ${RUN_LABEL}"
echo "  Downstream: ../../output_to_input/BLOCK_orthogroups_X_all_annotations/${RUN_LABEL}/"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
