#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: NextFlow pipeline scaffold for per-protein secretome evidence-table builder
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// Secretome Evidence Table Builder
// =============================================================================
//
// SCAFFOLD STATUS ( 2026-05-23 ):
//   - validate_proteome_manifest:  IMPLEMENTED ( reuses standard pattern )
//   - build_evidence_table:        STUB ( script not yet written; pivots
//                                  the long-format DB output of
//                                  BLOCK_build_annotation_database into one
//                                  wide TSV per species )
//   - write_run_log:               IMPLEMENTED
//
// The pivot script ( 002_ai-python-build_evidence_table.py ) is the substantive
// piece. It will be designed and written after the upstream tool RUNs +
// BLOCK_build_annotation_database are run end-to-end so the actual input
// shapes are known.
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process validate_proteome_manifest {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        val manifest_path

    output:
        path '1_ai-validated_manifest.tsv', emit: validated_manifest
        path '1_ai-log-validate_proteome_manifest.log'

    script:
    """
    python3 ${scripts_dir}/001_ai-python-validate_proteome_manifest.py \
        --manifest-path ${manifest_path} \
        --output-dir .
    """
}

/*
 * Process 2: Build per-protein evidence table for one species
 *
 * SCAFFOLD: script not yet written. Will pivot from long-format DB at
 * params.annotation_database_dir + proteome FASTA into wide per-protein TSV.
 *
 * Expected input tuple: ( species_name, proteome_path, phyloname )
 * Expected output:      <phyloname>_evidence_table.tsv
 */
process build_evidence_table {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        tuple val( species_name ), val( proteome_path ), val( phyloname )

    output:
        path "${phyloname}_evidence_table.tsv", emit: evidence_table
        path "2_ai-log-build_evidence_table_${phyloname}.log"

    script:
    """
    python3 ${scripts_dir}/002_ai-python-build_evidence_table.py \
        --input-fasta ${proteome_path} \
        --annotation-database-dir ${params.annotation_database_dir} \
        --deeploc-csv-dir ${params.deeploc_csv_dir} \
        --include-databases '${params.include_databases}' \
        --output-dir . \
        --phyloname ${phyloname}
    """
}

/*
 * Process 3: Write Run Log ( final marker for pipeline completion )
 * Calls: scripts/003_ai-python-write_run_log.py
 */
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-write_run_log.py \
        --workflow-name "build_evidence_table" \
        --subproject-name "secretome" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// Workflow
// ============================================================================
// NOTE: Symlinks for output_to_input/BLOCK_secretome_evidence_table/ are
// created by RUN-workflow.sh AFTER this pipeline completes. NextFlow only
// writes real files to OUTPUT_pipeline/N-output/ directories.
// ============================================================================
workflow {
    // Step 1: Validate proteome manifest
    validate_proteome_manifest( params.proteome_manifest )

    // Step 2: Parse validated manifest into per-species channel, build evidence table per species
    validated_channel = validate_proteome_manifest.out.validated_manifest
        .splitCsv( sep: '\t', skip: 1 )
        .map { row -> tuple( row[ 0 ], row[ 1 ], row[ 2 ] ) }

    build_evidence_table( validated_channel )

    // Step 3: Write run log (FINAL STEP)
    write_run_log( build_evidence_table.out.evidence_table.collect() )
}
