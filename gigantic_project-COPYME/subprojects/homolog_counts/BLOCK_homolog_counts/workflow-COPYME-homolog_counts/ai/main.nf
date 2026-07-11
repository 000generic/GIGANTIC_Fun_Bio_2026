#!/usr/bin/env nextflow
/*
 * GIGANTIC homolog_counts - BLOCK homolog_counts Pipeline
 * AI: Claude Code | Opus 4.7 | 2026 May 20
 * Human: Eric Edsinger
 *
 * Purpose: Produce per-species70 homolog count tables from multiple upstream
 * GIGANTIC subprojects. One wide TSV per source:
 *   Feature_ID | Total_Count | Total_Species_Count | <70 species cols, alpha by phyloname>
 *
 * Scripts:
 *   001: Validate species70 manifest + emit canonical alphabetical phyloname column order
 *   002: Count orthogroups from orthogroups/BLOCK_orthohmm_GIGANTIC
 *   003: Count HGNC gene group homologs from trees_gene_groups
 *   004: Count curated gene family homologs from trees_gene_families
 *   005: Write run log
 *   006: Rewrite species column headers (short labels) - runs once per source
 *        count TSV, producing short-header variants in 6-/7-/8-output/.
 *
 * Scripts 002-004 are independent and run in parallel (all consume the species
 * column order from script 001 to guarantee identical column shape across TSVs).
 * Script 006 runs three times (once per source TSV), each downstream of its
 * corresponding count process.
 *
 * Symlinks for output_to_input/BLOCK_homolog_counts/ are created by
 * RUN-workflow.sh AFTER this pipeline completes.
 */

nextflow.enable.dsl = 2

// ============================================================================
// PARAMETERS (from config.yaml via nextflow.config + -params-file)
// ============================================================================
// All defaults live in nextflow.config; users edit START_HERE-user_config.yaml,
// not this file. Nested params (params.X.Y.Z) mirror the yaml shape.

// ============================================================================
// VALIDATE REQUIRED INPUTS
// ============================================================================

if ( !params.inputs.species70_phyloname_map || !file( params.inputs.species70_phyloname_map ).exists() ) {
    error """
    ========================================================================
    CONFIGURATION ERROR: species70_phyloname_map not set or file missing.

    Set inputs.species70_phyloname_map in START_HERE-user_config.yaml to the
    canonical species70 mapping file (columns: genus_species | phyloname | phyloname_taxonid).
    ========================================================================
    """.stripIndent()
}

// ============================================================================
// PROCESSES
// ============================================================================

/*
 * Process 1: Validate species70 manifest + emit canonical column order
 * Calls: scripts/001_ai-python-validate_species70_manifest.py
 *
 * The species_order output is the canonical column order shared by all
 * counting scripts to guarantee identical species column layout.
 */
process validate_species70_manifest {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    output:
        path "1-output/1_ai-species70_alphabetical_phylonames.tsv", emit: species_order
        path "1-output/1_ai-log-validate_species70_manifest.log"

    script:
    """
    mkdir -p 1-output

    python3 ${projectDir}/scripts/001_ai-python-validate_species70_manifest.py \\
        --workflow-root ${projectDir}/.. \\
        --phyloname-map ${params.inputs.species70_phyloname_map} \\
        --output-dir 1-output
    """
}

/*
 * Process 2: Count orthogroups from orthogroups/BLOCK_orthohmm
 * Calls: scripts/002_ai-python-count-orthogroups_orthohmm.py
 */
process count_orthogroups_orthohmm {
    label 'counting'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path species_order

    output:
        path "2-output/2_ai-counts-orthogroups_orthohmm.tsv", emit: counts
        path "2-output/2_ai-log-count-orthogroups_orthohmm.log"

    script:
    """
    mkdir -p 2-output

    python3 ${projectDir}/scripts/002_ai-python-count-orthogroups_orthohmm.py \\
        --workflow-root ${projectDir}/.. \\
        --species-order ${species_order} \\
        --orthogroups-dir ${params.inputs.orthogroups_orthohmm_dir} \\
        --output-dir 2-output
    """
}

/*
 * Process 3: Count HGNC gene group homologs from trees_gene_groups
 * Calls: scripts/003_ai-python-count-trees_gene_groups.py
 */
process count_trees_gene_groups {
    label 'counting'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path species_order

    output:
        path "3-output/3_ai-counts-trees_gene_groups.tsv", emit: counts
        path "3-output/3_ai-log-count-trees_gene_groups.log"

    script:
    """
    mkdir -p 3-output

    python3 ${projectDir}/scripts/003_ai-python-count-trees_gene_groups.py \\
        --workflow-root ${projectDir}/.. \\
        --species-order ${species_order} \\
        --gene-groups-dir ${params.inputs.trees_gene_groups_dir} \\
        --output-dir 3-output
    """
}

/*
 * Process 4: Count curated gene family homologs from trees_gene_families
 * Calls: scripts/004_ai-python-count-trees_gene_families.py
 */
