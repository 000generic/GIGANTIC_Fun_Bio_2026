#!/bin/bash
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: Obtain the NCBI taxonomy snapshot for phyloname generation - download the current release, reuse an existing copy on disk, or download a specific dated archive
# Human: Eric Edsinger

################################################################################
# SCRIPT PURPOSE (For Non-Programmers):
# ----------------------------------------------------------------------------
# This script makes an NCBI taxonomy snapshot available to the rest of the
# phylonames workflow. The NCBI (National Center for Biotechnology Information)
# maintains a comprehensive database of all known species and their taxonomic
# relationships. The key file we need from it is "rankedlineage.dmp".
#
# It supports THREE ways to obtain the snapshot (chosen by --source-mode, which
# comes from the ncbi_taxonomy.source_mode setting in START_HERE-user_config.yaml):
#
#   download_latest   Download the current "new_taxdump" release from NCBI.
#                     Simplest, but the snapshot changes over time.
#
#   supply_path       Reuse a taxonomy directory you ALREADY have on disk
#                     (one that contains rankedlineage.dmp). Nothing is
#                     downloaded. This is the reproducible choice: pinning one
#                     snapshot guarantees the GIGANTIC-generated numbered clades
#                     and phylonames are identical every time you re-run.
#
#   download_version  Download a SPECIFIC dated snapshot from the NCBI archive
#                     (e.g., 2026-03-01). Reproducible without keeping a local
#                     copy. The archived files are .zip (the latest is .tar.gz).
#
# In all three modes the script leaves behind, in the current directory:
#   database-ncbi_taxonomy_latest        a handle pointing at the snapshot
#   database-ncbi_taxonomy_<...>         the snapshot directory (or a symlink)
# so the rest of the workflow sees one uniform interface regardless of source.
################################################################################

################################################################################
# TECHNICAL NOTES (For Python/CS Experts):
# ----------------------------------------------------------------------------
# - Runs inside the NextFlow work directory (cwd). main.nf passes the
#   ncbi_taxonomy.* params as flags; this script does NOT read the yaml itself.
# - download_latest / download_version use wget with retry logic.
# - download_version extracts a .zip via python3 zipfile (no unzip dependency).
# - supply_path resolves to an ABSOLUTE path and symlinks it in, so NextFlow can
#   stage the handle into downstream process work dirs and still resolve it.
# - Fail-fast: any missing/invalid input or a snapshot lacking rankedlineage.dmp
#   exits non-zero so the pipeline stops immediately (no silent bad data).
################################################################################

set -e  # Exit on any error

# ============================================================================
# Parse arguments (all supplied by main.nf from ncbi_taxonomy.* params)
# ============================================================================
SOURCE_MODE="download_latest"
TAXONOMY_PATH=""
DOWNLOAD_VERSION=""
DOWNLOAD_URL="ftp://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz"
ARCHIVE_URL_PATTERN="https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump_archive/new_taxdump_{version}.zip"
WORKFLOW_DIR="."

while [ $# -gt 0 ]; do
    case "$1" in
        --source-mode)         SOURCE_MODE="$2"; shift 2 ;;
        --taxonomy-path)       TAXONOMY_PATH="$2"; shift 2 ;;
        --download-version)    DOWNLOAD_VERSION="$2"; shift 2 ;;
        --download-url)        DOWNLOAD_URL="$2"; shift 2 ;;
        --archive-url-pattern) ARCHIVE_URL_PATTERN="$2"; shift 2 ;;
        --workflow-dir)        WORKFLOW_DIR="$2"; shift 2 ;;
        *) echo "ERROR: unknown argument '$1'"; exit 1 ;;
    esac
done

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
DATABASE_DIR="database-ncbi_taxonomy_${TIMESTAMP}"

echo "============================================================"
echo "NCBI Taxonomy - Obtain Snapshot"
echo "============================================================"
echo "Source mode:      ${SOURCE_MODE}"
echo "Timestamp (UTC):  ${TIMESTAMP}"
echo ""

# ----------------------------------------------------------------------------
# Helper: verify a directory holds the file phyloname generation needs
# ----------------------------------------------------------------------------
require_rankedlineage() {
    local dir="$1"
    if [ ! -f "${dir}/rankedlineage.dmp" ]; then
        echo "ERROR: rankedlineage.dmp not found in: ${dir}"
        echo "This file is required for phyloname generation (script 002)."
        echo "A valid NCBI 'new_taxdump' snapshot contains rankedlineage.dmp at its top level."
        exit 1
    fi
}

