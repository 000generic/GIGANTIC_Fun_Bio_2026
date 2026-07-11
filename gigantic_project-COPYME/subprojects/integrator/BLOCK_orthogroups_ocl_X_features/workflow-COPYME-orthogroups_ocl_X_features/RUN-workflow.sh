#!/bin/bash
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Run orthogroups_ocl_X_features integration (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC integrator - BLOCK_orthogroups_ocl_X_features
################################################################################
#
# PURPOSE:
# Integrate OCL orthogroup analysis (per phylogenetic species-tree structure)
# with dark proteome / hotspot / secretome per-gene features. The OCL
# orthogroup summary is the spine; each orthogroup's member sequence IDs are
# the bridge to the per-gene feature tables.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml:
#    - run_label (e.g. "species70_X_OrthoHMM" — mirror the OCL run integrated)
#    - species_set_name (e.g. "species70")
#    - execution_mode ("local" or "slurm"); if slurm, slurm_account + slurm_qos
#    - input paths (OCL orthogroups + dark/hotspot/secretome output_to_input)
# 2. Edit INPUT_user/structure_manifest.tsv with structure IDs to integrate
# 3. Verify upstream output_to_input/ are populated:
#    - ocl_phylogenetic_structures/output_to_input/BLOCK_orthogroups_X_ocl/<run_label>/
#         (must expose 4_ai-orthogroups-complete_ocl_summary.tsv AND
#          4_ai-path_states-per_orthogroup_per_species.tsv per structure)
#    - dark_proteomes/output_to_input/BLOCK_classify_dark_proteome/dark_proteome/
#    - hotspots/output_to_input/BLOCK_identify_hotspots/hotspots/
#    - secretome/output_to_input/STEP_2-filter_secretome/  (+ STEP_1-build_evidence_table/)
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-BLOCK conda env from ai/conda_environment.yml
# 2. Runs the pipeline:
#    001: build structure-invariant gene->feature lookup (once)
#    002: per-structure integrated orthogroup summary    (Table 1)
#    003: per-structure block-state expanded table       (Table 2)
#    004: per-structure gene-level drill-down            (Table 3)
#    005: validate results (strict fail-fast)
#    006: write run log
# 3. Creates output_to_input symlinks for downstream consumers
#
# OUTPUT:
#   OUTPUT_pipeline/_shared/1-output/            gene->feature lookup
#   OUTPUT_pipeline/structure_NNN/2-output/      Table 1 (integrated summary)
#   OUTPUT_pipeline/structure_NNN/3-output/      Table 2 (block-state expanded)
#   OUTPUT_pipeline/structure_NNN/4-output/      Table 3 (gene drill-down)
#   OUTPUT_pipeline/structure_NNN/5-output/      validation report
#   ../../output_to_input/BLOCK_orthogroups_ocl_X_features/<run_label>/
################################################################################

echo "========================================================================"
echo "GIGANTIC integrator - orthogroups_ocl_X_features"
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

# Structure count (used in the final console summary) and workflow directory
# name (used below to build output_to_input symlink targets).
MANIFEST="INPUT_user/structure_manifest.tsv"
STRUCTURE_COUNT=0
if [ -f "${MANIFEST}" ]; then
    STRUCTURE_COUNT=$(tail -n +2 "${MANIFEST}" | grep -v '^$' | wc -l)
fi

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# ============================================================================
# SLURM self-submission (if execution_mode=slurm and not already in a job)
# ============================================================================
if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""
    SLURM_CPUS=$(read_config "cpus" "3")
    SLURM_MEM=$(read_config "memory_gb" "20")
    SLURM_TIME=$(read_config "time_hours" "8")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs
    SBATCH_ARGS="--job-name=integrator_ocl_X_features"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/integrator_ocl_X_features-%j.log"
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
ENV_NAME="aiG-integrator-orthogroups_ocl_X_features"
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
[ -d "INPUT_user" ] || { echo "ERROR: INPUT_user/ not found!"; exit 1; }
echo "  [OK] INPUT_user/ found"
[ -f "${MANIFEST}" ] || { echo "ERROR: Structure manifest not found: ${MANIFEST}"; exit 1; }
echo "  [OK] Structure manifest found: ${MANIFEST}"
echo "  [OK] Structures to process: ${STRUCTURE_COUNT}"
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
# Real files live in OUTPUT_pipeline/structure_NNN/{2,3,4}-output/.
# Expose all three per-structure tables under a run_label-namespaced subdir,
# with clean (infix-free) names so downstream paths are stable.
echo ""
echo "Creating symlinks for downstream consumers..."

SHARED_DIR="../../output_to_input/BLOCK_orthogroups_ocl_X_features/${RUN_LABEL}"
mkdir -p "${SHARED_DIR}"

# Remove stale per-structure symlink dirs from previous runs
for old in "${SHARED_DIR}"/structure_*; do
    [ -e "$old" ] && rm -rf "$old"
done

for structure_dir in OUTPUT_pipeline/structure_*; do
    [ -d "$structure_dir" ] || continue
    structure_name=$(basename "$structure_dir")          # structure_NNN
    structure_num="${structure_name#structure_}"          # NNN
    mkdir -p "${SHARED_DIR}/${structure_name}"

    declare -A TABLE_MAP=(
        ["2-output/2_ai-structure_${structure_num}_orthogroups-integrated_summary.tsv"]="2_ai-orthogroups-integrated_summary.tsv"
        ["3-output/3_ai-structure_${structure_num}_block_states-integrated_expanded.tsv"]="3_ai-block_states-integrated_expanded.tsv"
        ["4-output/4_ai-structure_${structure_num}_genes-integrated_drilldown.tsv"]="4_ai-genes-integrated_drilldown.tsv"
    )
    for src_rel in "${!TABLE_MAP[@]}"; do
        clean_name="${TABLE_MAP[$src_rel]}"
        src_file="${structure_dir}/${src_rel}"
        if [ -f "$src_file" ]; then
            ln -sf "../../../../BLOCK_orthogroups_ocl_X_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/${structure_name}/${src_rel}" \
                "${SHARED_DIR}/${structure_name}/${clean_name}"
        fi
    done
    unset TABLE_MAP
done

SYMLINK_COUNT=$(find "${SHARED_DIR}" -name "*.tsv" -type l 2>/dev/null | wc -l)
echo "  output_to_input/BLOCK_orthogroups_ocl_X_features/${RUN_LABEL}/ -> ${SYMLINK_COUNT} symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Integration complete."
echo "  Run Label: ${RUN_LABEL}"
echo "  Structures processed: ${STRUCTURE_COUNT}"
echo "  Downstream: ../../output_to_input/BLOCK_orthogroups_ocl_X_features/${RUN_LABEL}/"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
