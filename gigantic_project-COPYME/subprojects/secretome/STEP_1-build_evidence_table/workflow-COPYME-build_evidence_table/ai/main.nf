#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: NextFlow pipeline scaffold for per-protein secretome evidence-table builder
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// Secretome Evidence Table Builder
// =============================================================================
//
// Processes:
//   - validate_proteome_manifest:  validate the species proteome manifest.
//   - build_evidence_table:        pivot the long-format standardized
//                                  annotation database produced by
//                                  annotations_hmms/BLOCK_build_annotation_database
//                                  into one wide per-protein evidence table per
//                                  species (002_ai-python-build_evidence_table.py).
//   - write_run_log:               final completion marker + provenance log.
//
// Path handling: upstream input paths in START_HERE-user_config.yaml are
// RELATIVE to this workflow directory. main.nf passes an absolute
// --workflow-root ( ${projectDir}/.. ) to each script, which resolves those
// relative paths against it so they survive NextFlow's work/ execution dirs.
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
 * Pivots the long-format standardized annotation database
 * (params.annotation_database_dir) + the species proteome FASTA into one wide
 * per-protein evidence table, augmented with DeepLoc per-compartment
 * probabilities (params.deeploc_csv_dir).
 *
 * Input tuple:   ( species_name, proteome_path, phyloname )
 * Output:        <phyloname>_evidence_table.tsv
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
        --workflow-root ${projectDir}/.. \
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
// NOTE: Symlinks for output_to_input/STEP_1-build_evidence_table/ are
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
