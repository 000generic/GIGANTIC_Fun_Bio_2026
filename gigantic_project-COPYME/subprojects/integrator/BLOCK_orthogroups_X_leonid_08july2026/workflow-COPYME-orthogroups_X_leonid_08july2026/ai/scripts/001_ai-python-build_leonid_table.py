#!/usr/bin/env python3
# AI: Claude (Cursor) | Opus 4.8 | 2026 July 08 | Purpose: Build the per-orthogroup Leonid table (IDs, sequences, Pfam/GO/PANTHER annotations, species-tree deconvolution)
# Human: Eric Edsinger

"""
Script 001 — Build the orthogroups_X_leonid table (one row per OrthoHMM orthogroup).

Each row is ONE OrthoHMM orthogroup. Columns, in order:

  Orthogroup_ID
  Sequence_IDs                     comma-delimited full GIGANTIC member IDs
  Member_Sequence_Count            integer
  Is_Singleton                     yes | no
  Pfam_Identifiers                 comma-delimited non-redundant Pfam accessions
  Pfam_Names                       ' // '-delimited names (aligned to identifiers)
  GO_Identifiers                   comma-delimited non-redundant GO IDs
  GO_Names                         ' // '-delimited names (aligned to identifiers)
  PANTHER_Identifiers              comma-delimited non-redundant PANTHER accessions
  PANTHER_Names                    ' // '-delimited names (aligned to identifiers)
  Annogroups_Pfam (2 cols)         Annogroup_IDs + names
  Annogroups_GO (2 cols)           same pattern (ALL annogroup types)
  Annogroups_PANTHER (2 cols)      same pattern (ALL annogroup types)
  Gene_Families (2 cols)           family slug identifiers + names
  Gene_Groups (2 cols)             gene group identifiers + names
  <clade / species columns...>     species-tree deconvolution (see below)

Species-tree deconvolution
--------------------------
Adds one column per NON-REDUNDANT clade (internal node or species tip) taken as the
UNION of clades across the user-selected species-tree structures (default 001, 003,
031, 032). Each cell = the count of the orthogroup's member sequences within that
clade:
  - tip (a species)  -> member sequences from that one species
  - internal node    -> sum over its descendant species
A clade that covers every species (a tree root) therefore equals the orthogroup's
Member_Sequence_Count. GIGANTIC Rule 6 guarantees a clade_id_name identifies a fixed
topologically-structured species set, so its count is identical in every structure it
appears in; the union is non-redundant and each column's header records which of the
selected structures the clade appears in. Column order: largest clade (root) -> tips.

Annotation source
-----------------
Pfam / GO / PANTHER accessions come from the validated `annogroups` subproject
FEATURE-type membership (one feature annogroup per distinct accession a sequence
carries), keyed on the full GIGANTIC sequence identifier.

Annogroups_Pfam / Annogroups_GO / Annogroups_PANTHER add curated annogroup
membership (ALL types: feature, combination, architecture, absent) with
Annogroup_ID as the identifier and Annotation_Definitions as the name.

Fail-fast (§36): exits 1 if any input is missing; if a Rule-6 violation is seen (a
clade_id_name with different species across the selected structures); if a member's
species is not a tree tip (would be silently uncounted); if a full-coverage clade's
count != Member_Sequence_Count; if an annotated (membership) sequence is absent from
the orthogroups (a silently dropped annotation); if an annotation name contains the
NAME delimiter ' // '.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_orthogroups_X_leonid as U


def guard_name( label: str, identifier: str, name: str ):
    if U.NAME_DELIM in name:
        print( f"CRITICAL ERROR: {label} name for identifier {identifier} contains the NAME-column "
               f"delimiter {U.NAME_DELIM!r} and would corrupt the *_Names list: {name!r}", file = sys.stderr )
        sys.exit( 1 )


def new_feature( prefix: str, label: str ) -> dict:
    return {
        "prefix": prefix,
        "label": label,
        "orthogroups___identifiers": defaultdict( set ),
        "identifiers___names": {},
        "skipped_non_orthogroup": 0,
    }


def add_feature_annotation( feature: dict, og_id: str, identifier: str, name: str ):
    feature[ "orthogroups___identifiers" ][ og_id ].add( identifier )
    feature[ "identifiers___names" ][ identifier ] = name


def new_annogroup_feature( prefix: str, label: str ) -> dict:
    return {
        "prefix": prefix,
        "label": label,
        "orthogroups___identifiers": defaultdict( set ),
        "orthogroups___sequences": defaultdict( set ),
        "orthogroups___species": defaultdict( set ),
        "identifiers___names": {},
    }


def add_annogroup_annotation( feature: dict, og_id: str, sequence_id: str, genus_species: str,
                              identifier: str, name: str ):
    feature[ "orthogroups___identifiers" ][ og_id ].add( identifier )
    feature[ "orthogroups___sequences" ][ og_id ].add( sequence_id )
    feature[ "orthogroups___species" ][ og_id ].add( genus_species )
    feature[ "identifiers___names" ][ identifier ] = name


# ---------------------------------------------------------------------------
# Clade data (species-tree deconvolution), restricted to the selected structures
# ---------------------------------------------------------------------------
def load_clade_data( clade_map_path: Path, selected_structures: list ):
    """
    Load clades from the trees_species clade->species map, keeping only the
    user-selected structures. Builds the non-redundant clade union with, per
    clade: its species set, descendant count, and which selected structures it
    appears in. Validates Rule-6 consistency (same clade_id_name => same species
    set across every selected structure).

    Returns:
        clades___species          { clade_id_name: frozenset( Genus_species ) }
        clades___descendant_count { clade_id_name: int }   (0 for tips)
        clades___structures       { clade_id_name: sorted list of structure ids present }
        tip_species               set of Genus_species (the leaves)
        species___ancestor_clades { Genus_species: [ clade_id_name, ... ] }
        union_ordered_clades      clades ordered root -> tips
        full_coverage_clades      clades whose species set == all tips
    """
    selected = set( selected_structures )
    clades___species = {}
    clades___descendant_count = {}
    clades___structures_set = defaultdict( set )
    tip_species = set()
    seen_structures = set()

    # header:
    # Structure_ID	Clade_ID_Name	Phylogenetic_Block	Descendant_Species_Count	Descendant_Species_List	...
    # structure_001	C082_Metazoa	...::...	70	Acropora_muricata,Adineta_vaga,...	...
    with open( clade_map_path, 'r' ) as input_clade_map:
        header_ids___indices = U.build_header_index( input_clade_map.readline() )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_descendant_count = header_ids___indices[ "Descendant_Species_Count" ]
        index_descendant_list = header_ids___indices[ "Descendant_Species_List" ]

        for line in input_clade_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ index_structure ]
            if structure_id not in selected:
                continue
            seen_structures.add( structure_id )

            clade_id_name = parts[ index_clade ]
            descendant_count = int( parts[ index_descendant_count ] ) if parts[ index_descendant_count ] else 0
            descendant_list = parts[ index_descendant_list ] if index_descendant_list < len( parts ) else ''

            if descendant_count > 0:
                species = frozenset( name.strip() for name in descendant_list.split( ',' ) if name.strip() )
            else:
                # tip: clade_id_name is like C###_Genus_species -> species after first '_'
                species_name = clade_id_name.split( '_', 1 )[ 1 ] if '_' in clade_id_name else clade_id_name
                species = frozenset( [ species_name ] )
                tip_species.add( species_name )

            clades___structures_set[ clade_id_name ].add( structure_id )

            if clade_id_name in clades___species:
                if clades___species[ clade_id_name ] != species:
                    print( f"CRITICAL ERROR: clade {clade_id_name} has DIFFERENT species sets across the "
                           f"selected structures (Rule 6 violation) -- counts would be ill-defined", file = sys.stderr )
                    sys.exit( 1 )
            else:
                clades___species[ clade_id_name ] = species
                clades___descendant_count[ clade_id_name ] = descendant_count

    missing_structures = selected - seen_structures
    if missing_structures:
        print( f"CRITICAL ERROR: selected structure(s) not found in {clade_map_path}: "
               f"{sorted( missing_structures )}", file = sys.stderr )
        sys.exit( 1 )
    if not clades___species:
        print( f"CRITICAL ERROR: no clades found for selected structures in {clade_map_path}", file = sys.stderr )
        sys.exit( 1 )

    clades___structures = { clade: sorted( structures ) for clade, structures in clades___structures_set.items() }

    union_ordered_clades = sorted(
        clades___species.keys(),
        key = lambda clade: ( -clades___descendant_count[ clade ], clade )
    )
    full_coverage_clades = [ clade for clade in union_ordered_clades
                             if clades___species[ clade ] == frozenset( tip_species ) ]

    species___ancestor_clades = defaultdict( list )
    for clade_id_name, species in clades___species.items():
        for species_name in species:
            species___ancestor_clades[ species_name ].append( clade_id_name )

    return ( clades___species, clades___descendant_count, clades___structures, tip_species,
             species___ancestor_clades, union_ordered_clades, full_coverage_clades )


# ---------------------------------------------------------------------------
# Orthogroups spine
# ---------------------------------------------------------------------------
def load_orthogroups( orthogroups_path: Path ):
    """
    Load the headerless OrthoHMM table:
        OG_ID <tab> member_1 <tab> member_2 <tab> ...
    Returns:
        orthogroups              [ ( og_id, [ member, ... ] ) ]  (file order)
        sequences___orthogroups  { member: og_id }  (keys reuse the member str objects)
    """
    orthogroups = []
    sequences___orthogroups = {}
    with open( orthogroups_path, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            og_id = parts[ 0 ]
            members = parts[ 1: ]
            orthogroups.append( ( og_id, members ) )
            for member in members:
                sequences___orthogroups[ member ] = og_id
    if not orthogroups:
        print( f"CRITICAL ERROR: no orthogroups parsed from {orthogroups_path}", file = sys.stderr )
        sys.exit( 1 )
    return orthogroups, sequences___orthogroups


# ---------------------------------------------------------------------------
# Annotations from annogroups FEATURE membership + map
# ---------------------------------------------------------------------------
def load_feature_accession_names( map_path: Path, source: str ):
    """
    From the annogroup MAP, build { accession: name } for FEATURE-type rows.
    Fails fast if a name contains the NAME delimiter (would corrupt the *_Names column).
    """
    accessions___names = {}
    # header:
    # Annogroup_ID	Source	Annogroup_Type	Defining_Features	Annotation_Definitions	...
    # annogroup_pfam_PF00001	pfam	feature	PF00001	7 transmembrane receptor (rhodopsin family) ==PF00001	...
    with open( map_path, 'r' ) as input_map:
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_defining = header_ids___indices[ "Defining_Features" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_type ] != 'feature':
                continue
            accession = parts[ index_defining ]
            definition = parts[ index_definitions ] if index_definitions < len( parts ) else ''
            # Annotation_Definitions is "name ==accession" for feature rows; keep the name.
            name = definition.split( ' ==' )[ 0 ].strip()
            if U.NAME_DELIM in name:
                print( f"CRITICAL ERROR: {source} name for accession {accession} contains the NAME-column "
                       f"delimiter {U.NAME_DELIM!r} and would corrupt the *_Names list: {name!r}", file = sys.stderr )
                sys.exit( 1 )
            accessions___names[ accession ] = name
    if not accessions___names:
        print( f"CRITICAL ERROR: no feature-type accessions parsed from {map_path}", file = sys.stderr )
        sys.exit( 1 )
    return accessions___names


def aggregate_source_accessions( membership_path: Path, source: str,
                                 accessions___names: dict, sequences___orthogroups: dict,
                                 missing_report_path: Path ):
    """
    Stream the annogroup FEATURE-type membership and aggregate, per orthogroup, the
    non-redundant set of accessions its member sequences carry for this source.

    Returns { og_id: set( accession ) }.

    Fail-fast: any membership (annotated) sequence absent from the orthogroups means a
    silently dropped annotation (species-set / ID mismatch) -> write the offenders and
    exit 1. Any membership accession lacking a name in the map -> exit 1.
    """
    orthogroups___accessions = defaultdict( set )
    missing_sequences = []
    # header:
    # Sequence_Identifier	Genus_Species	Annogroup_ID	Annogroup_Type	Member_Architecture_Coordinates ...
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        prefix = f"annogroup_{source}_"
        prefix_length = len( prefix )
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_type ] != 'feature':
                continue
            sequence_id = parts[ index_sequence ]
            og_id = sequences___orthogroups.get( sequence_id )
            if og_id is None:
                if len( missing_sequences ) < 100:
                    missing_sequences.append( sequence_id )
                else:
                    missing_sequences.append( None )  # sentinel: count beyond 100
                continue
            annogroup_id = parts[ index_annogroup ]
            accession = annogroup_id[ prefix_length: ] if annogroup_id.startswith( prefix ) else annogroup_id
            if accession not in accessions___names:
                print( f"CRITICAL ERROR: {source} membership accession {accession} (from {annogroup_id}) has no "
                       f"name in the annogroup map -- map/membership mismatch", file = sys.stderr )
                sys.exit( 1 )
            orthogroups___accessions[ og_id ].add( accession )

    if missing_sequences:
        real_missing = [ s for s in missing_sequences if s is not None ]
        overflow = missing_sequences.count( None )
        missing_report_path.parent.mkdir( parents = True, exist_ok = True )
        with open( missing_report_path, 'w' ) as output_missing:
            output_missing.write( "Sequence_Identifier (annotated membership sequence absent from the orthogroups table)\n" )
            for sequence_id in real_missing:
                output_missing.write( sequence_id + '\n' )
        print( f"CRITICAL ERROR: {source} has {len( real_missing ) + overflow} annotated sequence(s) absent from the "
               f"orthogroups table -- their annotations would be silently dropped. First offenders written to "
               f"{missing_report_path}", file = sys.stderr )
        sys.exit( 1 )

    return orthogroups___accessions


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
            name = U.annogroup_name_from_map_fields(
                parts[ index_type ],
                parts[ index_definitions ] if index_definitions < len( parts ) else '',
            )
            guard_name( source_label, annogroup_id, name )
            annogroup_ids___names[ annogroup_id ] = name
    if not annogroup_ids___names:
        print( f"CRITICAL ERROR: no annogroups parsed from {map_path}", file = sys.stderr )
        sys.exit( 1 )
    return annogroup_ids___names


def aggregate_source_annogroups( membership_path: Path, source_label: str,
                                 annogroup_ids___names: dict, sequences___orthogroups: dict,
                                 missing_report_path: Path ) -> dict:
    feature = new_annogroup_feature( source_label, source_label )
    missing_sequences = []
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_id = parts[ index_sequence ]
            annogroup_id = parts[ index_annogroup ]
            og_id = sequences___orthogroups.get( sequence_id )
            if og_id is None:
                if len( missing_sequences ) < 100:
                    missing_sequences.append( sequence_id )
                else:
                    missing_sequences.append( None )
                continue
            if annogroup_id not in annogroup_ids___names:
                print( f"CRITICAL ERROR: {source_label} membership annogroup {annogroup_id} has no "
                       f"name in the annogroup map -- map/membership mismatch", file = sys.stderr )
                sys.exit( 1 )
            genus_species = U.genus_species_from_full_gigantic_id( sequence_id )
            add_annogroup_annotation(
                feature, og_id, sequence_id, genus_species, annogroup_id,
                annogroup_ids___names[ annogroup_id ],
            )

    if missing_sequences:
        real_missing = [ sequence_id for sequence_id in missing_sequences if sequence_id is not None ]
        overflow = missing_sequences.count( None )
        missing_report_path.parent.mkdir( parents = True, exist_ok = True )
        with open( missing_report_path, 'w' ) as output_missing:
            output_missing.write( "Sequence_Identifier (annogroup membership sequence absent from the orthogroups table)\n" )
            for sequence_id in real_missing:
                output_missing.write( sequence_id + '\n' )
        print( f"CRITICAL ERROR: {source_label} has {len( real_missing ) + overflow} annogroup membership "
               f"sequence(s) absent from the orthogroups table -- their annotations would be silently dropped. "
               f"First offenders written to {missing_report_path}", file = sys.stderr )
        sys.exit( 1 )
    return feature


def annogroup_feature_headers( feature: dict ) -> list:
    prefix = feature[ "prefix" ]
    label = feature[ "label" ]
    return [
        f"{prefix}_Identifiers (comma delimited non-redundant {label} identifiers across all member sequences)",
        f"{prefix}_Names (' // ' delimited {label} names aligned to {prefix}_Identifiers; "
        f"' // ' used because names may contain commas, semicolons, or pipes)",
    ]


def annogroup_feature_cells( feature: dict, og_id: str ) -> list:
    identifiers = sorted( feature[ "orthogroups___identifiers" ].get( og_id, () ) )
    names = U.NAME_DELIM.join( feature[ "identifiers___names" ][ identifier ] for identifier in identifiers )
    return [ U.DELIM.join( identifiers ), names ]


def feature_headers( feature: dict ) -> list:
    prefix = feature[ "prefix" ]
    label = feature[ "label" ]
    return [
        f"{prefix}_Identifiers (comma delimited non-redundant {label} identifiers across all member sequences)",
        f"{prefix}_Names (' // ' delimited {label} names aligned to {prefix}_Identifiers; "
        f"' // ' used because names may contain commas, semicolons, or pipes)",
    ]


def feature_cells( feature: dict, og_id: str ) -> list:
    identifiers = sorted( feature[ "orthogroups___identifiers" ].get( og_id, () ) )
    names = U.NAME_DELIM.join( feature[ "identifiers___names" ][ identifier ] for identifier in identifiers )
    return [ U.DELIM.join( identifiers ), names ]


# ---------------------------------------------------------------------------
# Gene families / gene groups (invert AGS FASTAs; LOG-AND-SKIP)
# ---------------------------------------------------------------------------
def iter_fasta_member_headers( fasta_path: Path ):
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if not line.startswith( '>' ):
                continue
            header = line[ 1: ].strip()
            if header.startswith( 'g_' ):
                yield header


def load_gene_families( feature: dict, gene_families_dir: Path, sequences___orthogroups: dict ):
    if not gene_families_dir.is_dir():
        print( f"CRITICAL ERROR: gene_families directory not found: {gene_families_dir}", file = sys.stderr )
        sys.exit( 1 )
    family_count = 0
    for family_dir in sorted( gene_families_dir.iterdir() ):
        if not family_dir.is_dir():
            continue
        ags_files = sorted( family_dir.rglob( "16_ai-ags-*.aa" ) )
        if not ags_files:
            continue
        family_slug = family_dir.name
        family_count += 1
        for ags_file in ags_files:
            for sequence_id in iter_fasta_member_headers( ags_file ):
                og_id = sequences___orthogroups.get( sequence_id )
                if og_id is None:
                    feature[ "skipped_non_orthogroup" ] += 1
                    continue
                add_feature_annotation( feature, og_id, family_slug, family_slug )
    print( f"[001] gene_families: {family_count} families scanned" )


def load_gene_group_metadata( metadata_path: Path ) -> dict:
    sanitized___id_name = {}
    if not metadata_path.is_file():
        print( f"[001] WARNING: gene_groups HGNC metadata not found ({metadata_path}); "
               f"gene group ids will fall back to sanitized names" )
        return sanitized___id_name
    with open( metadata_path, 'r' ) as input_metadata:
        header_ids___indices = U.build_header_index( input_metadata.readline() )
        index_id = header_ids___indices[ "Gene_Group_ID" ]
        index_name = header_ids___indices[ "Gene_Group_Name" ]
        index_sanitized = header_ids___indices[ "Sanitized_Name" ]
        for line in input_metadata:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sanitized___id_name[ parts[ index_sanitized ] ] = ( parts[ index_id ], parts[ index_name ] )
    return sanitized___id_name


GENE_GROUP_NAME_FALLBACKS = { "snap_family": "Synaptosomal-Associated Proteins" }


def load_gene_groups( feature: dict, gene_groups_dir: Path, sanitized___id_name: dict,
                    sequences___orthogroups: dict ):
    if not gene_groups_dir.is_dir():
        print( f"CRITICAL ERROR: gene_groups directory not found: {gene_groups_dir}", file = sys.stderr )
        sys.exit( 1 )
    group_dirs_seen = set()
    for instance_dir in sorted( gene_groups_dir.glob( "gene_groups-*" ) ):
        for ags_file in sorted( instance_dir.rglob( "16_ai-ags-*.aa" ) ):
            sanitized = None
            for part in ags_file.parts:
                if part.startswith( "gene_group-" ):
                    sanitized = part[ len( "gene_group-" ): ]
                    break
            if sanitized is None:
                continue
            group_dirs_seen.add( sanitized )
            if sanitized in sanitized___id_name:
                gene_group_id, gene_group_name = sanitized___id_name[ sanitized ]
            else:
                gene_group_id = sanitized
                gene_group_name = GENE_GROUP_NAME_FALLBACKS.get( sanitized, sanitized )
            guard_name( feature[ "label" ], gene_group_id, gene_group_name )
            for sequence_id in iter_fasta_member_headers( ags_file ):
                og_id = sequences___orthogroups.get( sequence_id )
                if og_id is None:
                    feature[ "skipped_non_orthogroup" ] += 1
                    continue
                add_feature_annotation( feature, og_id, gene_group_id, gene_group_name )
    print( f"[001] gene_groups: {len( group_dirs_seen )} groups scanned" )


# ---------------------------------------------------------------------------
# Self-documenting headers
# ---------------------------------------------------------------------------
def clade_header( clade, clades___descendant_count, clades___species, clades___structures, total_selected ):
    present_numbers = ','.join( U.structure_number( s ) for s in clades___structures[ clade ] )
    present = f"present in structures {present_numbers} of {total_selected} selected"
    if clades___descendant_count[ clade ] == 0:
        species_name = next( iter( clades___species[ clade ] ) )
        return ( f"{clade} (member sequence count of this orthogroup within tip {clade} = species "
                 f"{species_name}; {present})" )
    return ( f"{clade} (member sequence count of this orthogroup within clade {clade}; "
             f"{clades___descendant_count[ clade ]} descendant species; {present})" )


def main():
    parser = argparse.ArgumentParser( description = "Build the orthogroups_X_leonid table" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    species_set_name = config[ "species_set_name" ]
    annotation_sources = config[ "annotation_sources" ]
    annogroup_sources = config.get( "annogroup_sources", [ "pfam", "go", "panther" ] )
    selected_structures = config[ "inputs" ][ "deconvolution_structures" ]

    orthogroups_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_file" ] )
    annogroups_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "annogroups_dir" ] )
    clade_map_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "clade_species_mappings" ] )
    gene_families_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "gene_families_dir" ] )
    gene_groups_dir = U.resolve_input_path( workflow_root, config[ "inputs" ][ "gene_groups_dir" ] )
    gene_groups_hgnc_metadata = U.resolve_input_path( workflow_root, config[ "inputs" ][ "gene_groups_hgnc_metadata" ] )

    output_base = Path( args.output_dir )
    output_dir = output_base / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    table_filename = U.build_timestamped_table_filename( U.OUTPUT_TABLE_STEM )
    output_path = output_dir / table_filename

    # ---- inputs exist? -----------------------------------------------------
    for required in ( orthogroups_path, clade_map_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required input not found: {required}", file = sys.stderr )
            sys.exit( 1 )
    if not annogroups_dir.is_dir():
        print( f"CRITICAL ERROR: annogroups directory not found: {annogroups_dir}", file = sys.stderr )
        sys.exit( 1 )

    # ---- clades ------------------------------------------------------------
    ( clades___species, clades___descendant_count, clades___structures, tip_species,
      species___ancestor_clades, union_ordered_clades, full_coverage_clades ) = load_clade_data(
        clade_map_path, selected_structures )
    total_selected = len( selected_structures )
    print( f"[001] deconvolution: {len( union_ordered_clades )} non-redundant clades across "
           f"{total_selected} structures ({sorted( U.structure_number( s ) for s in selected_structures )}); "
           f"{len( tip_species )} tips; {len( full_coverage_clades )} full-coverage root clade(s)" )

    # ---- orthogroups -------------------------------------------------------
    orthogroups, sequences___orthogroups = load_orthogroups( orthogroups_path )
    print( f"[001] loaded {len( orthogroups )} orthogroups; {len( sequences___orthogroups )} member sequences" )

    # ---- annotations (per source) -----------------------------------------
    sources___accession_names = {}
    sources___orthogroup_accessions = {}
    for source in annotation_sources:
        source_dir = annogroups_dir / species_set_name / source
        map_path = source_dir / f"2_ai-{source}-annogroup_map.tsv"
        membership_path = source_dir / f"2_ai-{source}-annogroup_membership.tsv"
        for required in ( map_path, membership_path ):
            if not required.is_file():
                print( f"CRITICAL ERROR: required {source} input not found: {required}", file = sys.stderr )
                sys.exit( 1 )
        accessions___names = load_feature_accession_names( map_path, source )
        missing_report_path = output_dir / f"1_ai-{source}-sequences_absent_from_orthogroups.tsv"
        orthogroups___accessions = aggregate_source_accessions(
            membership_path, source, accessions___names, sequences___orthogroups, missing_report_path )
        sources___accession_names[ source ] = accessions___names
        sources___orthogroup_accessions[ source ] = orthogroups___accessions
        annotated_orthogroups = len( orthogroups___accessions )
        print( f"[001] {source}: {len( accessions___names )} feature accessions; "
               f"{annotated_orthogroups} orthogroups carry >=1 {source} annotation" )

    annogroup_features = []
    for source in annogroup_sources:
        prefix = U.annogroup_prefix_for_source( source )
        source_dir = annogroups_dir / species_set_name / source
        map_path = source_dir / f"2_ai-{source}-annogroup_map.tsv"
        membership_path = source_dir / f"2_ai-{source}-annogroup_membership.tsv"
        for required in ( map_path, membership_path ):
            if not required.is_file():
                print( f"CRITICAL ERROR: required {source} annogroup input not found: {required}", file = sys.stderr )
                sys.exit( 1 )
        annogroup_ids___names = load_annogroup_map( map_path, prefix )
        missing_report_path = output_dir / f"1_ai-{source}-annogroup_sequences_absent_from_orthogroups.tsv"
        feature = aggregate_source_annogroups(
            membership_path, prefix, annogroup_ids___names, sequences___orthogroups, missing_report_path )
        annogroup_features.append( feature )
        print( f"[001] {prefix}: {len( feature[ 'identifiers___names' ] )} annogroup identifiers; "
               f"{len( feature[ 'orthogroups___identifiers' ] )} orthogroups carry >=1 annogroup" )

    feature_gene_families = new_feature( "Gene_Families", "gene family" )
    load_gene_families( feature_gene_families, gene_families_dir, sequences___orthogroups )
    print( f"[001] Gene_Families: {len( feature_gene_families[ 'orthogroups___identifiers' ] )} orthogroups; "
           f"{feature_gene_families[ 'skipped_non_orthogroup' ]} non-orthogroup member(s) skipped (logged)" )

    sanitized___id_name = load_gene_group_metadata( gene_groups_hgnc_metadata )
    feature_gene_groups = new_feature( "Gene_Groups", "gene group" )
    load_gene_groups( feature_gene_groups, gene_groups_dir, sanitized___id_name, sequences___orthogroups )
    print( f"[001] Gene_Groups: {len( feature_gene_groups[ 'orthogroups___identifiers' ] )} orthogroups; "
           f"{feature_gene_groups[ 'skipped_non_orthogroup' ]} non-orthogroup member(s) skipped (logged)" )

    # ---- header ------------------------------------------------------------
    header_columns = [
        "Orthogroup_ID (OrthoHMM orthogroup identifier)",
        "Sequence_IDs (comma delimited full GIGANTIC member protein identifiers in this orthogroup)",
        "Member_Sequence_Count (number of member protein sequences in this orthogroup)",
        "Is_Singleton (yes if the orthogroup has exactly one member sequence else no)",
    ]
    for source in annotation_sources:
        label = source.upper() if source in ( "go", ) else source.capitalize()
        # canonical display labels: Pfam, GO, PANTHER
        display = { "pfam": "Pfam", "go": "GO", "panther": "PANTHER" }.get( source, label )
        header_columns.append(
            f"{display}_Identifiers (comma delimited non-redundant {display} identifiers across all member sequences)" )
        header_columns.append(
            f"{display}_Names ('space slash slash space' delimited {display} names aligned to "
            f"{display}_Identifiers; delimited by ' // ' because names may contain commas, semicolons, or pipes)" )
    for feature in annogroup_features:
        header_columns.extend( annogroup_feature_headers( feature ) )
    header_columns.extend( feature_headers( feature_gene_families ) )
    header_columns.extend( feature_headers( feature_gene_groups ) )
    header_columns.extend(
        clade_header( clade, clades___descendant_count, clades___species, clades___structures, total_selected )
        for clade in union_ordered_clades )
    header_line = '\t'.join( header_columns )

    # ---- write rows --------------------------------------------------------
    rows_written = 0
    with open( output_path, 'w' ) as output_table:
        output_table.write( header_line + '\n' )
        for og_id, members in orthogroups:
            member_count = len( members )
            is_singleton = "yes" if member_count == 1 else "no"

            # per-species member counts (fail fast on non-tip species)
            species___counts = defaultdict( int )
            for member in members:
                genus_species = U.genus_species_from_full_gigantic_id( member )
                if genus_species is None or genus_species not in tip_species:
                    print( f"CRITICAL ERROR: orthogroup {og_id} member {member} maps to species "
                           f"{genus_species!r}, which is not a tree tip -- it would be silently uncounted",
                           file = sys.stderr )
                    sys.exit( 1 )
                species___counts[ genus_species ] += 1

            # per-clade counts (member counted in every ancestor clade)
            clades___counts = defaultdict( int )
            for genus_species, count in species___counts.items():
                for clade_id_name in species___ancestor_clades[ genus_species ]:
                    clades___counts[ clade_id_name ] += count

            # research-integrity: full-coverage (root) clade totals == member_count
            for clade in full_coverage_clades:
                if clades___counts.get( clade, 0 ) != member_count:
                    print( f"CRITICAL ERROR: orthogroup {og_id} count at full-coverage clade {clade} "
                           f"({clades___counts.get( clade, 0 )}) != Member_Sequence_Count {member_count}",
                           file = sys.stderr )
                    sys.exit( 1 )

            row = [ og_id, U.DELIM.join( members ), str( member_count ), is_singleton ]
            for source in annotation_sources:
                accessions = sorted( sources___orthogroup_accessions[ source ].get( og_id, () ) )
                names = [ sources___accession_names[ source ][ accession ] for accession in accessions ]
                row.append( U.DELIM.join( accessions ) )
                row.append( U.NAME_DELIM.join( names ) )
            for feature in annogroup_features:
                row.extend( annogroup_feature_cells( feature, og_id ) )
            row.extend( feature_cells( feature_gene_families, og_id ) )
            row.extend( feature_cells( feature_gene_groups, og_id ) )
            row.extend( str( clades___counts.get( clade, 0 ) ) for clade in union_ordered_clades )
            output_table.write( '\t'.join( row ) + '\n' )
            rows_written += 1

    print( f"[001] wrote {rows_written} orthogroup rows ({len( header_columns )} columns) -> {output_path}" )
    U.write_output_table_pointer( output_base, table_filename )


if __name__ == '__main__':
    main()
