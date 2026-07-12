# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Build cross-producer sequence annotation index aligned with integrator catalog annotation types
# Human: Eric Edsinger

"""
Script 006 — Build the cross-producer sequence -> annotation index.

Runs ONCE per workflow. Annotation types and delimiters match the integrator catalog
BLOCKs (orthogroups_X_all_annotations / leonid / species): Pfam, GO, PANTHER,
Annogroups_Pfam/GO/PANTHER, Gene_Families, Gene_Groups (HGNC gg<N>), Dark_Proteome,
Hotspots.

Per-sequence index columns: <Type>_Identifiers + <Type>_Names (two columns per type).
Script 004 aggregates to four columns per type on composite-clades detail tables
(Species_Count, Sequence_Count, Identifiers, Names).

Fail-fast: exits 1 on missing configured sources or empty index.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U

INTERPROSCAN_ID_TRUNCATION_LENGTH = 255
GO_TERMS_COLUMN_INDEX = 13
GO_PROTEIN_COLUMN_INDEX = 0

ANNOTATION_TYPES = U.ANNOTATION_TYPE_SPECS


def load_go_names( go_name_path: Path ) -> dict:
    identifiers___names = {}
    with open( go_name_path, 'r' ) as input_go:
        header_ids___indices = U.build_header_index( input_go.readline() )
        index_id = header_ids___indices[ "GO_ID" ]
        index_name = header_ids___indices[ "GO_Name" ]
        for line in input_go:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            identifiers___names[ parts[ index_id ] ] = parts[ index_name ]
    if not identifiers___names:
        print( f"CRITICAL ERROR: no GO id->name pairs in {go_name_path}", file = sys.stderr )
        sys.exit( 1 )
    return identifiers___names


def load_parsed_hmm( source_dir: Path, source: str, sequences___ids_names: dict ):
    subdirectory = source_dir / source
    files = sorted( subdirectory.glob( f"{source}-*.tsv" ) ) if subdirectory.is_dir() else []
    if not files:
        print( f"CRITICAL ERROR: no {source} files in {subdirectory}", file = sys.stderr )
        sys.exit( 1 )
    rows = 0
    for source_file in files:
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            index_accession = header_ids___indices[ "Accession" ]
            index_description = header_ids___indices[ "Description" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                sequence_id = parts[ index_protein ]
                if len( sequence_id ) == INTERPROSCAN_ID_TRUNCATION_LENGTH:
                    continue
                accession = parts[ index_accession ]
                name = parts[ index_description ] if index_description < len( parts ) else ''
                U.guard_name( source, accession, name )
                sequences___ids_names[ sequence_id ][ accession ] = name
                rows += 1
    return rows


def load_go_raw( raw_dir: Path, go_id_to_name: dict, sequences___ids_names: dict ):
    files = sorted( raw_dir.glob( "*_interproscan_results.tsv" ) )
    if not files:
        print( f"CRITICAL ERROR: no *_interproscan_results.tsv in {raw_dir}", file = sys.stderr )
        sys.exit( 1 )
    rows = 0
    for source_file in files:
        with open( source_file, 'r' ) as input_source:
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                if len( parts ) <= GO_TERMS_COLUMN_INDEX:
                    continue
                sequence_id = parts[ GO_PROTEIN_COLUMN_INDEX ]
                if len( sequence_id ) == INTERPROSCAN_ID_TRUNCATION_LENGTH:
                    continue
                go_terms = parts[ GO_TERMS_COLUMN_INDEX ]
                if not go_terms:
                    continue
                for token in go_terms.split( '|' ):
                    token = token.strip()
                    if not token.startswith( 'GO:' ):
                        continue
                    go_id = token.split( '(' )[ 0 ].strip()
                    name = go_id_to_name.get( go_id, "unknown GO term" )
                    U.guard_name( "GO", go_id, name )
                    sequences___ids_names[ sequence_id ][ go_id ] = name
                    rows += 1
    return rows


def load_annogroup_map( map_path: Path, source_label: str ) -> dict:
    annogroup_ids___names = {}
    with open( map_path, 'r' ) as input_map:
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
            name = U.annogroup_name_from_map_fields( parts[ index_type ], parts[ index_definitions ] if index_definitions < len( parts ) else '' )
            U.guard_name( source_label, annogroup_id, name )
            annogroup_ids___names[ annogroup_id ] = name
    return annogroup_ids___names


def load_annogroup_membership( membership_path: Path, annogroup_ids___names: dict, sequences___ids_names: dict, source_label: str ):
    rows = 0
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            if annogroup_id not in annogroup_ids___names:
                print( f"CRITICAL ERROR: {source_label} membership annogroup {annogroup_id} missing from map", file = sys.stderr )
                sys.exit( 1 )
            name = annogroup_ids___names[ annogroup_id ]
            sequence_id = parts[ index_sequence ]
            sequences___ids_names[ sequence_id ][ annogroup_id ] = name
            rows += 1
    return rows


def load_gene_families( gene_families_dir: Path, sequences___ids_names: dict ):
    rows = 0
    for ags_file in sorted( gene_families_dir.glob( "**/16_ai-ags-*.aa" ) ):
        family_token = ags_file.stem.replace( "16_ai-ags-", "" )
        family_slug = family_token if family_token else ags_file.parent.name
        with open( ags_file, 'r' ) as input_ags:
            for line in input_ags:
                if not line.startswith( '>' ):
                    continue
                sequence_id = line[ 1: ].strip().split()[ 0 ]
                sequences___ids_names[ sequence_id ][ family_slug ] = family_slug
                rows += 1
    return rows


def load_gene_groups_hgnc( gene_groups_dir: Path, metadata_path: Path, sequences___ids_names: dict ):
    sanitized___id_name = U.load_gene_group_metadata( metadata_path )
    rows = 0
    for instance_dir in sorted( gene_groups_dir.glob( "gene_groups-*" ) ):
        for ags_file in sorted( instance_dir.rglob( "16_ai-ags-*.aa" ) ):
            sanitized = U.sanitized_name_from_ags_path( ags_file )
            if sanitized is None:
                continue
            gene_group_id, gene_group_name = U.resolve_gene_group_id_name( sanitized, sanitized___id_name )
            U.guard_name( "Gene_Groups", gene_group_id, gene_group_name )
            with open( ags_file, 'r' ) as input_ags:
                for line in input_ags:
                    if not line.startswith( '>' ):
                        continue
                    sequence_id = line[ 1: ].strip().split()[ 0 ]
                    sequences___ids_names[ sequence_id ][ gene_group_id ] = gene_group_name
                    rows += 1
    return rows


def load_dark_proteome( dark_dir: Path, sequences___ids_names: dict ):
    files = sorted( p for p in dark_dir.glob( "3_ai-dark_proteome-*.tsv" ) if "dark_proteome_summary" not in p.name )
    if not files:
        print( f"CRITICAL ERROR: no per-species dark proteome files in {dark_dir}", file = sys.stderr )
        sys.exit( 1 )
    rows = 0
    for source_file in files:
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_full_id = header_ids___indices[ "Full_GIGANTIC_Gene_ID" ]
            index_status = header_ids___indices[ "Status" ]
            index_sources = header_ids___indices[ "Annotation_Sources_CSV" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                sequence_id = parts[ index_full_id ]
                status = parts[ index_status ]
                sources = parts[ index_sources ] if index_sources < len( parts ) else ''
                name = sources.replace( ',', ' ' ).strip() if sources.strip() else "none"
                U.guard_name( "Dark_Proteome", status, name )
                sequences___ids_names[ sequence_id ][ status ] = name
                rows += 1
    return rows


def load_hotspots( hotspots_dir: Path, sequences___ids_names: dict ):
    files = sorted( p for p in hotspots_dir.glob( "3_ai-hotspots-*.tsv" ) if "hotspot_summary" not in p.name )
    if not files:
        print( f"CRITICAL ERROR: no per-species hotspot files in {hotspots_dir}", file = sys.stderr )
        sys.exit( 1 )
    species_gene___hotspots = defaultdict( set )
    for source_file in files:
        genus_species = source_file.name[ len( "3_ai-hotspots-" ): -len( ".tsv" ) ]
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_hotspot = header_ids___indices[ "Hotspot_ID" ]
            index_members = header_ids___indices[ "Member_Source_Gene_IDs" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                hotspot_id = parts[ index_hotspot ]
                members_cell = parts[ index_members ] if index_members < len( parts ) else ''
                for gene_field in members_cell.split( ',' ):
                    gene_field = gene_field.strip()
                    if gene_field:
                        species_gene___hotspots[ ( genus_species, gene_field ) ].add( hotspot_id )
    rows = 0
    for ( genus_species, gene_field ), hotspot_ids in species_gene___hotspots.items():
        for hotspot_id in hotspot_ids:
            rows += 1
    return species_gene___hotspots, rows


def format_ids_names( ids_names: dict, names_blank: bool ):
    identifiers = sorted( ids_names.keys() )
    if not identifiers:
        return ( '', '' )
    names = [ '' ] * len( identifiers ) if names_blank else [ ids_names[ identifier ] for identifier in identifiers ]
    return ( U.DELIM.join( identifiers ), '' if names_blank else U.NAME_DELIM.join( names ) )


def main():
    parser = argparse.ArgumentParser( description = "Build the cross-producer sequence annotation index" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    parser.add_argument( '--workflow_root', default = None )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = Path( args.workflow_root ).resolve() if args.workflow_root else U.workflow_root_from_output_dir( args.output_dir )
    sources = config.get( "annotation_index" )
    if not sources:
        print( "CRITICAL ERROR: config is missing the 'annotation_index' block", file = sys.stderr )
        sys.exit( 1 )

    required_keys = [
        "interproscan_parsed_dir", "interproscan_raw_dir", "go_id_to_name",
        "pfam_membership", "pfam_map", "go_membership", "go_map",
        "panther_membership", "panther_map",
        "gene_families_dir", "gene_groups_dir", "gene_groups_hgnc_metadata",
        "dark_proteome_dir", "hotspots_dir",
    ]
    resolved = {}
    for key in required_keys:
        if key not in sources or not str( sources[ key ] ).strip():
            print( f"CRITICAL ERROR: annotation_index.{key} is not set", file = sys.stderr )
            sys.exit( 1 )
        path = U.resolve_input_path( workflow_root, str( sources[ key ] ).strip() )
        if not path.exists():
            print( f"CRITICAL ERROR: annotation_index.{key} not found: {path}", file = sys.stderr )
            sys.exit( 1 )
        resolved[ key ] = path

    types___sequences = { prefix: defaultdict( dict ) for ( prefix, label, names_blank ) in ANNOTATION_TYPES }

    rows = load_parsed_hmm( resolved[ "interproscan_parsed_dir" ], "pfam", types___sequences[ "Pfam" ] )
    print( f"[006] Pfam: {rows} rows -> {len( types___sequences[ 'Pfam' ] )} sequences" )

    go_names = load_go_names( resolved[ "go_id_to_name" ] )
    rows = load_go_raw( resolved[ "interproscan_raw_dir" ], go_names, types___sequences[ "GO" ] )
    print( f"[006] GO: {rows} rows -> {len( types___sequences[ 'GO' ] )} sequences" )

    rows = load_parsed_hmm( resolved[ "interproscan_parsed_dir" ], "panther", types___sequences[ "PANTHER" ] )
    print( f"[006] PANTHER: {rows} rows -> {len( types___sequences[ 'PANTHER' ] )} sequences" )

    for prefix, membership_key, map_key, label in [
        ( "Annogroups_Pfam", "pfam_membership", "pfam_map", "Annogroups_Pfam" ),
        ( "Annogroups_GO", "go_membership", "go_map", "Annogroups_GO" ),
        ( "Annogroups_PANTHER", "panther_membership", "panther_map", "Annogroups_PANTHER" ),
    ]:
        annogroup_map = load_annogroup_map( resolved[ map_key ], label )
        rows = load_annogroup_membership( resolved[ membership_key ], annogroup_map, types___sequences[ prefix ], label )
        print( f"[006] {prefix}: {rows} rows -> {len( types___sequences[ prefix ] )} sequences" )

    rows = load_gene_families( resolved[ "gene_families_dir" ], types___sequences[ "Gene_Families" ] )
    print( f"[006] Gene_Families: {rows} rows -> {len( types___sequences[ 'Gene_Families' ] )} sequences" )

    rows = load_gene_groups_hgnc( resolved[ "gene_groups_dir" ], resolved[ "gene_groups_hgnc_metadata" ], types___sequences[ "Gene_Groups" ] )
    print( f"[006] Gene_Groups: {rows} rows -> {len( types___sequences[ 'Gene_Groups' ] )} sequences" )

    rows = load_dark_proteome( resolved[ "dark_proteome_dir" ], types___sequences[ "Dark_Proteome" ] )
    print( f"[006] Dark_Proteome: {rows} rows -> {len( types___sequences[ 'Dark_Proteome' ] )} sequences" )

    species_gene___hotspots, hotspot_rows = load_hotspots( resolved[ "hotspots_dir" ], types___sequences[ "Hotspots" ] )
    hotspot_sequences = 0
    for source_file in sorted( resolved[ "interproscan_parsed_dir" ].glob( "pfam/pfam-*.tsv" ) ):
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                sequence_id = parts[ index_protein ]
                if len( sequence_id ) == INTERPROSCAN_ID_TRUNCATION_LENGTH:
                    continue
                parsed = U.parse_full_gigantic_id( sequence_id )
                if parsed[ 0 ] is None:
                    continue
                source_gene_field, phyloname, genus_species = parsed
                hotspot_ids = species_gene___hotspots.get( ( genus_species, source_gene_field ) )
                if not hotspot_ids:
                    continue
                for hotspot_id in hotspot_ids:
                    types___sequences[ "Hotspots" ][ sequence_id ][ hotspot_id ] = ''
                hotspot_sequences += 1
    print( f"[006] Hotspots: {hotspot_rows} region-gene links -> {len( types___sequences[ 'Hotspots' ] )} sequences ({hotspot_sequences} pfam-indexed joins)" )

    all_sequences = set()
    for prefix, label, names_blank in ANNOTATION_TYPES:
        all_sequences.update( types___sequences[ prefix ].keys() )
    if not all_sequences:
        print( "CRITICAL ERROR: annotation index is empty", file = sys.stderr )
        sys.exit( 1 )

    output_dir = Path( args.output_dir ) / "annotation_index"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_path = U.timestamped_output_path(
        output_dir,
        "6_ai-sequence_annotation_index",
        Path( args.output_dir ),
    )

    header = [ "Sequence_Identifier (full GIGANTIC member sequence identifier)" ]
    for prefix, label, names_blank in ANNOTATION_TYPES:
        header.append( f"{prefix}_Identifiers (comma delimited distinct {label} identifiers on this sequence)" )
        if names_blank:
            header.append( f"{prefix}_Names (intentionally blank; hotspot has no separate human-readable name)" )
        else:
            header.append( f"{prefix}_Names (' // ' delimited {label} names aligned to {prefix}_Identifiers)" )

    rows_written = 0
    with open( output_path, 'w' ) as output_file:
        output_file.write( '\t'.join( header ) + '\n' )
        for sequence_id in sorted( all_sequences ):
            cells = [ sequence_id ]
            for prefix, label, names_blank in ANNOTATION_TYPES:
                identifiers_cell, names_cell = format_ids_names( types___sequences[ prefix ].get( sequence_id, {} ), names_blank )
                cells.extend( [ identifiers_cell, names_cell ] )
            output_file.write( '\t'.join( cells ) + '\n' )
            rows_written += 1

    print( f"[006] wrote annotation index: {rows_written} sequences x {len( ANNOTATION_TYPES )} types -> {output_path}" )


if __name__ == '__main__':
    main()
