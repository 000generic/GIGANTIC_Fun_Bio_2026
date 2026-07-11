#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * SEQUENCE_GROUPS_X_SPECIES : RESOLVE SEQUENCE-GROUP SETS ONTO THE SPECIES TREE
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow. ONE run resolves MANY producers' sequence-group
 * sets (orthogroups, annogroups, gene families, gene groups, ...) onto the species-
 * tree clades. Each producer listed in START_HERE-user_config.yaml `producers:` is
 * its OWN process chain (a separate execution of 001->002/003/004), writing into its
 * own per-producer output subtree OUTPUT_pipeline/<group_set_label>/. Producer-
 * agnostic: Script 001 adapts each producer's native output into a STANDARD
 * membership; everything downstream reads only that.
 *
 * Per producer:
 *   001 adapt_membership          -> <label>/1-output  standard membership
 *   002 species_tree_deconvolution -> <label>/2-output  member sequence+species counts per clade
 *   003 per_species_sequence_map  -> <label>/3-output  member sequence ids per species
 *   004 composite_clades          -> <label>/4-output  composite clades (4 algorithms)
 * 002/003/004 are independent (all read that producer's membership) -> run in parallel.
 * 005 write_run_log runs ONCE after all producers complete (gigantic_conventions §45).
 *
 * The shared inputs (clade_species_mappings, composite_clades_manifest) and the
 * composite_clades building-block block are read from config by every producer.
 *
 * AI: Claude Code | Opus 4.8 | 2026 June 28  (multi-producer: Claude | Opus 4.8 | 2026 July 08)
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    GIGANTIC sequence_groups_X_species - resolve sequence-group sets onto the species tree
    Usage: bash RUN-workflow.sh   (edit START_HERE-user_config.yaml first)
    """.stripIndent()
    exit 0
}

// All configuration comes from START_HERE-user_config.yaml via -params-file.
// projectDir is ai/, so the workflow root is ${projectDir}/.. .
// Each producer spec is a map: { producer, group_set_label, producer_membership, group_attributes }.

// ============================================================================
// PROCESS 001: ADAPT MEMBERSHIP (producer -> standard membership), per producer
// ============================================================================
process adapt_membership {
    label 'local'
    tag "${spec.group_set_label}"

    input:
        val spec

    output:
        tuple val( spec ), val( true ), emit: done

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-adapt_sequence_group_membership.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --workflow_root ${projectDir}/.. \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${spec.group_set_label} \\
        --producer ${spec.producer} \\
        --group_set_label ${spec.group_set_label} \\
        --producer_membership '${spec.producer_membership}'
    """
}

// ============================================================================
// PROCESS 002: SPECIES-TREE DECONVOLUTION (sequence + species counts per clade)
// ============================================================================
process species_tree_deconvolution {
    tag "${spec.group_set_label}"

    input:
        tuple val( spec ), val( ready )

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-species_tree_deconvolution.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --workflow_root ${projectDir}/.. \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${spec.group_set_label} \\
        --group_set_label ${spec.group_set_label} \\
        --group_attributes '${spec.group_attributes}'
    """
}

// ============================================================================
// PROCESS 003: PER-SPECIES SEQUENCE MAP
// ============================================================================
process per_species_sequence_map {
    tag "${spec.group_set_label}"

    input:
        tuple val( spec ), val( ready )

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-per_species_sequence_map.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --workflow_root ${projectDir}/.. \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${spec.group_set_label} \\
        --group_set_label ${spec.group_set_label} \\
        --group_attributes '${spec.group_attributes}'
    """
}

// ============================================================================
// PROCESS 006: BUILD ANNOTATION INDEX (once; cross-producer sequence -> annotations)
// ============================================================================
// Builds ONE sequence -> annotation index (PFAM/PANTHER/GO/Gene_Families/Gene_Groups)
// that Script 004 joins onto every producer's composite-clades detail tables. Runs
// once and gates all composite_clades tasks.
process build_annotation_index {
    input:
        val ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/006_ai-python-build_annotation_index.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --workflow_root ${projectDir}/.. \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: COMPOSITE CLADES (four algorithms) + detail-table annotations
// ============================================================================
process composite_clades {
    tag "${spec.group_set_label}"

    input:
        tuple val( spec ), val( ready ), val( index_ready )

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-composite_clades.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --workflow_root ${projectDir}/.. \\
        --output_dir ${projectDir}/../${params.output.base_dir}/${spec.group_set_label} \\
        --group_set_label ${spec.group_set_label} \\
        --group_attributes '${spec.group_attributes}'
    """
}

// ============================================================================
// PROCESS 005: WRITE RUN LOG (once, after all producers finish)
// ============================================================================
process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \
        --workflow-name "resolve_groups" \
        --subproject-name "sequence_groups_X_species-BLOCK_resolve_groups" \
        --project-name "${params.project_name}" \
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================
workflow {
    // One process chain per producer spec; producers run in parallel.
    producers = Channel.fromList( params.producers )
    adapt_membership( producers )
    species_tree_deconvolution( adapt_membership.out.done )
    per_species_sequence_map( adapt_membership.out.done )

    // The cross-producer annotation index is built once and gates every producer's
    // composite_clades task (which joins it onto the detail tables).
    build_annotation_index( Channel.of( true ) )
    composite_clades( adapt_membership.out.done.combine( build_annotation_index.out.done ) )

    // Run log once every producer's three overlays complete.
    write_run_log(
        species_tree_deconvolution.out.done
            .mix( per_species_sequence_map.out.done, composite_clades.out.done )
            .collect()
    )
}

// Completion summary + output_to_input symlinks handled by RUN-workflow.sh.