# ============================================================================
# MODE: supply_path - reuse an existing snapshot (no download)
# ============================================================================
if [ "${SOURCE_MODE}" == "supply_path" ]; then
    if [ -z "${TAXONOMY_PATH}" ]; then
        echo "ERROR: source_mode is 'supply_path' but ncbi_taxonomy.taxonomy_path is empty."
        echo "Set taxonomy_path in START_HERE-user_config.yaml to a directory containing rankedlineage.dmp."
        exit 1
    fi

    # Resolve relative paths against the workflow directory (where the user edits
    # the config), not the NextFlow work dir this script runs in.
    case "${TAXONOMY_PATH}" in
        /*) RESOLVED_INPUT="${TAXONOMY_PATH}" ;;
        *)  RESOLVED_INPUT="${WORKFLOW_DIR}/${TAXONOMY_PATH}" ;;
    esac

    # Absolute, with symlinks (e.g. database-ncbi_taxonomy_latest) followed to the
    # real snapshot dir so we pin the actual snapshot.
    RESOLVED_ABS=$(realpath -m "${RESOLVED_INPUT}")

    if [ ! -d "${RESOLVED_ABS}" ]; then
        echo "ERROR: taxonomy_path does not resolve to a directory:"
        echo "  configured: ${TAXONOMY_PATH}"
        echo "  resolved:   ${RESOLVED_ABS}"
        exit 1
    fi

    require_rankedlineage "${RESOLVED_ABS}"

    echo "Reusing existing NCBI taxonomy snapshot (no download):"
    echo "  ${RESOLVED_ABS}"

    # Materialize the uniform handles as symlinks to the absolute snapshot dir.
    ln -s "${RESOLVED_ABS}" "${DATABASE_DIR}"
    ln -s "${RESOLVED_ABS}" "database-ncbi_taxonomy_latest"

    echo ""
    echo "============================================================"
    echo "Snapshot ready (supply_path)."
    echo "  database-ncbi_taxonomy_latest -> ${RESOLVED_ABS}"
    echo "============================================================"
    exit 0
fi

# ============================================================================
# MODE: download_latest / download_version - fetch + extract
# ============================================================================
if [ "${SOURCE_MODE}" == "download_latest" ]; then
    FETCH_URL="${DOWNLOAD_URL}"
    ARCHIVE_KIND="tar.gz"
    if [ -z "${FETCH_URL}" ]; then
        echo "ERROR: source_mode is 'download_latest' but ncbi_taxonomy.download_url is empty."
        exit 1
    fi
elif [ "${SOURCE_MODE}" == "download_version" ]; then
    if [ -z "${DOWNLOAD_VERSION}" ]; then
        echo "ERROR: source_mode is 'download_version' but ncbi_taxonomy.download_version is empty."
        echo "Set download_version to a dated NCBI snapshot, e.g. \"2026-03-01\"."
        exit 1
    fi
    # Substitute {version} into the archive URL pattern.
    FETCH_URL="${ARCHIVE_URL_PATTERN/\{version\}/${DOWNLOAD_VERSION}}"
    ARCHIVE_KIND="zip"
else
    echo "ERROR: unknown source_mode '${SOURCE_MODE}'."
    echo "Must be one of: download_latest | supply_path | download_version"
    exit 1
fi

echo "Download URL:     ${FETCH_URL}"
echo "Target directory: ${DATABASE_DIR}"
echo ""

mkdir -p "${DATABASE_DIR}"
cd "${DATABASE_DIR}"

# Record provenance metadata
cat > "download_metadata.txt" << EOF
NCBI Taxonomy Database Download Metadata
========================================
Download timestamp (UTC):   $(date -u +"%Y-%m-%d %H:%M:%S")
Download timestamp (local): $(date +"%Y-%m-%d %H:%M:%S %Z")
Source mode:                ${SOURCE_MODE}
Source URL:                 ${FETCH_URL}
Requested version:          ${DOWNLOAD_VERSION:-N/A (latest)}
Target directory:           ${DATABASE_DIR}
Downloaded by:              GIGANTIC phylonames subproject (script 001)
EOF

echo "Downloading NCBI taxonomy snapshot..."
echo "This may take a few minutes depending on connection speed..."
echo ""

if [ "${ARCHIVE_KIND}" == "tar.gz" ]; then
    ARCHIVE_FILE="new_taxdump.tar.gz"
else
    ARCHIVE_FILE="new_taxdump.zip"
fi

wget --tries=3 \
     --waitretry=10 \
     --timeout=60 \
     --progress=bar:force \
     "${FETCH_URL}" \
     -O "${ARCHIVE_FILE}"

echo ""
echo "Recording checksum..."
md5sum "${ARCHIVE_FILE}" >> download_metadata.txt
echo "" >> download_metadata.txt

echo ""
echo "Extracting taxonomy files..."
if [ "${ARCHIVE_KIND}" == "tar.gz" ]; then
    tar -xzf "${ARCHIVE_FILE}"
else
    # Archived snapshots are .zip; extract with python3 zipfile (no unzip needed).
    python3 -c "import zipfile, sys; zipfile.ZipFile( sys.argv[1] ).extractall( '.' )" "${ARCHIVE_FILE}"
fi

# Record extracted file sizes
echo "Extracted files:" >> download_metadata.txt
ls -lh *.dmp >> download_metadata.txt 2>/dev/null || echo "No .dmp files found" >> download_metadata.txt

# Verify the critical file exists before declaring success
require_rankedlineage "."

# Clean up archive to save space
echo ""
echo "Cleaning up archive..."
rm -f "${ARCHIVE_FILE}"

cd ..

# Create the uniform "latest" handle
echo ""
echo "Creating symlink to latest database..."
rm -f database-ncbi_taxonomy_latest
ln -s "${DATABASE_DIR}" database-ncbi_taxonomy_latest

echo ""
echo "============================================================"
echo "Download Complete!"
echo "============================================================"
echo "Database directory: ${DATABASE_DIR}"
echo "Symlink created:    database-ncbi_taxonomy_latest -> ${DATABASE_DIR}"
echo ""
echo "Key files:"
ls -lh "${DATABASE_DIR}"/*.dmp 2>/dev/null | head -5
echo ""
echo "Metadata recorded in: ${DATABASE_DIR}/download_metadata.txt"
echo "Next step: 002_ai-python-generate_phylonames.py"
echo "============================================================"
