#!/bin/bash
# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Run the sequence_groups_X_species resolve_groups workflow (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC sequence_groups_X_species - BLOCK_resolve_groups
################################################################################
#
# PURPOSE:
# Resolve ONE sequence-group set (orthogroups, annogroups, gene families, ...)
# onto the species-tree clades: standard membership (001), deconvolution (002),
# per-species sequence map (003), composite clades (004).
#
# USAGE:   bash RUN-workflow.sh
#
# BEFORE RUNNING, edit START_HERE-user_config.yaml:
#   - group_set_label (e.g. "species70_X_OrthoHMM")
#   - species_set_name, producer (e.g. "orthogroups")
#   - inputs.producer_membership / clade_species_mappings / composite_clades_manifest
#   - composite_clades block (building-block clade groups)
#   - execution_mode ("local" or "slurm"); for slurm set slurm_account / slurm_qos
#
# OUTPUT:
#   OUTPUT_pipeline/{1,2,3,4}-output/
#   Downstream symlinks in ../../output_to_input/<group_set_label>/
################################################################################

echo "========================================================================"
echo "GIGANTIC sequence_groups_X_species - resolve_groups"
echo "========================================================================"
echo "Started: $(date)"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ---- read flat YAML keys (no Python dependency) ----------------------------
read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")
GROUP_SET_LABEL=$(read_config "group_set_label" "")
PRODUCER=$(read_config "producer" "")
SPECIES_SET=$(read_config "species_set_name" "")

# Workflow directory name (used below to build output_to_input symlink targets).
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# ---- SLURM self-submit -----------------------------------------------------
if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "24")
    SLURM_TIME=$(read_config "time_hours" "4")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")
    mkdir -p slurm_logs
    SBATCH_ARGS="--job-name=resolve_groups --cpus-per-task=${SLURM_CPUS} --mem=${SLURM_MEM}gb --time=${SLURM_TIME}:00:00 --output=slurm_logs/resolve_groups-%j.log"
    [ -n "${SLURM_ACCOUNT}" ] && SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
    [ -n "${SLURM_QOS}" ] && SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"
    echo "Submitting with: sbatch ${SBATCH_ARGS}"
    sbatch ${SBATCH_ARGS} --wrap="bash $(realpath $0)"
    echo "Job submitted. Check slurm_logs/ for output."
    exit 0
fi

[ -n "${SLURM_JOB_ID}" ] && echo "Running inside SLURM job ${SLURM_JOB_ID}" || echo "Execution mode: local"
echo ""

# ---- conda env (on-demand) -------------------------------------------------
ENV_NAME="aiG-sequence_groups_X_species-resolve_groups"
ENV_YML="ai/conda_environment.yml"
module load conda 2>/dev/null || true
if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found! On HPC: module load conda"; exit 1
fi
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    if command -v mamba &> /dev/null; then mamba env create -f "${ENV_YML}" -y; else conda env create -f "${ENV_YML}" -y; fi
    [ $? -ne 0 ] && { echo "ERROR: failed to create conda env '${ENV_NAME}'"; exit 1; }
fi
conda activate "${ENV_NAME}" 2>/dev/null && echo "Activated conda environment: ${ENV_NAME}" || echo "WARNING: could not activate '${ENV_NAME}'"
if ! command -v nextflow &> /dev/null; then module load nextflow 2>/dev/null || true; fi
command -v nextflow &> /dev/null || { echo "ERROR: NextFlow not available!"; exit 1; }
echo ""

# ---- validate prerequisites ------------------------------------------------
[ -f "START_HERE-user_config.yaml" ] || { echo "ERROR: START_HERE-user_config.yaml not found"; exit 1; }
echo "Configuration: group_set=${GROUP_SET_LABEL} producer=${PRODUCER} species_set=${SPECIES_SET}"
echo ""

# ---- run NextFlow ----------------------------------------------------------
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""; [ "${RESUME}" == "true" ] && RESUME_FLAG="-resume"
echo "Running NextFlow pipeline..."
nextflow run ai/main.nf ${RESUME_FLAG} -profile local -params-file START_HERE-user_config.yaml
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    exit $EXIT_CODE
fi

# ---- output_to_input symlinks ---------------------------------------------
# Real files in OUTPUT_pipeline/{2,3,4}-output/; symlinks under
# ../../output_to_input/<group_set_label>/ for downstream consumers.
echo ""
echo "Creating output_to_input symlinks for ${GROUP_SET_LABEL}..."
# output_to_input lives at the SUBPROJECT root; real files live under
# <subproject>/<block>/<workflow>/OUTPUT_pipeline/. So a symlink at
# output_to_input/<label>/ reaches them via ../../<block>/<workflow>/...
BLOCK_DIR_NAME="$(basename "$(dirname "${SCRIPT_DIR}")")"
# Per-producer namespace: output_to_input/<producer>/<group_set_label>/ so the many
# group sets stay navigable (annogroups/, orthogroups/, gene_families/, gene_groups/).
SHARED_DIR="../../output_to_input/${PRODUCER}/${GROUP_SET_LABEL}"
# replace stale state for this group set (output_to_input holds only symlinks)
find "${SHARED_DIR}" -mindepth 1 -maxdepth 1 -name '*.tsv' -type l -delete 2>/dev/null
rm -rf "${SHARED_DIR}/composite_clades_detail_tables" 2>/dev/null
mkdir -p "${SHARED_DIR}"
SYMLINK_COUNT=0
link_outputs() {
    # link every .tsv in OUTPUT_pipeline/$1 into SHARED_DIR (flat)
    for f in OUTPUT_pipeline/$1/*.tsv; do
        [ -f "$f" ] || continue
        ln -sf "../../../${BLOCK_DIR_NAME}/${WORKFLOW_DIR_NAME}/$f" "${SHARED_DIR}/$(basename "$f")"
        SYMLINK_COUNT=$((SYMLINK_COUNT+1))
    done
}
link_outputs "2-output"   # deconvolution union tables
link_outputs "3-output"   # per-species map
link_outputs "4-output"   # composite per-group + summary
# composite detail tables (a subdir)
if [ -d "OUTPUT_pipeline/4-output/composite_clades_detail_tables" ]; then
    mkdir -p "${SHARED_DIR}/composite_clades_detail_tables"
    for f in OUTPUT_pipeline/4-output/composite_clades_detail_tables/*.tsv; do
        [ -f "$f" ] || continue
        ln -sf "../../../../${BLOCK_DIR_NAME}/${WORKFLOW_DIR_NAME}/$f" "${SHARED_DIR}/composite_clades_detail_tables/$(basename "$f")"
        SYMLINK_COUNT=$((SYMLINK_COUNT+1))
    done
fi
echo "  output_to_input/${GROUP_SET_LABEL}/ -> ${SYMLINK_COUNT} symlinks"

echo ""
echo "========================================================================"
echo "SUCCESS! sequence_groups_X_species resolve_groups complete."
echo "  OUTPUT_pipeline/1-output/  standard membership"
echo "  OUTPUT_pipeline/2-output/  deconvolution (sequence + species counts per clade)"
echo "  OUTPUT_pipeline/3-output/  per-species sequence map"
echo "  OUTPUT_pipeline/4-output/  composite clades"
echo "  output_to_input/${GROUP_SET_LABEL}/"
echo "Completed: $(date)"
echo "========================================================================"

conda deactivate 2>/dev/null || true
