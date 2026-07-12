#!/bin/bash
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: Run species_X_all_annotations integration (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC integrator - BLOCK_species_X_all_annotations
################################################################################
#
# PURPOSE:
# Build, per species, a proteome annotation table — one row per protein
# sequence, with every per-gene feature GIGANTIC produces joined onto the
# genomesDB proteome spine. Structure-invariant features are joined once
# (Phase 1 -> 1-output/_shared/); the orthogroup + annogroup OCL columns are
# added per species-tree structure (Phase 2 -> 2-output/<structure>/) for the
# structures listed in START_HERE-user_config.yaml ("all" or a list).
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml:
#    - run_label, species_set_name
#    - structures ("all" or e.g. [structure_001, structure_003, structure_032, structure_033])
#    - annogroup_sources, orthogroups_ocl_run_label, annogroup_ocl_run_label
#    - execution_mode ("local" or "slurm"); if slurm, slurm_account + slurm_qos
#    - input paths (inputs.*)
# 2. Verify upstream output_to_input/ are populated (see ai/AI_GUIDE.md).
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-BLOCK conda env from ai/conda_environment.yml
# 2. Runs the pipeline:
#    000: resolve the structure set (+ fail-fast verify OCL inputs)
#    001: build per-species invariant base tables       (1-output/_shared)
#    002: append OCL columns per structure (fan-out)     (2-output/<structure>)
#    003: validate results (strict fail-fast)            (3-output)
#    004: write run log                                  (ai/logs)
# 3. Creates output_to_input symlinks for downstream consumers
#
# OUTPUT:
#   OUTPUT_pipeline/1-output/_shared/   per-species invariant base tables + availability summary
#   OUTPUT_pipeline/2-output/<structure>/  full wide per-species tables (base + OCL) per structure
#   OUTPUT_pipeline/3-output/           validation report
#   ../../output_to_input/BLOCK_species_X_all_annotations/<run_label>/
################################################################################

echo "========================================================================"
echo "GIGANTIC integrator - species_X_all_annotations"
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
    SLURM_CPUS=$(read_config "cpus" "8")
    SLURM_MEM=$(read_config "memory_gb" "64")
    SLURM_TIME=$(read_config "time_hours" "12")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs
    SBATCH_ARGS="--job-name=integrator_species_X_all_annotations"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/integrator_species_X_all_annotations-%j.log"
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
ENV_NAME="aiG-integrator-species_X_all_annotations"
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
# Real files live in OUTPUT_pipeline/{1,2}-output/. Expose the per-species base
# tables (_shared) and each materialized structure's wide tables under a
# run_label-namespaced subdir, as DIRECTORY symlinks (one per structure + _shared).
echo ""
echo "Creating symlinks for downstream consumers..."

SHARED_DIR="../../output_to_input/BLOCK_species_X_all_annotations/${RUN_LABEL}"
find "${SHARED_DIR}" -mindepth 1 -delete 2>/dev/null || true
mkdir -p "${SHARED_DIR}"
python3 "${INTEGRATOR_AI}/link_stable_output_to_input_symlinks.py" \
    --output-pipeline OUTPUT_pipeline \
    --shared-dir "${SHARED_DIR}" \
    --workflow-relative "../../../BLOCK_species_X_all_annotations/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline" \
    --preserve-subdirs --strip-stage-prefix
SYMLINK_COUNT=$(find "${SHARED_DIR}" -type l 2>/dev/null | wc -l)
echo "  output_to_input/BLOCK_species_X_all_annotations/${RUN_LABEL}/ -> ${SYMLINK_COUNT} symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Integration complete."
echo "  Run Label: ${RUN_LABEL}"
echo "  Downstream: ../../output_to_input/BLOCK_species_X_all_annotations/${RUN_LABEL}/"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
