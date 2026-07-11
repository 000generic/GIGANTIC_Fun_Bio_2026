#!/usr/bin/env python3
# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Phase 1 — build per-species proteome annotation base tables (every structure-invariant per-gene feature joined onto the proteome spine)
# Human: Eric Edsinger

"""
Script 001 — Phase 1: per-species proteome annotation BASE tables (invariant).

The spine is the genomesDB STEP_4 per-species sequence table: one row per
protein, with the full GIGANTIC identifier + amino acid sequence. Every
structure-INVARIANT per-gene feature is joined onto the spine here, once, and
written to OUTPUT_pipeline/1-output/_shared/<phyloname>-proteome_annotations-base.tsv.
The structure-DEPENDENT OCL columns are added later, per structure, by Script 002.

Sources joined (join key in parentheses):
  - genomesDB sequence table  (spine)                    full GIGANTIC ID
  - gene_sizes                (Gene/CDS/Protein size)    bare g_ field + species
  - hotspots                  (hotspot membership)       bare g_ field + species
  - one_direction_homologs    (top-N nr DIAMOND hits)    full GIGANTIC ID
  - annotations_hmms          (Pfam / IPR-GO / PANTHER-GO / PANTHER)  full GIGANTIC ID
  - annogroups                (pfam / go / panther membership)        full GIGANTIC ID
  - orthogroups               (orthogroup id + size)     full GIGANTIC ID
  - secretome                 (SignalP + DeepLoc)        full GIGANTIC ID
  - trees_gene_groups         (AGS membership list)      full GIGANTIC ID in AGS FASTA
  - trees_gene_families       (AGS membership list)      full GIGANTIC ID in AGS FASTA
  - dark_proteomes            (DARK / ANNOTATED)         full GIGANTIC ID

Species-set policy: every protein in the spine becomes a row. A source that
does not cover a species (gene_sizes / hotspots = 64 of 70) writes NA for that
species' proteins plus an availability flag — never a silent drop (per
AI_BEHAVIOR.md). Sources not present for an individual protein write NA.

Fail-fast: exits 1 if the spine, orthogroups file, or any configured annogroup
membership file is missing.
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_species_X_all_annotations as U


# ---------------------------------------------------------------------------
# BASE table column schema (self-documenting headers, §34). Single source of
# truth for Script 002 (which appends OCL columns) and Script 003 (validation).
# Annotation types use four columns each: Species_Count, Sequence_Count,
# Identifiers, Names (aligned with orthogroups_X_all_annotations).
# ---------------------------------------------------------------------------
BASE_HEADER_COLUMNS = [
    "Sequence_Identifier (full GIGANTIC protein identifier g_gene-t_rna-p_protein-n_phyloname; the per-protein join key)",
    "Phyloname (GIGANTIC phyloname for the species)",
    "Genus_Species (Genus_species derived from the phyloname)",
    "Sequence_Length (protein length in residues from the genomesDB sequence table)",
    "Protein_Sequence (amino acid sequence single letter codes no whitespace)",
    "Gene_Size_BP (genomic span in base pairs from gene_sizes; NA if gene_sizes unavailable for the species or gene)",
    "CDS_Size_BP (coding sequence length in base pairs from gene_sizes; NA if unavailable)",
    "Protein_Size_AA (protein length in amino acids from gene_sizes computed as CDS divided by 3; NA if unavailable)",
    "Gene_Sizes_Available (yes if the gene_sizes per species table exists for this species else no)",
    "In_Hotspot (yes if this gene is a member of at least one hotspot else no; NA if hotspots unavailable for the species)",
    "Hotspot_IDs (comma delimited hotspot identifiers this gene belongs to; NA if none or unavailable)",
    "Hotspot_Paralog_Counts (comma delimited paralog counts parallel to Hotspot_IDs; NA if none or unavailable)",
    "Hotspots_Available (yes if the hotspots per species table exists for this species else no)",
    "Top_3_NR_Hits (top 3 NCBI nr DIAMOND BLASTp hits semicolon delimited each as hit header text with e-value; NA if no hits)",
] + U.feature_header_columns( "Pfam", "Pfam domain" ) + U.feature_header_columns( "InterPro_GO", "InterProScan GO term" ) + U.feature_header_columns( "PANTHER_GO", "PANTHER GO term" ) + U.feature_header_columns( "PANTHER", "PANTHER family" ) + [
    "Annotations_HMMs_Available (yes if the annotations_hmms per species tables exist for this species else no)",
] + U.feature_header_columns( "Annogroups_Pfam", "pfam annogroup" ) + U.feature_header_columns( "Annogroups_GO", "go annogroup" ) + U.feature_header_columns( "Annogroups_PANTHER", "panther annogroup" ) + [
    "Orthogroup_ID (OrthoHMM orthogroup identifier this protein belongs to; NA if the protein is in no orthogroup)",
    "Orthogroup_Member_Protein_Count (number of member proteins in the orthogroup; NA if no orthogroup)",
    "Orthogroup_Species_Count (number of distinct species in the orthogroup; NA if no orthogroup)",
    "Secretome_SignalP_Call (signalp slow model call one of Sec/SPI Sec/SPII Tat/SPI None; NA if secretome unavailable)",
    "Secretome_SignalP_Probability (signalp slow model probability; NA if unavailable)",
    "Secretome_DeepLoc_Localization (deeploc predicted subcellular localization; NA if unavailable)",
    "Secretome_Available (yes if the secretome evidence table exists for this species else no)",
] + U.feature_header_columns( "Gene_Groups", "trees_gene_groups gene group", names_blank = True ) + U.feature_header_columns( "Gene_Families", "trees_gene_families gene family", names_blank = True ) + [
    "Dark_Status (DARK or ANNOTATED from dark_proteomes; NA if unavailable)",
    "Dark_Proteome_Available (yes if the dark proteome table exists for this species else no)",
]


# ===========================================================================
# GLOBAL loaders (read once, used for every species)
# ===========================================================================

def load_orthogroups( orthogroups_path: Path ):
    """
    Read the headerless orthogroups table once and return three maps:
      proteins___orthogroups        : member full GIGANTIC ID -> orthogroup id
      orthogroups___member_counts   : orthogroup id -> member protein count
      orthogroups___species_counts  : orthogroup id -> distinct species count
    """
    proteins___orthogroups = {}
    orthogroups___member_counts = {}
    orthogroups___species_counts = {}
    with open( orthogroups_path, 'r' ) as input_orthogroups:
        # Headerless: OG_ID\tmember_full_id\tmember_full_id...
        for line in input_orthogroups:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ 0 ]
            members = [ member for member in parts[ 1: ] if member ]
            orthogroups___member_counts[ orthogroup_id ] = len( members )
            species = set()
            for member in members:
                proteins___orthogroups[ member ] = orthogroup_id
                ( _gene, _phyloname, genus_species ) = U.parse_full_gigantic_id( member )
                if genus_species is not None:
                    species.add( genus_species )
            orthogroups___species_counts[ orthogroup_id ] = len( species )
    return proteins___orthogroups, orthogroups___member_counts, orthogroups___species_counts


def load_annogroup_map( map_path: Path, source_label: str ) -> dict:
    """Build { Annogroup_ID: name } for every row in the annogroup MAP."""
    annogroup_ids___names = {}
    with open( map_path, 'r' ) as input_map:
        # Annogroup_ID (...)\tSource (...)\tAnnogroup_Type (...)\tDefining_Features (...)\tAnnotation_Definitions (...)
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            annogroup_type = parts[ index_type ]
            definitions = parts[ index_definitions ] if index_definitions < len( parts ) else ''
            name = U.annogroup_name_from_map_fields( annogroup_type, definitions )
            U.guard_name( source_label, annogroup_id, name )
            annogroup_ids___names[ annogroup_id ] = name
    if not annogroup_ids___names:
        print( f"CRITICAL ERROR: no annogroups parsed from {map_path}", file = sys.stderr )
        sys.exit( 1 )
    return annogroup_ids___names


def load_annogroup_membership( membership_path: Path ) -> dict:
    """
    Read one annogroup-source membership file once -> sequence id -> [ annogroup ids ].
    A sequence appears once per annogroup it belongs to (feature / combination /
    architecture / absent), so the per-sequence list is the union across types.
    """
    sequences___annogroups = defaultdict( list )
    with open( membership_path, 'r' ) as input_membership:
        # Sequence_Identifier (...)\tGenus_Species (...)\tAnnogroup_ID (...)\tAnnogroup_Type (...)\tMember_Architecture_Coordinates (...)
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequences___annogroups[ parts[ index_sequence ] ].append( parts[ index_annogroup ] )
    return sequences___annogroups


def load_ags_memberships( ags_files, name_from_path ) -> dict:
    """
    Scan a set of AGS FASTA (.aa) files -> sequence id -> set( ags names ).

    `name_from_path` maps an AGS file Path to its gene-group / gene-family name.
    AGS files contain both reference seed headers (rgs_*) and discovered homolog
    headers (full GIGANTIC IDs); only the latter match the proteome spine, so the
    rgs_ keys are simply never queried. The first whitespace token of each '>'
    header is taken as the identifier.
    """
    sequences___ags_names = defaultdict( set )
    for ags_file in ags_files:
        ags_name = name_from_path( ags_file )
        with open( ags_file, 'r' ) as input_ags:
            for line in input_ags:
                if not line.startswith( '>' ):
                    continue
                identifier = line[ 1: ].strip().split()[ 0 ]
                sequences___ags_names[ identifier ].add( ags_name )
    return sequences___ags_names


# ===========================================================================
# PER-SPECIES loaders (built and freed per species)
# ===========================================================================

def load_gene_sizes_for_species( gene_sizes_path: Path ) -> dict:
    """source_gene_field -> ( gene_size_bp, cds_size_bp, protein_size_aa )."""
    gene_fields___sizes = {}
    with open( gene_sizes_path, 'r' ) as input_gene_sizes:
        # Source_Gene_ID (...)\tGIGANTIC_Identifier (...)\t...\tGene_Size (...)\tCDS_Size (...)\tProtein_Size (...)\t...
        header_ids___indices = U.build_header_index( input_gene_sizes.readline() )
        index_gene = header_ids___indices[ "Source_Gene_ID" ]
        index_gene_size = header_ids___indices[ "Gene_Size" ]
        index_cds_size = header_ids___indices[ "CDS_Size" ]
        index_protein_size = header_ids___indices[ "Protein_Size" ]
        for line in input_gene_sizes:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            gene_fields___sizes[ parts[ index_gene ] ] = (
                parts[ index_gene_size ], parts[ index_cds_size ], parts[ index_protein_size ]
            )
    return gene_fields___sizes


def load_hotspots_for_species( hotspots_path: Path ) -> dict:
    """source_gene_field -> [ ( hotspot_id, paralog_count ), ... ] (gene-indexed)."""
    gene_fields___hotspots = defaultdict( list )
    with open( hotspots_path, 'r' ) as input_hotspots:
        # Hotspot_ID (...)\tChromosome (...)\tHotspot_Start (...)\tHotspot_End (...)\tParalog_Count (...)\tMember_Source_Gene_IDs (...)
        header_ids___indices = U.build_header_index( input_hotspots.readline() )
        index_hotspot = header_ids___indices[ "Hotspot_ID" ]
        index_paralogs = header_ids___indices[ "Paralog_Count" ]
        index_members = header_ids___indices[ "Member_Source_Gene_IDs" ]
        for line in input_hotspots:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            hotspot_id = parts[ index_hotspot ]
            paralog_count = parts[ index_paralogs ]
            parts_members = parts[ index_members ].split( ',' )
            for member_gene_field in parts_members:
                member_gene_field = member_gene_field.strip()
                if member_gene_field:
                    gene_fields___hotspots[ member_gene_field ].append( ( hotspot_id, paralog_count ) )
    return gene_fields___hotspots


def load_nr_hits_for_species( nr_path: Path, top_n: int ) -> dict:
    """query full GIGANTIC ID -> formatted top-N nr hits cell."""
    sequences___nr_hits = {}
    with open( nr_path, 'r' ) as input_nr:
        # Query_Sequence_ID (...)\tTop_10_Hit_IDs (...)\tTop_10_Hit_Headers (...)\tTop_10_Hit_E_Values (...)\t...
        header_ids___indices = U.build_header_index( input_nr.readline() )
        index_query = header_ids___indices[ "Query_Sequence_ID" ]
        index_ids = header_ids___indices[ "Top_10_Hit_IDs" ]
        index_headers = header_ids___indices[ "Top_10_Hit_Headers" ]
        index_evalues = header_ids___indices[ "Top_10_Hit_E_Values" ]
        for line in input_nr:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequences___nr_hits[ parts[ index_query ] ] = U.format_top_nr_hits(
                parts[ index_ids ], parts[ index_headers ], parts[ index_evalues ], top_n
            )
    return sequences___nr_hits


def load_hmms_accession_table_for_species( table_path: Path ) -> dict:
    """
    annotations_hmms consolidated per-species table (pfam or panther) ->
    sequence id -> [ ( accession, description ), ... ] deduplicated by accession.
    """
    sequences___hits = defaultdict( list )
    seen = set()
    with open( table_path, 'r' ) as input_table:
        # Phyloname (...)\tSequence_Identifier (...)\tDomain_Start (...)\tDomain_Stop (...)\tDatabase_Name (...)\tAnnotation_Identifier (...)\tAnnotation_Details (...)
        header_ids___indices = U.build_header_index( input_table.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_accession = header_ids___indices[ "Annotation_Identifier" ]
        index_details = header_ids___indices[ "Annotation_Details" ]
        for line in input_table:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_identifier = parts[ index_sequence ]
            accession = parts[ index_accession ]
            details = parts[ index_details ] if index_details < len( parts ) else ""
            dedupe_key = ( sequence_identifier, accession )
            if dedupe_key in seen:
                continue
            seen.add( dedupe_key )
            U.guard_name( "Pfam/PANTHER", accession, details )
            sequences___hits[ sequence_identifier ].append( ( accession, details ) )
    return sequences___hits


def load_hmms_go_table_for_species( table_path: Path ):
    """
    annotations_hmms consolidated GO table -> two maps:
      sequences___interpro_go : sequence id -> [ ( clean GO id, GO name ), ... ]
      sequences___panther_go  : sequence id -> [ ( clean GO id, GO name ), ... ]
    """
    sequences___interpro_go = defaultdict( list )
    sequences___panther_go = defaultdict( list )
    seen = set()
    with open( table_path, 'r' ) as input_table:
        # Phyloname (...)\tSequence_Identifier (...)\t...\tAnnotation_Identifier (GO:NNNNNNN(source))\tAnnotation_Details (...)
        header_ids___indices = U.build_header_index( input_table.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_accession = header_ids___indices[ "Annotation_Identifier" ]
        index_details = header_ids___indices[ "Annotation_Details" ]
        for line in input_table:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_identifier = parts[ index_sequence ]
            ( source, clean_go ) = U.split_go_identifier_source( parts[ index_accession ] )
            go_name = parts[ index_details ] if index_details < len( parts ) else clean_go
            dedupe_key = ( sequence_identifier, source, clean_go )
            if dedupe_key in seen:
                continue
            seen.add( dedupe_key )
            U.guard_name( "GO", clean_go, go_name )
            if source == "InterPro":
                sequences___interpro_go[ sequence_identifier ].append( ( clean_go, go_name ) )
            elif source == "PANTHER":
                sequences___panther_go[ sequence_identifier ].append( ( clean_go, go_name ) )
            else:
                continue
    return sequences___interpro_go, sequences___panther_go


def load_secretome_for_species( secretome_path: Path ) -> dict:
    """sequence id -> ( signalp_slow_call, signalp_slow_probability, deeploc_localization )."""
    sequences___secretome = {}
    with open( secretome_path, 'r' ) as input_secretome:
        # Phyloname (...)\tProtein_Identifier (...)\t...\tdeeploc_Localizations (...)\t...\tsignalp_slow_Call (...)\tsignalp_slow_Probability (...)
        header_ids___indices = U.build_header_index( input_secretome.readline() )
        index_protein = header_ids___indices[ "Protein_Identifier" ]
        index_call = header_ids___indices[ "signalp_slow_Call" ]
        index_probability = header_ids___indices[ "signalp_slow_Probability" ]
        index_localization = header_ids___indices[ "deeploc_Localizations" ]
        for line in input_secretome:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            call = parts[ index_call ] if index_call < len( parts ) else U.NA
            probability = parts[ index_probability ] if index_probability < len( parts ) else U.NA
            localization = parts[ index_localization ] if index_localization < len( parts ) else U.NA
            sequences___secretome[ parts[ index_protein ] ] = ( call, probability, localization )
    return sequences___secretome


def load_dark_for_species( dark_path: Path ) -> dict:
    """sequence id -> Status (DARK or ANNOTATED)."""
    sequences___dark_status = {}
    with open( dark_path, 'r' ) as input_dark:
        # Full_GIGANTIC_Gene_ID (...)\tSource_Gene_ID (...)\t...\tStatus (...)\tAnnotation_Sources_CSV (...)
        header_ids___indices = U.build_header_index( input_dark.readline() )
        index_full_id = header_ids___indices[ "Full_GIGANTIC_Gene_ID" ]
        index_status = header_ids___indices[ "Status" ]
        for line in input_dark:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequences___dark_status[ parts[ index_full_id ] ] = parts[ index_status ]
    return sequences___dark_status


# ===========================================================================
# Helpers to format list cells
# ===========================================================================

def sorted_identifier_name_lists( pairs: list ) -> tuple:
    """Sort ( identifier, name ) pairs by identifier; return parallel lists."""
    sorted_pairs = sorted( pairs, key = lambda pair: pair[ 0 ] )
    identifiers = [ pair[ 0 ] for pair in sorted_pairs ]
    names = [ pair[ 1 ] for pair in sorted_pairs ]
    return identifiers, names


def sorted_unique_strings( values ) -> list:
    return sorted( set( values ) )


def main():
    parser = argparse.ArgumentParser( description = "Phase 1 — per-species proteome annotation base tables" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    top_n_nr_hits = int( config.get( "nr_top_n", 3 ) )
    annogroup_sources = list( config.get( "annogroup_sources", [ "pfam", "go", "panther" ] ) )
    species_set_name = config[ "species_set_name" ]

    inputs = config[ "inputs" ]
    spine_dir = U.resolve_input_path( workflow_root, inputs[ "spine_dir" ] )
    gene_sizes_dir = U.resolve_input_path( workflow_root, inputs[ "gene_sizes_dir" ] )
    hotspots_dir = U.resolve_input_path( workflow_root, inputs[ "hotspots_dir" ] )
    nr_hits_dir = U.resolve_input_path( workflow_root, inputs[ "nr_hits_dir" ] )
    hmms_databases_dir = U.resolve_input_path( workflow_root, inputs[ "hmms_databases_dir" ] )
    annogroups_dir = U.resolve_input_path( workflow_root, inputs[ "annogroups_dir" ] )
    orthogroups_file = U.resolve_input_path( workflow_root, inputs[ "orthogroups_file" ] )
    secretome_dir = U.resolve_input_path( workflow_root, inputs[ "secretome_dir" ] )
    dark_dir = U.resolve_input_path( workflow_root, inputs[ "dark_dir" ] )
    gene_groups_ags_root = U.resolve_input_path( workflow_root, inputs[ "gene_groups_ags_root" ] )
    gene_families_ags_root = U.resolve_input_path( workflow_root, inputs[ "gene_families_ags_root" ] )

    # ---- fail-fast on critical inputs ------------------------------------
    spine_files = sorted( spine_dir.glob( "*-T1-proteome-sequence_table.tsv" ) )
    if not spine_files:
        print( f"CRITICAL ERROR: no spine sequence tables found in {spine_dir}", file = sys.stderr )
        print( "  Verify inputs.spine_dir points at genomesDB/output_to_input/STEP_4-create_final_species_set/<species_set>_gigantic_T1_sequence_tables.", file = sys.stderr )
        sys.exit( 1 )
    if not orthogroups_file.is_file():
        print( f"CRITICAL ERROR: orthogroups file not found: {orthogroups_file}", file = sys.stderr )
        sys.exit( 1 )

    annogroup_membership_paths = {}
    annogroup_map_paths = {}
    for source in annogroup_sources:
        source_dir = annogroups_dir / species_set_name / source
        membership_path = source_dir / f"2_ai-{source}-annogroup_membership.tsv"
        map_path = source_dir / f"2_ai-{source}-annogroup_map.tsv"
        if not membership_path.is_file():
            print( f"CRITICAL ERROR: annogroup membership not found for source '{source}': {membership_path}", file = sys.stderr )
            print( "  Remove the source from annogroup_sources, or run the annogroups subproject for it.", file = sys.stderr )
            sys.exit( 1 )
        if not map_path.is_file():
            print( f"CRITICAL ERROR: annogroup map not found for source '{source}': {map_path}", file = sys.stderr )
            sys.exit( 1 )
        annogroup_membership_paths[ source ] = membership_path
        annogroup_map_paths[ source ] = map_path

    run_when = datetime.now()
    timestamp_suffix = U.filename_timestamp_suffix( run_when )
    print( f"[001] run timestamp suffix: {timestamp_suffix}" )

    # ---- GLOBAL loads (once) ---------------------------------------------
    print( f"[001] loading orthogroups: {orthogroups_file}" )
    proteins___orthogroups, orthogroups___member_counts, orthogroups___species_counts = load_orthogroups( orthogroups_file )
    print( f"[001]   {len( proteins___orthogroups )} proteins in {len( orthogroups___member_counts )} orthogroups" )

    source___sequences___annogroups = {}
    source___annogroup_ids___names = {}
    for source in annogroup_sources:
        prefix = U.annogroup_prefix_for_source( source )
        print( f"[001] loading annogroup map ({source}): {annogroup_map_paths[ source ]}" )
        source___annogroup_ids___names[ source ] = load_annogroup_map( annogroup_map_paths[ source ], prefix )
        print( f"[001] loading annogroup membership ({source}): {annogroup_membership_paths[ source ]}" )
        source___sequences___annogroups[ source ] = load_annogroup_membership( annogroup_membership_paths[ source ] )
        print( f"[001]   {len( source___sequences___annogroups[ source ] )} sequences with {source} annogroups" )

    print( f"[001] scanning gene_groups AGS files under {gene_groups_ags_root}" )
    gene_group_ags_files = sorted( gene_groups_ags_root.glob( "*/16_ai-ags-*.aa" ) )
    sequences___gene_groups = load_ags_memberships(
        gene_group_ags_files,
        name_from_path = lambda path: path.parent.name[ len( "gene_group-" ): ] if path.parent.name.startswith( "gene_group-" ) else path.parent.name,
    )
    print( f"[001]   {len( gene_group_ags_files )} AGS files -> {len( sequences___gene_groups )} sequences with gene-group membership" )

    print( f"[001] scanning gene_families AGS files under {gene_families_ags_root}" )
    gene_family_ags_files = sorted(
        path for path in gene_families_ags_root.glob( "*/STEP_1-homolog_discovery/16_ai-ags-*.aa" )
        if path.parts[ -3 ] != "gene_family_COPYME"
    )
    sequences___gene_families = load_ags_memberships(
        gene_family_ags_files,
        name_from_path = lambda path: path.parts[ -3 ],
    )
    print( f"[001]   {len( gene_family_ags_files )} AGS files -> {len( sequences___gene_families )} sequences with gene-family membership" )

    output_shared_dir = Path( args.output_dir ) / "1-output" / "_shared"
    output_shared_dir.mkdir( parents = True, exist_ok = True )
    U.write_run_timestamp_pointer( output_shared_dir, timestamp_suffix )

    # Availability summary accumulator.
    availability_rows = []

    # ---- PER-SPECIES build ------------------------------------------------
    for spine_file in spine_files:
        phyloname = U.phyloname_from_spine_filename( spine_file.name )
        genus_species = U.genus_species_from_phyloname( phyloname )

        # Per-species source files (located by the correct per-source key).
        gene_sizes_path = gene_sizes_dir / f"3_ai-ranked_gene_metrics-{genus_species}.tsv"
        hotspots_path = hotspots_dir / f"3_ai-hotspots-{genus_species}.tsv"
        nr_path = nr_hits_dir / f"{phyloname}_top_hits.tsv"
        pfam_path = hmms_databases_dir / "database_pfam" / f"gigantic_annotations-database_pfam-{phyloname}.tsv"
        go_path = hmms_databases_dir / "database_go" / f"gigantic_annotations-database_go-{phyloname}.tsv"
        panther_path = hmms_databases_dir / "database_panther" / f"gigantic_annotations-database_panther-{phyloname}.tsv"
        secretome_path = secretome_dir / f"{phyloname}_evidence_table.tsv"
        dark_path = dark_dir / f"3_ai-dark_proteome-{genus_species}.tsv"

        gene_sizes_available = gene_sizes_path.is_file()
        hotspots_available = hotspots_path.is_file()
        hmms_available = pfam_path.is_file() and go_path.is_file() and panther_path.is_file()
        secretome_available = secretome_path.is_file()
        dark_available = dark_path.is_file()

        gene_fields___sizes = load_gene_sizes_for_species( gene_sizes_path ) if gene_sizes_available else {}
        gene_fields___hotspots = load_hotspots_for_species( hotspots_path ) if hotspots_available else {}
        sequences___nr_hits = load_nr_hits_for_species( nr_path, top_n_nr_hits ) if nr_path.is_file() else {}
        sequences___pfam = load_hmms_accession_table_for_species( pfam_path ) if pfam_path.is_file() else {}
        sequences___panther = load_hmms_accession_table_for_species( panther_path ) if panther_path.is_file() else {}
        if go_path.is_file():
            sequences___interpro_go, sequences___panther_go = load_hmms_go_table_for_species( go_path )
        else:
            sequences___interpro_go, sequences___panther_go = {}, {}
        sequences___secretome = load_secretome_for_species( secretome_path ) if secretome_available else {}
        sequences___dark_status = load_dark_for_species( dark_path ) if dark_available else {}

        output_table_path = output_shared_dir / U.build_timestamped_proteome_base_filename( phyloname, run_when )
        protein_count = 0

        with open( spine_file, 'r' ) as input_spine, open( output_table_path, 'w' ) as output_table:
            output_table.write( '\t'.join( BASE_HEADER_COLUMNS ) + '\n' )

            # Phyloname (...)\tGigantic_Protein_Identifier (...)\tSequence_Length (...)\tProtein_Sequence (...)
            header_ids___indices = U.build_header_index( input_spine.readline() )
            index_protein = header_ids___indices[ "Gigantic_Protein_Identifier" ]
            index_length = header_ids___indices[ "Sequence_Length" ]
            index_sequence = header_ids___indices[ "Protein_Sequence" ]

            for line in input_spine:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                sequence_identifier = parts[ index_protein ]
                sequence_length = parts[ index_length ]
                protein_sequence = parts[ index_sequence ] if index_sequence < len( parts ) else ""

                ( source_gene_field, _phyloname, _genus_species ) = U.parse_full_gigantic_id( sequence_identifier )

                # gene_sizes
                if not gene_sizes_available:
                    gene_size_bp = cds_size_bp = protein_size_aa = U.NA
                elif source_gene_field in gene_fields___sizes:
                    gene_size_bp, cds_size_bp, protein_size_aa = gene_fields___sizes[ source_gene_field ]
                else:
                    gene_size_bp = cds_size_bp = protein_size_aa = U.NA

                # hotspots
                if not hotspots_available:
                    in_hotspot = U.NA
                    hotspot_ids = U.NA
                    hotspot_paralog_counts = U.NA
                else:
                    hits = gene_fields___hotspots.get( source_gene_field, [] )
                    if hits:
                        in_hotspot = "yes"
                        hotspot_ids = U.DELIM.join( hotspot_id for ( hotspot_id, _paralogs ) in hits )
                        hotspot_paralog_counts = U.DELIM.join( paralogs for ( _hotspot_id, paralogs ) in hits )
                    else:
                        in_hotspot = "no"
                        hotspot_ids = U.NA
                        hotspot_paralog_counts = U.NA

                # nr hits
                top_nr_hits = sequences___nr_hits.get( sequence_identifier, U.NA )

                # annotations_hmms (four columns per type)
                pfam_pairs = sequences___pfam.get( sequence_identifier, [] )
                pfam_identifiers, pfam_names = sorted_identifier_name_lists( pfam_pairs )
                pfam_cells = U.format_per_protein_annotation_columns(
                    pfam_identifiers, pfam_names, source_available = hmms_available
                )

                interpro_pairs = sequences___interpro_go.get( sequence_identifier, [] )
                interpro_identifiers, interpro_names = sorted_identifier_name_lists( interpro_pairs )
                interpro_go_cells = U.format_per_protein_annotation_columns(
                    interpro_identifiers, interpro_names, source_available = hmms_available
                )

                panther_go_pairs = sequences___panther_go.get( sequence_identifier, [] )
                panther_go_identifiers, panther_go_names = sorted_identifier_name_lists( panther_go_pairs )
                panther_go_cells = U.format_per_protein_annotation_columns(
                    panther_go_identifiers, panther_go_names, source_available = hmms_available
                )

                panther_pairs = sequences___panther.get( sequence_identifier, [] )
                panther_identifiers, panther_names = sorted_identifier_name_lists( panther_pairs )
                panther_cells = U.format_per_protein_annotation_columns(
                    panther_identifiers, panther_names, source_available = hmms_available
                )

                # annogroups (membership union per source; four columns each)
                annogroup_pfam_ids = sorted_unique_strings(
                    source___sequences___annogroups.get( "pfam", {} ).get( sequence_identifier, [] )
                )
                annogroup_pfam_names = [
                    source___annogroup_ids___names[ "pfam" ][ annogroup_id ]
                    for annogroup_id in annogroup_pfam_ids
                ]
                annogroup_pfam_cells = U.format_per_protein_annotation_columns(
                    annogroup_pfam_ids, annogroup_pfam_names
                )

                annogroup_go_ids = sorted_unique_strings(
                    source___sequences___annogroups.get( "go", {} ).get( sequence_identifier, [] )
                )
                annogroup_go_names = [
                    source___annogroup_ids___names[ "go" ][ annogroup_id ]
                    for annogroup_id in annogroup_go_ids
                ]
                annogroup_go_cells = U.format_per_protein_annotation_columns(
                    annogroup_go_ids, annogroup_go_names
                )

                annogroup_panther_ids = sorted_unique_strings(
                    source___sequences___annogroups.get( "panther", {} ).get( sequence_identifier, [] )
                )
                annogroup_panther_names = [
                    source___annogroup_ids___names[ "panther" ][ annogroup_id ]
                    for annogroup_id in annogroup_panther_ids
                ]
                annogroup_panther_cells = U.format_per_protein_annotation_columns(
                    annogroup_panther_ids, annogroup_panther_names
                )

                # orthogroups
                orthogroup_id = proteins___orthogroups.get( sequence_identifier )
                if orthogroup_id is None:
                    orthogroup_id_cell = U.NA
                    orthogroup_member_count = U.NA
                    orthogroup_species_count = U.NA
                else:
                    orthogroup_id_cell = orthogroup_id
                    orthogroup_member_count = str( orthogroups___member_counts.get( orthogroup_id, 0 ) )
                    orthogroup_species_count = str( orthogroups___species_counts.get( orthogroup_id, 0 ) )

                # secretome
                if not secretome_available:
                    secretome_call = secretome_probability = secretome_localization = U.NA
                else:
                    ( secretome_call, secretome_probability, secretome_localization ) = sequences___secretome.get(
                        sequence_identifier, ( U.NA, U.NA, U.NA )
                    )

                # AGS memberships (identifiers only; names intentionally blank)
                gene_group_ids = sorted_unique_strings( sequences___gene_groups.get( sequence_identifier, set() ) )
                gene_group_cells = U.format_per_protein_annotation_columns(
                    gene_group_ids, names_blank = True
                )
                gene_family_ids = sorted_unique_strings( sequences___gene_families.get( sequence_identifier, set() ) )
                gene_family_cells = U.format_per_protein_annotation_columns(
                    gene_family_ids, names_blank = True
                )

                # dark
                dark_status = sequences___dark_status.get( sequence_identifier, U.NA ) if dark_available else U.NA

                row_fields = [
                    sequence_identifier,
                    phyloname,
                    genus_species,
                    sequence_length,
                    protein_sequence,
                    gene_size_bp,
                    cds_size_bp,
                    protein_size_aa,
                    "yes" if gene_sizes_available else "no",
                    in_hotspot,
                    hotspot_ids,
                    hotspot_paralog_counts,
                    "yes" if hotspots_available else "no",
                    top_nr_hits,
                    *pfam_cells,
                    *interpro_go_cells,
                    *panther_go_cells,
                    *panther_cells,
                    "yes" if hmms_available else "no",
                    *annogroup_pfam_cells,
                    *annogroup_go_cells,
                    *annogroup_panther_cells,
                    orthogroup_id_cell,
                    orthogroup_member_count,
                    orthogroup_species_count,
                    secretome_call,
                    secretome_probability,
                    secretome_localization,
                    "yes" if secretome_available else "no",
                    *gene_group_cells,
                    *gene_family_cells,
                    dark_status,
                    "yes" if dark_available else "no",
                ]
                output_table.write( '\t'.join( row_fields ) + '\n' )
                protein_count += 1

        availability_rows.append( (
            phyloname, genus_species, str( protein_count ),
            "yes" if gene_sizes_available else "no",
            "yes" if hotspots_available else "no",
            "yes" if nr_path.is_file() else "no",
            "yes" if hmms_available else "no",
            "yes" if secretome_available else "no",
            "yes" if dark_available else "no",
        ) )
        print( f"[001] {phyloname}: {protein_count} proteins -> {output_table_path.name}" )

    # ---- availability summary --------------------------------------------
    summary_header = [
        "Phyloname (GIGANTIC phyloname for the species)",
        "Genus_Species (Genus_species of the species)",
        "Protein_Count (number of proteins in the species proteome spine)",
        "Gene_Sizes_Available (yes if gene_sizes per species table present)",
        "Hotspots_Available (yes if hotspots per species table present)",
        "NR_Hits_Available (yes if one_direction_homologs nr top hits present)",
        "Annotations_HMMs_Available (yes if pfam+go+panther per species tables present)",
        "Secretome_Available (yes if secretome evidence table present)",
        "Dark_Proteome_Available (yes if dark proteome table present)",
    ]
    summary_path = output_shared_dir / U.build_timestamped_availability_summary_filename( run_when )
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( '\t'.join( summary_header ) + '\n' )
        for row in availability_rows:
            output_summary.write( '\t'.join( row ) + '\n' )

    print( f"[001] wrote {len( availability_rows )} per-species base tables + availability summary -> {output_shared_dir}" )

    if not availability_rows:
        print( "CRITICAL ERROR: no species processed — spine produced zero base tables", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