process count_trees_gene_families {
    label 'counting'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path species_order

    output:
        path "4-output/4_ai-counts-trees_gene_families.tsv", emit: counts
        path "4-output/4_ai-log-count-trees_gene_families.log"

    script:
    """
    mkdir -p 4-output

    python3 ${projectDir}/scripts/004_ai-python-count-trees_gene_families.py \\
        --workflow-root ${projectDir}/.. \\
        --species-order ${species_order} \\
        --gene-families-dir ${params.inputs.trees_gene_families_dir} \\
        --output-dir 4-output
    """
}

/*
 * Process 6a: Rewrite species column headers (short labels) for orthohmm counts
 * Calls: scripts/006_ai-python-rewrite_species_column_headers.py
 */
process rewrite_short_headers_orthohmm {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path counts_tsv

    output:
        path "6-output/6_ai-counts-orthogroups_orthohmm-short_species_headers.tsv", emit: short_headers
        path "6-output/6_ai-log-rewrite_species_column_headers-orthohmm.log"

    script:
    """
    mkdir -p 6-output

    python3 ${projectDir}/scripts/006_ai-python-rewrite_species_column_headers.py \\
        --input-tsv ${counts_tsv} \\
        --output-tsv 6-output/6_ai-counts-orthogroups_orthohmm-short_species_headers.tsv \\
        > 6-output/6_ai-log-rewrite_species_column_headers-orthohmm.log 2>&1
    """
}

/*
 * Process 6b: Rewrite species column headers (short labels) for gene_groups counts
 * Calls: scripts/006_ai-python-rewrite_species_column_headers.py
 */
process rewrite_short_headers_gene_groups {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path counts_tsv

    output:
        path "7-output/7_ai-counts-trees_gene_groups-short_species_headers.tsv", emit: short_headers
        path "7-output/7_ai-log-rewrite_species_column_headers-gene_groups.log"

    script:
    """
    mkdir -p 7-output

    python3 ${projectDir}/scripts/006_ai-python-rewrite_species_column_headers.py \\
        --input-tsv ${counts_tsv} \\
        --output-tsv 7-output/7_ai-counts-trees_gene_groups-short_species_headers.tsv \\
        > 7-output/7_ai-log-rewrite_species_column_headers-gene_groups.log 2>&1
    """
}

/*
 * Process 6c: Rewrite species column headers (short labels) for gene_families counts
 * Calls: scripts/006_ai-python-rewrite_species_column_headers.py
 */
process rewrite_short_headers_gene_families {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path counts_tsv

    output:
        path "8-output/8_ai-counts-trees_gene_families-short_species_headers.tsv", emit: short_headers
        path "8-output/8_ai-log-rewrite_species_column_headers-gene_families.log"

    script:
    """
    mkdir -p 8-output

    python3 ${projectDir}/scripts/006_ai-python-rewrite_species_column_headers.py \\
        --input-tsv ${counts_tsv} \\
        --output-tsv 8-output/8_ai-counts-trees_gene_families-short_species_headers.tsv \\
        > 8-output/8_ai-log-rewrite_species_column_headers-gene_families.log 2>&1
    """
}

/*
 * Process 5: Write Run Log
 * Calls: scripts/005_ai-python-write_run_log.py
 *
 * Runs only after all three counting processes complete (input collects
 * their .counts emissions).
 */
process write_run_log {
    label 'local'

    publishDir "${projectDir}/../${params.output.base_dir}", mode: 'copy', overwrite: true

    input:
        path all_count_outputs

    output:
        path "5-output/5_ai-run_log.md", emit: run_log

    script:
    """
    mkdir -p 5-output

    python3 ${projectDir}/scripts/005_ai-python-write_run_log.py \\
        --workflow-name "homolog_counts" \\
        --subproject-name "homolog_counts" \\
        --project-name "${params.project.name}" \\
        --status success \\
        --output-dir 5-output
    """
}

// ============================================================================
// WORKFLOW
// ============================================================================

workflow {
    // Step 1: Validate species70 manifest (must run first; emits canonical column order)
    validate_species70_manifest()

    // Steps 2-4: Independent counters, run in parallel
    count_orthogroups_orthohmm( validate_species70_manifest.out.species_order )
    count_trees_gene_groups(   validate_species70_manifest.out.species_order )
    count_trees_gene_families( validate_species70_manifest.out.species_order )

    // Step 6 (a/b/c): Rewrite species column headers to short labels for each
    // source. Each process is downstream of its corresponding count process.
    // Outputs to 6-/7-/8-output/ (numbered to match the source count's N+4).
    rewrite_short_headers_orthohmm(    count_orthogroups_orthohmm.out.counts )
    rewrite_short_headers_gene_groups( count_trees_gene_groups.out.counts   )
    rewrite_short_headers_gene_families( count_trees_gene_families.out.counts )

    // Step 5: Run log (waits on all three counters AND all three short-header
    // rewrites, so the log reflects the complete pipeline state)
    all_outputs = count_orthogroups_orthohmm.out.counts
        .mix(
            count_trees_gene_groups.out.counts,
            count_trees_gene_families.out.counts,
            rewrite_short_headers_orthohmm.out.short_headers,
            rewrite_short_headers_gene_groups.out.short_headers,
            rewrite_short_headers_gene_families.out.short_headers,
        )
        .collect()

    write_run_log( all_outputs )
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
