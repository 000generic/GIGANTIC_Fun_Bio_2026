#!/usr/bin/env nextflow
// AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: STEP_2 - augment STEP_1 evidence tables then filter to produce per-species secretome
// Human: Eric Edsinger

nextflow.enable.dsl = 2

// =============================================================================
// STEP_2: secretome filter pipeline (Stage 2 — full chain)
// =============================================================================
//
// Per species, in this order:
//   001 validate_filter_manifest         — JSON syntax + structure
//   003 augment_with_derived_columns     — cysteine count, pfam max-per-accession
//   005 augment_with_orthogroups         — OG_ID + total members + 4 model-species ortholog cols
//   006 augment_with_blastp_top10        — top 10 NCBI nr hits + e-values + headers
//   002 apply_filters_per_species        — filter manifest applied AFTER augment so
//                                          filter clauses can reference derived cols
//                                          (e.g. Pfam_Max_Hits_Per_Single_Accession ≤ 4)
//   004 write_run_log                    — final marker
//
// Per-stage output dirs:
//   1-output  validated manifest snapshot
//   3-output  derived-augmented per-species TSV
//   5-output  + orthogroup-augmented
//   6-output  + blastp-augmented   (this is the "full evidence" per-species TSV)
//   2-output  filtered secretome   (subset of 6-output rows that pass the manifest)
//   4-output  run log
//
// Per-species final secretome filename: <phyloname>_<run_label>.tsv
// where run_label = "secretome_NNN[_<optional_name>]" (set by RUN-workflow.sh).
// =============================================================================

scripts_dir = "${projectDir}/scripts"

process validate_filter_manifest {
    publishDir "${params.output_dir}/1-output", mode: 'copy'

    input:
        path manifest_path

    output:
        path "${params.run_label}_validated_manifest.json", emit: validated_manifest
        path "${params.run_label}_log-validate_filter_manifest.log"

    script:
    """
    python3 ${scripts_dir}/001_ai-python-validate_filter_manifest.py \
        --manifest-path ${manifest_path} \
        --run-label ${params.run_label} \
        --output-dir .
    """
}

process augment_with_derived_columns {
    publishDir "${params.output_dir}/3-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( evidence_table )

    output:
        tuple val( phyloname ), path( "${phyloname}_${params.run_label}_derived_augmented.tsv" ), emit: augmented
        path "${phyloname}_${params.run_label}_log-augment_derived.log"

    script:
    """
    python3 ${scripts_dir}/003_ai-python-augment_with_derived_columns.py \
        --workflow-root ${projectDir}/.. \
        --filtered-tsv ${evidence_table} \
        --proteome-fasta ${params.proteome_dir}/${phyloname}-T1-proteome.aa \
        --pfam-long-format-tsv ${params.annotation_database_dir}/database_pfam/gigantic_annotations-database_pfam-${phyloname}.tsv \
        --run-label ${params.run_label} \
        --phyloname ${phyloname} \
        --output-dir .
    mv ${phyloname}_${params.run_label}_secretome.tsv ${phyloname}_${params.run_label}_derived_augmented.tsv
    """
}

process augment_with_orthogroups {
    publishDir "${params.output_dir}/5-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( input_tsv )

    output:
        tuple val( phyloname ), path( "${phyloname}_${params.run_label}_orthogroups_augmented.tsv" ), emit: augmented
        path "${phyloname}_${params.run_label}_log-augment_orthogroups.log"

    script:
    """
    python3 ${scripts_dir}/005_ai-python-augment_with_orthogroups.py \
        --workflow-root ${projectDir}/.. \
        --input-tsv ${input_tsv} \
        --orthogroups-tsv ${params.orthogroups_tsv} \
        --run-label ${params.run_label} \
        --phyloname ${phyloname} \
        --output-dir .
    """
}

process augment_with_blastp_top10 {
    publishDir "${params.output_dir}/6-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( input_tsv )

    output:
        tuple val( phyloname ), path( "${phyloname}_${params.run_label}_blastp_augmented.tsv" ), emit: augmented
        path "${phyloname}_${params.run_label}_log-augment_blastp.log"

    script:
    """
    python3 ${scripts_dir}/006_ai-python-augment_with_blastp_top10.py \
        --workflow-root ${projectDir}/.. \
        --input-tsv ${input_tsv} \
        --blastp-top-hits-tsv ${params.blastp_top_hits_dir}/${phyloname}_top_hits.tsv \
        --run-label ${params.run_label} \
        --phyloname ${phyloname} \
        --output-dir .
    """
}

process apply_filters_per_species {
    publishDir "${params.output_dir}/2-output", mode: 'copy'

    input:
        tuple val( phyloname ), path( augmented_tsv )
        path validated_manifest

    output:
        tuple val( phyloname ), path( "${phyloname}_${params.run_label}.tsv" ), emit: secretome
        path "${phyloname}_${params.run_label}_log-apply_filters.log"

    script:
    """
    python3 ${scripts_dir}/002_ai-python-apply_filters_per_species.py \
        --evidence-table ${augmented_tsv} \
        --manifest ${validated_manifest} \
        --run-label ${params.run_label} \
        --phyloname ${phyloname} \
        --output-dir .
    mv ${phyloname}_${params.run_label}_filtered.tsv ${phyloname}_${params.run_label}.tsv
    """
}

process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${scripts_dir}/004_ai-python-write_run_log.py \
        --workflow-name "filter_secretome-${params.run_label}" \
        --subproject-name "secretome" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// =============================================================================
// Workflow
// =============================================================================
workflow {
    // Step 1: validate manifest
    def manifest_file = file( params.filter_manifest_path )
    if ( !manifest_file.isAbsolute() ) {
        manifest_file = file( "${workflow.launchDir}/${params.filter_manifest_path}" )
    }
    validate_filter_manifest( manifest_file )

    // Per-species evidence-table input
    species_channel = Channel
        .fromPath( "${params.evidence_table_dir}/*_evidence_table.tsv" )
        .map { f ->
            def name = f.getName()
            def phyloname = name.replaceFirst( /_evidence_table\.tsv$/, '' )
            tuple( phyloname, f )
        }

    // Step 3: derived-column augment
    augment_with_derived_columns( species_channel )

    // Step 5: orthogroup augment
    augment_with_orthogroups( augment_with_derived_columns.out.augmented )

    // Step 6: BLASTP top-10 augment
    augment_with_blastp_top10( augment_with_orthogroups.out.augmented )

    // Step 2: apply filter manifest (now has all augmented cols available)
    apply_filters_per_species(
        augment_with_blastp_top10.out.augmented,
        validate_filter_manifest.out.validated_manifest
    )

    // Step 4: write run log (final marker after all secretomes land)
    write_run_log( apply_filters_per_species.out.secretome.collect() )
}
