#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Build the structure-invariant per-gene dark/hotspot/secretome feature lookup
# Human: Eric Edsinger

"""
Script 001 — Build the gene -> feature lookup (structure-invariant, runs once).

Orthogroup membership and per-gene features do NOT change with tree structure,
so this lookup is built a single time and reused by every per-structure task
(scripts 002/004). It joins three feature sources on the GIGANTIC sequence ID:

  - dark_proteome : Full_GIGANTIC_Gene_ID -> Status (DARK/ANNOTATED)
                    [join: full GIGANTIC ID, exact match]
  - secretome     : Protein_Identifier in filtered set -> Is_Secreted
                    [join: full GIGANTIC ID, exact match]
                    + evidence columns (SignalP/DeepLoc/Pfam) from the wide
                      evidence tables, for the gene-level drill-down (table 3)
  - hotspots      : (Genus_species, source_gene_field) -> Hotspot_ID
                    [join: per-species bare gene field; hotspot member IDs are
                     only unique within a species]

Species-set policy: UNION + availability flags. A species missing from a source
is recorded as not-available for that axis; its genes are never silently
dropped (per AI_BEHAVIOR.md zero-tolerance for silent artifacts).

Outputs (under OUTPUT_pipeline/_shared/1-output/):
  1_ai-gene_feature_lookup.tsv          one row per gene, all axes joined
  1_ai-feature_availability_summary.tsv per-species availability per axis

Fail-fast: exits 1 if ALL feature sources are missing/empty (no signal to join).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U


def list_species_files( directory: Path, suffix_marker: str, name_marker: str ) -> dict:
    """
    Return { species_or_phyloname_token : Path } for files in `directory`
    matching `suffix_marker` (a glob fragment). `name_marker` is the substring
    after which the species token appears in the filename.
    """
    tokens___paths = {}
    if not directory.is_dir():
        return tokens___paths
    for path in sorted( directory.glob( f"*{suffix_marker}*" ) ):
        if not path.is_file():
            continue
        token = U.species_label_from_filename( path.name, name_marker )
        tokens___paths[ token ] = path
    return tokens___paths


def load_dark( dark_dir: Path ):
    """full_id -> 'DARK'/'ANNOTATED'  ; plus the set of dark species (Genus_species)."""
    full_ids___statuses = {}
    dark_species = set()
    species___paths = list_species_files( dark_dir, "dark_proteome-", "dark_proteome-" )
    for genus_species, path in species___paths.items():
        dark_species.add( genus_species )
        with open( path, 'r' ) as input_dark:
            # Full_GIGANTIC_Gene_ID (...)\tSource_Gene_ID (...)\t...\tStatus (DARK if all three axes False else ANNOTATED)\t...
            # g_A1BG-t_NM_130786.4-p_NP_570602.2-n_Metazoa_..._Homo_sapiens\tA1BG\t...\tANNOTATED\t...
            header_line = input_dark.readline()
            header_ids___indices = U.build_header_index( header_line )
            index_full_id = header_ids___indices[ "Full_GIGANTIC_Gene_ID" ]
            index_status = header_ids___indices[ "Status" ]
            for line in input_dark:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                full_id = parts[ index_full_id ]
                status = parts[ index_status ]
                full_ids___statuses[ full_id ] = status
    return full_ids___statuses, dark_species


def load_secretome_membership( secretome_filtered_dir: Path ):
    """set of secreted full_ids ; plus the set of secretome species (Genus_species)."""
    secreted_full_ids = set()
    secretome_species = set()
    # Filtered filenames look like '<phyloname>_secretome_<filter_label>.tsv'
    for path in sorted( secretome_filtered_dir.glob( "*_secretome_*.tsv" ) ) if secretome_filtered_dir.is_dir() else []:
        phyloname = path.name.split( "_secretome_" )[ 0 ]
        secretome_species.add( U.genus_species_from_phyloname( phyloname ) )
        with open( path, 'r' ) as input_secretome:
            # Phyloname (...)\tProtein_Identifier (protein identifier from proteome FASTA word 1 of header)\t...
            # Metazoa_..._Homo_sapiens\tg_A1BG-t_...-n_Metazoa_..._Homo_sapiens\t...
            header_line = input_secretome.readline()
            header_ids___indices = U.build_header_index( header_line )
            index_protein_id = header_ids___indices[ "Protein_Identifier" ]
            for line in input_secretome:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                secreted_full_ids.add( parts[ index_protein_id ] )
    return secreted_full_ids, secretome_species


def load_secretome_evidence( secretome_evidence_dir: Path ):
    """
    full_id -> { signalp_call, signalp_probability, deeploc_extracellular,
                 deeploc_transmembrane, pfam_unique, pfam_total } ;
    plus the set of evidence species (Genus_species).
    Columns are selected by self-documenting header_ID (robust to column order).
    """
    full_ids___evidence = {}
    evidence_species = set()
    for path in sorted( secretome_evidence_dir.glob( "*_evidence_table.tsv" ) ) if secretome_evidence_dir.is_dir() else []:
        phyloname = path.name.replace( "_evidence_table.tsv", "" )
        evidence_species.add( U.genus_species_from_phyloname( phyloname ) )
        with open( path, 'r' ) as input_evidence:
            # Phyloname (...)\tProtein_Identifier (...)\t...\tdeeploc_Extracellular_Probability (...)\t...\tsignalp_fast_Call (...)\t...
            # Metazoa_..._Homo_sapiens\tg_A1BG-...\t...\t0.01\t...\tSP\t...
            header_line = input_evidence.readline()
            header_ids___indices = U.build_header_index( header_line )
            index_protein_id = header_ids___indices[ "Protein_Identifier" ]

            # Prefer signalp_fast_*, fall back to signalp_slow_*
            index_signalp_call = header_ids___indices.get( "signalp_fast_Call",
                                  header_ids___indices.get( "signalp_slow_Call" ) )
            index_signalp_prob = header_ids___indices.get( "signalp_fast_Probability",
                                  header_ids___indices.get( "signalp_slow_Probability" ) )
            index_extracellular = header_ids___indices.get( "deeploc_Extracellular_Probability" )
            index_transmembrane = header_ids___indices.get( "deeploc_Transmembrane_Probability" )
            index_pfam_unique = header_ids___indices.get( "pfam_Unique_Annotation_Count" )
            index_pfam_total = header_ids___indices.get( "pfam_Hit_Count" )

            def field( parts, idx ):
                return parts[ idx ] if ( idx is not None and idx < len( parts ) ) else ""

            for line in input_evidence:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                full_id = parts[ index_protein_id ]
                full_ids___evidence[ full_id ] = {
                    "signalp_call": field( parts, index_signalp_call ),
                    "signalp_probability": field( parts, index_signalp_prob ),
                    "deeploc_extracellular": field( parts, index_extracellular ),
                    "deeploc_transmembrane": field( parts, index_transmembrane ),
                    "pfam_unique": field( parts, index_pfam_unique ),
                    "pfam_total": field( parts, index_pfam_total ),
                }
    return full_ids___evidence, evidence_species


def load_hotspots( hotspots_dir: Path ):
    """
    ( genus_species, source_gene_field ) -> Hotspot_ID ; plus hotspot species set.
    Hotspot member gene IDs are the bare gene field and are only unique within
    a species, so the key is keyed on ( species, gene_field ).
    """
    species_genes___hotspot_ids = {}
    hotspot_species = set()
    species___paths = list_species_files( hotspots_dir, "hotspots-", "hotspots-" )
    for genus_species, path in species___paths.items():
        hotspot_species.add( genus_species )
        with open( path, 'r' ) as input_hotspots:
            # Hotspot_ID (...)\tChromosome (...)\tHotspot_Start (...)\tHotspot_End (...)\tParalog_Count (...)\tMember_Source_Gene_IDs (comma delimited Source_Gene_IDs ...)
            # hotspot_e1e-60_w20_Homo_sapiens_1\tchr1\t...\t3\tOR4F5,OR4F29,OR4F16
            header_line = input_hotspots.readline()
            header_ids___indices = U.build_header_index( header_line )
            index_hotspot_id = header_ids___indices[ "Hotspot_ID" ]
            index_members = header_ids___indices[ "Member_Source_Gene_IDs" ]
            for line in input_hotspots:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                hotspot_id = parts[ index_hotspot_id ]
                members = parts[ index_members ] if index_members < len( parts ) else ""
                for source_gene_field in members.split( ',' ):
                    source_gene_field = source_gene_field.strip()
                    if source_gene_field:
                        species_genes___hotspot_ids[ ( genus_species, source_gene_field ) ] = hotspot_id
    return species_genes___hotspot_ids, hotspot_species


def main():
    parser = argparse.ArgumentParser( description = "Build the structure-invariant gene->feature lookup" )
    parser.add_argument( '--config', required = True, help = "Path to START_HERE-user_config.yaml" )
    parser.add_argument( '--output_dir', required = True, help = "OUTPUT_pipeline directory" )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    inputs = config[ "inputs" ]

    input_dark_dir = U.resolve_input_path( workflow_root, inputs[ "dark_proteome_dir" ] )
    input_hotspots_dir = U.resolve_input_path( workflow_root, inputs[ "hotspots_dir" ] )
    input_secretome_filtered_dir = U.resolve_input_path( workflow_root, inputs[ "secretome_filtered_dir" ] )
    input_secretome_evidence_dir = U.resolve_input_path( workflow_root, inputs[ "secretome_evidence_dir" ] )

    print( "[001] Building gene->feature lookup (structure-invariant)" )
    print( f"[001]   dark_proteome_dir       : {input_dark_dir}" )
    print( f"[001]   hotspots_dir            : {input_hotspots_dir}" )
    print( f"[001]   secretome_filtered_dir  : {input_secretome_filtered_dir}" )
    print( f"[001]   secretome_evidence_dir  : {input_secretome_evidence_dir}" )

    full_ids___statuses, dark_species = load_dark( input_dark_dir )
    secreted_full_ids, secretome_species = load_secretome_membership( input_secretome_filtered_dir )
    full_ids___evidence, evidence_species = load_secretome_evidence( input_secretome_evidence_dir )
    species_genes___hotspot_ids, hotspot_species = load_hotspots( input_hotspots_dir )

    print( f"[001]   dark genes: {len( full_ids___statuses )} across {len( dark_species )} species" )
    print( f"[001]   secreted genes: {len( secreted_full_ids )} across {len( secretome_species )} species" )
    print( f"[001]   evidence genes: {len( full_ids___evidence )} across {len( evidence_species )} species" )
    print( f"[001]   hotspot member genes: {len( species_genes___hotspot_ids )} across {len( hotspot_species )} species" )

    # ------------------------------------------------------------------
    # Fail-fast: at least one feature source must carry data (§36)
    # ------------------------------------------------------------------
    if not ( full_ids___statuses or secreted_full_ids or full_ids___evidence or species_genes___hotspot_ids ):
        print( "CRITICAL ERROR: no feature data found in ANY source.", file = sys.stderr )
        print( "  Checked dark / hotspots / secretome(filtered) / secretome(evidence).", file = sys.stderr )
        print( "  Verify the input paths in START_HERE-user_config.yaml resolve to populated", file = sys.stderr )
        print( "  output_to_input/ directories (the upstream subprojects must have run).", file = sys.stderr )
        sys.exit( 1 )

    # ------------------------------------------------------------------
    # Universe of genes = union of full IDs seen in dark + secreted + evidence
    # (dark covers all classified genes; evidence covers all proteins).
    # ------------------------------------------------------------------
    universe_full_ids = set( full_ids___statuses.keys() ) | secreted_full_ids | set( full_ids___evidence.keys() )
    print( f"[001]   gene universe (union): {len( universe_full_ids )}" )

    output_dir = Path( args.output_dir ) / "_shared" / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )

    # ------------------------------------------------------------------
    # Write the lookup table
    # ------------------------------------------------------------------
    output_base = Path( args.output_dir )
    output_lookup_path = U.timestamped_output_path( output_dir, "1_ai-gene_feature_lookup", output_base )
    header_columns = [
        "Full_GIGANTIC_Gene_ID (complete GIGANTIC sequence identifier g_..-t_..-p_..-n_phyloname)",
        "Genus_Species (Genus_species parsed from the phyloname n_ field of the sequence identifier)",
        "Source_Gene_Field (bare gene field parsed from g_ prefix; used to join hotspots within a species)",
        "Dark_Available (True if the gene's species has a dark_proteome classification file)",
        "Is_Dark (True if dark_proteome Status is DARK; False if ANNOTATED; NA if species not available)",
        "Hotspot_Available (True if the gene's species has a hotspots file)",
        "In_Hotspot (True if the gene is a member of any hotspot in its species; False otherwise; NA if species not available)",
        "Hotspot_ID (deterministic hotspot identifier the gene belongs to; empty if not in a hotspot; NA if species not available)",
        "Secretome_Available (True if the gene's species has a filtered secretome file)",
        "Is_Secreted (True if the gene is in the filtered secretome set; False otherwise; NA if species not available)",
        "SignalP_Call (signalp_fast Call from the secretome evidence table; empty if no evidence)",
        "SignalP_Probability (signalp_fast Probability from the secretome evidence table; empty if no evidence)",
        "DeepLoc_Extracellular_Probability (deeploc Extracellular probability from the secretome evidence table; empty if no evidence)",
        "DeepLoc_Transmembrane_Probability (deeploc Transmembrane probability from the secretome evidence table; empty if no evidence)",
        "Pfam_Unique_Accessions (pfam unique annotation count from the secretome evidence table; empty if no evidence)",
        "Pfam_Total_Hits (pfam total hit count from the secretome evidence table; empty if no evidence)",
    ]

    rows_written = 0
    with open( output_lookup_path, 'w' ) as output_lookup:
        output_lookup.write( '\t'.join( header_columns ) + '\n' )
        for full_id in sorted( universe_full_ids ):
            source_gene_field, phyloname, genus_species = U.parse_full_gigantic_id( full_id )
            if genus_species is None:
                # Sequence ID without the expected markers — record minimally,
                # all axes NA (surfaced rather than dropped).
                genus_species = ""
                source_gene_field = ""

            dark_available = genus_species in dark_species
            if dark_available:
                is_dark = "True" if full_ids___statuses.get( full_id ) == "DARK" else "False"
            else:
                is_dark = "NA"

            hotspot_available = genus_species in hotspot_species
            if hotspot_available:
                hotspot_id = species_genes___hotspot_ids.get( ( genus_species, source_gene_field ), "" )
                in_hotspot = "True" if hotspot_id else "False"
            else:
                hotspot_id = "NA"
                in_hotspot = "NA"

            secretome_available = genus_species in secretome_species
            if secretome_available:
                is_secreted = "True" if full_id in secreted_full_ids else "False"
            else:
                is_secreted = "NA"

            evidence = full_ids___evidence.get( full_id, {} )

            output = '\t'.join( [
                full_id,
                genus_species,
                source_gene_field,
                str( dark_available ),
                is_dark,
                str( hotspot_available ),
                in_hotspot,
                hotspot_id,
                str( secretome_available ),
                is_secreted,
                evidence.get( "signalp_call", "" ),
                evidence.get( "signalp_probability", "" ),
                evidence.get( "deeploc_extracellular", "" ),
                evidence.get( "deeploc_transmembrane", "" ),
                evidence.get( "pfam_unique", "" ),
                evidence.get( "pfam_total", "" ),
            ] ) + '\n'
            output_lookup.write( output )
            rows_written += 1

    print( f"[001]   wrote {rows_written} rows -> {output_lookup_path}" )

    # ------------------------------------------------------------------
    # Write per-species availability summary (documents union + flags)
    # ------------------------------------------------------------------
    all_species = sorted( dark_species | hotspot_species | secretome_species | evidence_species )
    output_availability_path = U.timestamped_output_path( output_dir, "1_ai-feature_availability_summary", output_base )
    availability_header = [
        "Genus_Species (species present in at least one feature source)",
        "Dark_Available (True if a dark_proteome file exists for this species)",
        "Hotspot_Available (True if a hotspots file exists for this species)",
        "Secretome_Filtered_Available (True if a filtered secretome file exists for this species)",
        "Secretome_Evidence_Available (True if a secretome evidence table exists for this species)",
    ]
    with open( output_availability_path, 'w' ) as output_availability:
        output_availability.write( '\t'.join( availability_header ) + '\n' )
        for genus_species in all_species:
            output = '\t'.join( [
                genus_species,
                str( genus_species in dark_species ),
                str( genus_species in hotspot_species ),
                str( genus_species in secretome_species ),
                str( genus_species in evidence_species ),
            ] ) + '\n'
            output_availability.write( output )

    print( f"[001]   wrote availability for {len( all_species )} species -> {output_availability_path}" )
    print( "[001] done." )


if __name__ == '__main__':
    main()
