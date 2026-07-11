#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * INTEGRATOR PIPELINE: ORTHOGROUPS_X_ALL_ANNOTATIONS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow that builds ONE table with one row per OrthoHMM
 * orthogroup: member sequence IDs, then FOUR columns (species count, sequence
 * count, identifiers, names) for each of seven annotation types — Pfam, GO,
 * PANTHER, gene families, gene groups, dark proteome, hotspots — plus a
 * species-tree deconvolution (per-clade / per-species member-sequence counts)
 * across the selected structures (001, 003, 031, 032).
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly under OUTPUT_pipeline/
 * - Structure-independent integration (orthogroup membership + all per-sequence
 *   annotations are invariant across structures), so there is no per-structure
 *   fan-out — a handful of singleton processes.
 * - All paths resolved from START_HERE-user_config.yaml (relative to workflow dir).
 *
 * Pipeline:
 *   001 build_annotations_table -> 1-output (the headline table)
 *   002 validate_results        -> 2-output (fail-fast, §36)
 *   003 write_run_log           -> ai/logs (§45)
 *
 * AI: Claude (Cursor) | Opus 4.8 | 2026 July 10
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC integrator - orthogroups_X_all_annotations
    ==============================================================================

    Usage:
        nextflow run main.nf -params-file ../START_HERE-user_config.yaml

    All configuration is read from START_HERE-user_config.yaml:
      - run_label, species_set_name, hmm_annotation_sources
      - inputs.{orthogroups_file, interproscan_parsed_dir, interproscan_raw_dir,
                go_id_to_name, gene_families_dir, gene_groups_dir,
                gene_groups_hgnc_metadata, dark_proteome_dir, hotspots_dir,
                clade_species_mappings, deconvolution_structures}
      - output.base_dir
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// PROCESS 001: BUILD THE ALL-ANNOTATIONS TABLE
// ============================================================================
// Reads the orthogroups spine, aggregates non-redundant per-sequence annotations
// for all seven types, and deconvolves the selected species-tree structures into
// per-clade / per-species member-count columns.

process build_annotations_table {
    label 'local'

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-build_annotations_table.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: VALIDATE RESULTS (fail-fast per §36)
// ============================================================================

process validate_results {
    label 'local'

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
        --workflow-name "orthogroups_X_all_annotations" \\
        --subproject-name "integrator-BLOCK_orthogroups_X_all_annotations" \\
        --project-name "${params.species_set_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    build_annotations_table()
    validate_results( build_annotations_table.out.done )
    write_run_log( validate_results.out.done )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
