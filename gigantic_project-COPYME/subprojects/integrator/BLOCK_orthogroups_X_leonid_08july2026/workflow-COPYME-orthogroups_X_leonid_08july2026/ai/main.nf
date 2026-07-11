#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * INTEGRATOR PIPELINE: ORTHOGROUPS_X_LEONID_08JULY2026
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow that builds ONE table with one row per OrthoHMM
 * orthogroup: member sequence IDs, non-redundant Pfam/GO/PANTHER annotations, and
 * a species-tree deconvolution (per-clade / per-species member-sequence counts)
 * across the selected structures (001, 003, 031, 032).
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly under OUTPUT_pipeline/
 * - Structure-independent integration (orthogroup membership, annogroup
 *   membership, and per-clade species sets are invariant across structures), so
 *   there is no per-structure fan-out — a handful of singleton processes.
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow dir).
 *
 * Pipeline:
 *   001 build_leonid_table  -> 1-output (the headline table)
 *   002 validate_results    -> 2-output (fail-fast, §36)
 *   003 write_run_log       -> ai/logs (§45)
 *
 * AI: Claude (Cursor) | Opus 4.8 | 2026 July 08
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC integrator - orthogroups_X_leonid_08july2026
    ==============================================================================

    Usage:
        nextflow run main.nf -params-file ../START_HERE-user_config.yaml

    All configuration is read from START_HERE-user_config.yaml:
      - run_label, species_set_name, annotation_sources
      - inputs.{orthogroups_file, annogroups_dir, clade_species_mappings,
                deconvolution_structures}
      - output.base_dir
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// PROCESS 001: BUILD THE LEONID TABLE
// ============================================================================
// Reads the orthogroups spine, aggregates non-redundant Pfam/GO/PANTHER
// annotations from annogroup feature membership, and deconvolves the selected
// species-tree structures into per-clade / per-species member-count columns.

process build_leonid_table {
    label 'local'
    cache false

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-build_leonid_table.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: VALIDATE RESULTS (fail-fast per §36)
// ============================================================================

process validate_results {
    label 'local'
    cache false

    input:
        val build_done

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-validate_results.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 003: WRITE RUN LOG (per §45)
// ============================================================================

process write_run_log {
    label 'local'

    input:
        val validate_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-write_run_log.py \\
        --workflow-name "orthogroups_X_leonid_08july2026" \\
        --subproject-name "integrator-BLOCK_orthogroups_X_leonid_08july2026" \\
        --project-name "${params.species_set_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    build_leonid_table()
    validate_results( build_leonid_table.out.done )
    write_run_log( validate_results.out.done )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
