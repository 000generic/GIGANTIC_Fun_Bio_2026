#!/usr/bin/env nextflow

/*
 * ==============================================================================
 * INTEGRATOR PIPELINE: SPECIES_X_ALL_ANNOTATIONS
 * ==============================================================================
 * GIGANTIC_1 NextFlow workflow that builds, per species, a proteome annotation
 * table: one row per protein sequence, with every per-gene feature GIGANTIC
 * produces joined onto the proteome spine (genomesDB STEP_4 sequence tables).
 *
 * Design: "Scripts Own the Data, NextFlow Manages Execution"
 * - Scripts read/write directly under OUTPUT_pipeline/
 * - Two phases:
 *     Phase 1 (once)      : structure-INVARIANT base tables  -> 1-output/_shared/
 *     Phase 2 (per struct): append structure-DEPENDENT OCL columns, full wide
 *                           table per species-tree structure -> 2-output/<structure>/
 * - The set of structures is user-configurable ("all" or a list); Script 000
 *   resolves it and fail-fast verifies each structure's OCL inputs exist.
 *
 * Pipeline:
 *   000 resolve_structures        -> structures.txt (channel of structure_NNN)
 *   001 build_invariant_base      -> 1-output/_shared (per-species base tables)
 *   002 build_per_structure_tables-> 2-output/<structure> (full wide tables) [fan-out]
 *   003 validate_results          -> 3-output (fail-fast, §36)
 *   004 write_run_log             -> ai/logs (§45)
 *
 * AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28
 * Human: Eric Edsinger
 * ==============================================================================
 */

params.help = false

if ( params.help ) {
    log.info """
    ==============================================================================
    GIGANTIC integrator - species_X_all_annotations
    ==============================================================================

    Usage:
        nextflow run ai/main.nf -params-file START_HERE-user_config.yaml

    All configuration is read from START_HERE-user_config.yaml:
      - run_label, species_set_name, structures (all | list), nr_top_n,
        annogroup_sources, orthogroups_ocl_run_label, annogroup_ocl_run_label
      - inputs.{spine_dir, gene_sizes_dir, hotspots_dir, nr_hits_dir,
                hmms_databases_dir, annogroups_dir, orthogroups_file,
                secretome_dir, dark_dir, gene_groups_ags_root,
                gene_families_ags_root, orthogroups_ocl_dir, annogroup_ocl_dir}
      - output.base_dir
    ==============================================================================
    """.stripIndent()
    exit 0
}

// ============================================================================
// PROCESS 000: RESOLVE STRUCTURE SET (and fail-fast verify OCL inputs exist)
// ============================================================================

process resolve_structures {
    label 'local'

    output:
        path "structures.txt", emit: structures

    script:
    """
    python3 ${projectDir}/scripts/000_ai-python-resolve_structures.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir} \\
        --output_list structures.txt
    """
}

// ============================================================================
// PROCESS 001: BUILD INVARIANT BASE TABLES (Phase 1, runs once)
// ============================================================================

process build_invariant_base {
    label 'local'
    cache false

    output:
        val true, emit: ready

    script:
    """
    python3 ${projectDir}/scripts/001_ai-python-build_invariant_base.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 002: BUILD PER-STRUCTURE WIDE TABLES (Phase 2, fan-out per structure)
// ============================================================================

process build_per_structure_tables {
    label 'local'
    cache false
    tag "${structure}"

    input:
        val structure
        val base_ready

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/002_ai-python-build_per_structure_tables.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir} \\
        --structure ${structure}
    """
}

// ============================================================================
// PROCESS 003: VALIDATE RESULTS (fail-fast per §36)
// ============================================================================

process validate_results {
    label 'local'
    cache false

    input:
        val all_structures_done

    output:
        val true, emit: done

    script:
    """
    python3 ${projectDir}/scripts/003_ai-python-validate_results.py \\
        --config ${projectDir}/../START_HERE-user_config.yaml \\
        --output_dir ${projectDir}/../${params.output.base_dir}
    """
}

// ============================================================================
// PROCESS 004: WRITE RUN LOG (per §45)
// ============================================================================

process write_run_log {
    label 'local'

    input:
        val previous_step_done

    output:
        val true, emit: log_complete

    script:
    """
    python3 ${projectDir}/scripts/004_ai-python-write_run_log.py \\
        --workflow-name "species_X_all_annotations" \\
        --subproject-name "integrator-BLOCK_species_X_all_annotations" \\
        --project-name "${params.species_set_name}" \\
        --status success
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Resolve the structure set (fail-fast if any OCL input missing).
    resolve_structures()

    // Build the structure-invariant base tables once.
    build_invariant_base()

    // One 002 task per resolved structure; each waits for the base tables.
    structures_ch = resolve_structures.out.structures
        .splitText()
        .map { it.trim() }
        .filter { it }

    build_per_structure_tables( structures_ch, build_invariant_base.out.ready.first() )

    // Barrier: validate only after every per-structure table is written.
    validate_results( build_per_structure_tables.out.done.collect() )

    // Write run log after validation passes.
    write_run_log( validate_results.out.done )
}

// Completion summary handled by RUN-workflow.sh (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
