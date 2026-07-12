#!/bin/bash
# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Run the sequence_groups_X_species sequence_groups workflow (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC sequence_groups_X_species - BLOCK_sequence_groups
################################################################################
#
# PURPOSE:
# Resolve MANY sequence-group sets (orthogroups, annogroups pfam/go/panther,
# gene families, gene groups, ...) onto the species-tree clades in ONE run:
#   001 standard membership, 002 deconvolution (4-structure scope), 003 per-species map,
#   006 annotation index (once), 004 composite clades (242 detail tables w/ annotations).
#
# USAGE:   bash RUN-workflow.sh
#
# BEFORE RUNNING, edit START_HERE-user_config.yaml:
#   - producers: (membership paths + optional group_attributes per producer)
#   - deconvolution_structures (default 001/003/031/032; [] = all 105)
#   - annotation_index (paths for Script 006; required for annotated detail tables)
#   - inputs.clade_species_mappings / composite_clades_manifest
#   - execution_mode ("local" or "slurm"); for slurm set slurm_account / slurm_qos
#
# OUTPUT:
#   OUTPUT_pipeline/{1,2,3,4}-output/
#   Downstream symlinks in ../../output_to_input/<group_set_label>/
################################################################################

echo "========================================================================"
echo "GIGANTIC sequence_groups_X_species - sequence_groups"
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
SPECIES_SET=$(read_config "species_set_name" "")
# Multi-producer: ONE run resolves every entry under `producers:` in the config.
PRODUCER_COUNT=$(grep -c '^[[:space:]]*- producer:' START_HERE-user_config.yaml)

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
    SBATCH_ARGS="--job-name=sequence_groups --cpus-per-task=${SLURM_CPUS} --mem=${SLURM_MEM}gb --time=${SLURM_TIME}:00:00 --output=slurm_logs/sequence_groups-%j.log"
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
ENV_NAME="aiG-sequence_groups_X_species-sequence_groups"
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
echo "Configuration: ${PRODUCER_COUNT} producer(s) species_set=${SPECIES_SET}"
echo ""

# ---- run timestamp pointer (§65 dual-layer; shared across all producers) ----
INTEGRATOR_AI="${SCRIPT_DIR}/../../../integrator/ai"
mkdir -p OUTPUT_pipeline
python3 "${INTEGRATOR_AI}/write_workflow_run_timestamp.py" --output-pipeline OUTPUT_pipeline

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

# ---- output_to_input symlinks (per producer) ------------------------------
# Real files live under <subproject>/<block>/<workflow>/OUTPUT_pipeline/<label>/{2,3,4}-output/;
# downstream consumers read symlinks under the SUBPROJECT-root output_to_input/
# in a per-producer namespace: output_to_input/<producer>/<group_set_label>/ so the
# many group sets stay navigable (annogroups/, orthogroups/, gene_families/, gene_groups/).
echo ""
echo "Creating output_to_input symlinks for ${PRODUCER_COUNT} producer(s)..."
BLOCK_DIR_NAME="$(basename "$(dirname "${SCRIPT_DIR}")")"

# (producer, group_set_label) pairs, parsed from the config with the workflow's Python.
PRODUCER_SPECS="$(python3 -c "
import yaml
with open( 'START_HERE-user_config.yaml' ) as handle:
    config = yaml.safe_load( handle )
for producer in config.get( 'producers', [] ):
    print( producer[ 'producer' ] + '\t' + producer[ 'group_set_label' ] )
")"
if [ -z "${PRODUCER_SPECS}" ]; then
    echo "ERROR: could not parse any producers from START_HERE-user_config.yaml"; exit 1
fi

while IFS=$'\t' read -r PRODUCER GROUP_SET_LABEL; do
    [ -n "${GROUP_SET_LABEL}" ] || continue
    OUT_LABEL_DIR="OUTPUT_pipeline/${GROUP_SET_LABEL}"
    SHARED_DIR="../../output_to_input/${PRODUCER}/${GROUP_SET_LABEL}"
    find "${SHARED_DIR}" -mindepth 1 -delete 2>/dev/null || true
    mkdir -p "${SHARED_DIR}"
    python3 "${INTEGRATOR_AI}/link_stable_output_to_input_symlinks.py" \
        --output-pipeline "OUTPUT_pipeline/${GROUP_SET_LABEL}" \
        --shared-dir "${SHARED_DIR}" \
        --workflow-relative "../../../${BLOCK_DIR_NAME}/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/${GROUP_SET_LABEL}" \
        --preserve-subdirs
    SYMLINK_COUNT=$(find "${SHARED_DIR}" -type l 2>/dev/null | wc -l)
    echo "  output_to_input/${PRODUCER}/${GROUP_SET_LABEL}/ -> ${SYMLINK_COUNT} symlinks"
done <<< "${PRODUCER_SPECS}"

if [ -d "OUTPUT_pipeline/annotation_index" ]; then
    ANNO_SHARED="../../output_to_input/annotation_index"
    find "${ANNO_SHARED}" -mindepth 1 -delete 2>/dev/null || true
    mkdir -p "${ANNO_SHARED}"
    python3 "${INTEGRATOR_AI}/link_stable_output_to_input_symlinks.py" \
        --output-pipeline OUTPUT_pipeline/annotation_index \
        --shared-dir "${ANNO_SHARED}" \
        --workflow-relative "../../../${BLOCK_DIR_NAME}/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/annotation_index"
    echo "  output_to_input/annotation_index/ -> $(find "${ANNO_SHARED}" -type l 2>/dev/null | wc -l) symlinks"
fi

echo ""
echo "========================================================================"
echo "SUCCESS! sequence_groups_X_species sequence_groups complete."
echo "  Per producer, under OUTPUT_pipeline/<group_set_label>/:"
echo "    1-output/  standard membership"
echo "    2-output/  deconvolution (sequence + species counts per clade)"
echo "    3-output/  per-species sequence map"
echo "    4-output/  composite clades"
echo "  Downstream symlinks: output_to_input/<producer>/<group_set_label>/"
echo "Completed: $(date)"
echo "========================================================================"

conda deactivate 2>/dev/null || true
