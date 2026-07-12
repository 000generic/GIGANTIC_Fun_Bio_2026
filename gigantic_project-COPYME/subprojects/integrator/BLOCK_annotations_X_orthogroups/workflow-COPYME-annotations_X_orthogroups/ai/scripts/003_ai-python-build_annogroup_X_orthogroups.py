#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Build Table 1 — annogroups joined to their orthogroups, kept when they touch a qualifying (non-bilaterian-metazoan) orthogroup
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18 | Purpose: Import-only refactor — read annogroups (members + accessions/definitions) DIRECTLY from the annogroups subproject (4-type framework); drop OCL dependency
# Human: Eric Edsinger

"""
Script 003 — Table 1: annogroups X orthogroups.

For each pfam annogroup (types from config; default feature + combination +
architecture + absent), map its member proteins to the orthogroups they belong to (shared
full GIGANTIC IDs), then KEEP the annogroup if at least one of its orthogroups is
QUALIFYING — class non_bilaterian_metazoan (zero bilaterians AND >=1 non-bilaterian
metazoan). Annogroups with no qualifying orthogroup are dropped.

For each kept annogroup ALL of its orthogroups are reported, grouped by the four
composition classes, with per-class counts and comma-delimited ID lists, PLUS a
finer set of named metazoan-phylum-composition classes (Ctenophora_Only,
Mixed_Ctenophora_Cnidaria_Only, Mixed_With_NonMetazoan, ... — Eric-specified,
2026-06-23). The named classes come from Script 001's per-orthogroup
Metazoan_Phylum_Signature + Has_NonMetazoan via U.named_phylum_class(); they are
disjoint and a curated subset (an orthogroup may match none), so they do NOT
necessarily sum to Orthogroup_Count — the coarse four-class counts remain the
reconciling layer.

Annogroups are imported DIRECTLY from the annogroups subproject (no OCL
dependency). Per source the subproject exposes, structure-independent:
  - 2_ai-<source>-annogroup_map.tsv         annogroup -> type, accessions, definitions
  - 2_ai-<source>-annogroup_membership.tsv  (sequence, annogroup, type) rows

Inputs:
  - orthogroups file (headerless)            -> protein -> orthogroup map
  - 1-output composition table (Script 001)  -> orthogroup -> composition class
  - annogroups subproject map                -> annogroup -> type / accessions / definitions
  - annogroups subproject membership         -> annogroup -> member Sequence_IDs (per type)

Fail-fast: exits 1 if any required input is missing.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U

QUALIFYING_CLASS = "non_bilaterian_metazoan"


def load_orthogroup_classes( composition_path: Path ) -> dict:
    """orthogroup_id -> composition_class (from Script 001's 1-output table)."""
    orthogroups___classes = {}
    with open( composition_path, 'r' ) as input_composition:
        header_line = input_composition.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_class = header_ids___indices[ "Composition_Class" ]
        for line in input_composition:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroups___classes[ parts[ index_og ] ] = parts[ index_class ]
    return orthogroups___classes


def load_orthogroup_phylum( composition_path: Path ) -> dict:
    """
    orthogroup_id -> ( metazoan_phylum_signature frozenset, has_nonmetazoan bool )
    from Script 001's 1-output table. Used to resolve each orthogroup's named
    phylum-composition class via U.named_phylum_class().
    """
    orthogroups___phylum = {}
    with open( composition_path, 'r' ) as input_composition:
        header_line = input_composition.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_signature = header_ids___indices[ "Metazoan_Phylum_Signature" ]
        index_has_nonmeta = header_ids___indices[ "Has_NonMetazoan" ]
        for line in input_composition:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            signature = U.parse_signature_cell( parts[ index_signature ] if index_signature < len( parts ) else "" )
            has_nonmetazoan = ( parts[ index_has_nonmeta ] == "yes" ) if index_has_nonmeta < len( parts ) else False
            orthogroups___phylum[ parts[ index_og ] ] = ( signature, has_nonmetazoan )
    return orthogroups___phylum


def load_protein_to_orthogroup( orthogroups_path: Path ) -> dict:
    """member_full_id -> orthogroup_id (from the headerless orthogroups table)."""
    proteins___orthogroups = {}
    with open( orthogroups_path, 'r' ) as input_orthogroups:
        # Headerless: OG_ID\tmember_full_id\tmember_full_id...
        for line in input_orthogroups:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            orthogroup_id = parts[ 0 ]
            for member in parts[ 1: ]:
                if member:
                    proteins___orthogroups[ member ] = orthogroup_id
    return proteins___orthogroups


def load_annogroup_annotations( map_path: Path ) -> dict:
    """
    annogroup_id -> ( annogroup_type, accessions, definitions ) from the annogroups
    subproject map. Defining_Features holds the accessions; Annotation_Definitions
    the 'definition ==accession' pairs. Used to attach pfam context to Table 1.
    """
    annogroups___annotations = {}
    with open( map_path, 'r' ) as input_map:
        header_line = input_map.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_accessions = header_ids___indices[ "Defining_Features" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            annogroup_type = parts[ index_type ] if index_type < len( parts ) else ""
            accessions = parts[ index_accessions ] if index_accessions < len( parts ) else ""
            definitions = parts[ index_definitions ] if index_definitions < len( parts ) else ""
            annogroups___annotations[ annogroup_id ] = ( annogroup_type, accessions, definitions )
    return annogroups___annotations


def aggregate_annogroup_membership( membership_path: Path, included_types: set ) -> dict:
    """
    Read the annogroups subproject membership ONCE and aggregate, for every
    annogroup whose type is in included_types:
        annogroup_id -> { 'members': [ Sequence_Identifier, ... ],
                          'species': set( Genus_Species, ... ) }
    Genus_Species comes straight from the membership file (already resolved).
    """
    annogroups___members = defaultdict( list )
    annogroups___species = defaultdict( set )
    with open( membership_path, 'r' ) as input_membership:
        # Sequence_Identifier (...)\tGenus_Species (...)\tAnnogroup_ID (...)\tAnnogroup_Type (...)\tMember_Architecture_Coordinates (...)
        header_line = input_membership.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_genus_species = header_ids___indices[ "Genus_Species" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_type ] not in included_types:
                continue
            annogroup_id = parts[ index_annogroup ]
            annogroups___members[ annogroup_id ].append( parts[ index_sequence ] )
            annogroups___species[ annogroup_id ].add( parts[ index_genus_species ] )
    return annogroups___members, annogroups___species


def main():
    parser = argparse.ArgumentParser( description = "Build Table 1 — annogroups X orthogroups" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    input_orthogroups_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "orthogroups_file" ] )
    species_set_name = config[ "species_set_name" ]
    annotation_source = config[ "annotation_database" ]
    annogroup_types = set( config[ "annogroup_types" ] )

    # annogroups subproject per-source directory (structure-independent)
    input_annogroups_root = U.resolve_input_path( workflow_root, config[ "inputs" ][ "annogroups_dir" ] )
    input_source_dir = input_annogroups_root / species_set_name / annotation_source
    input_map_path = input_source_dir / f"2_ai-{annotation_source}-annogroup_map.tsv"
    input_membership_path = input_source_dir / f"2_ai-{annotation_source}-annogroup_membership.tsv"

    input_composition_path = U.resolve_composition_table_path( Path( args.output_dir ) )

    if not input_composition_path.is_file():
        print( f"CRITICAL ERROR: composition table not found: {input_composition_path}", file = sys.stderr )
        print( "  Script 001 (classify_orthogroups) must run before this script.", file = sys.stderr )
        sys.exit( 1 )
    if not input_orthogroups_path.is_file():
        print( f"CRITICAL ERROR: orthogroups file not found: {input_orthogroups_path}", file = sys.stderr )
        sys.exit( 1 )
    for required in ( input_map_path, input_membership_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: annogroups subproject file not found: {required}", file = sys.stderr )
            print( f"  Verify inputs.annogroups_dir / species_set / source expose the annogroup map + membership.", file = sys.stderr )
            print( f"  Run the annogroups subproject (BLOCK_build_annogroups) for source '{annotation_source}' first.", file = sys.stderr )
            sys.exit( 1 )

    orthogroups___classes = load_orthogroup_classes( input_composition_path )
    print( f"[003] loaded {len( orthogroups___classes )} orthogroup composition classes" )
    orthogroups___phylum = load_orthogroup_phylum( input_composition_path )
    print( f"[003] loaded phylum signatures for {len( orthogroups___phylum )} orthogroups" )
    proteins___orthogroups = load_protein_to_orthogroup( input_orthogroups_path )
    print( f"[003] loaded protein->orthogroup map: {len( proteins___orthogroups )} proteins" )
    annogroups___annotations = load_annogroup_annotations( input_map_path )
    print( f"[003] loaded annotations for {len( annogroups___annotations )} annogroups (map)" )
    annogroups___members, annogroups___species = aggregate_annogroup_membership( input_membership_path, annogroup_types )
    print( f"[003] aggregated membership for {len( annogroups___members )} annogroups of types {sorted( annogroup_types )}" )

    output_dir = Path( args.output_dir ) / "3-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_table_path = U.timestamped_output_path( output_dir, "3_ai-annogroups_X_orthogroups", Path( args.output_dir ) )

    header_columns = [
        "Annogroup_ID (canonical annogroup identifier from the annogroups subproject)",
        "Annogroup_Type (feature or combination or architecture or absent)",
        "Annotation_Accessions (comma delimited pfam accessions for this annogroup; empty for absent)",
        "Annotation_Definitions (semicolon delimited definition ==accession pairs for this annogroup passed through from the annogroups subproject map)",
        "Annogroup_Species_Count (number of unique species in the annogroup)",
        "Annogroup_Member_Protein_Count (number of member proteins in the annogroup)",
        "Members_With_Orthogroup_Count (count of member proteins that map to an orthogroup)",
        "Members_Without_Orthogroup_Count (count of member proteins that map to no orthogroup)",
        "Orthogroup_Count (number of distinct orthogroups the member proteins fall into)",
        "NonBilaterian_Metazoan_Orthogroup_Count (count of those orthogroups that are qualifying: zero bilaterians and at least one non-bilaterian metazoan)",
        "NonMetazoan_Only_Orthogroup_Count (count of those orthogroups made of only non-metazoan unicellular outgroups)",
        "Bilaterian_Only_Orthogroup_Count (count of those orthogroups made of only bilaterians)",
        "Mixed_With_Bilaterian_Orthogroup_Count (count of those orthogroups that contain bilaterians plus non-bilaterian members)",
        "NonBilaterian_Metazoan_Orthogroup_IDs (comma delimited qualifying orthogroup identifiers)",
        "NonMetazoan_Only_Orthogroup_IDs (comma delimited non-metazoan-unicell-only orthogroup identifiers)",
        "Bilaterian_Only_Orthogroup_IDs (comma delimited bilaterian-only orthogroup identifiers)",
        "Mixed_With_Bilaterian_Orthogroup_IDs (comma delimited bilaterian-plus-non-bilaterian orthogroup identifiers)",
        "All_Orthogroup_IDs (comma delimited list of every distinct orthogroup the member proteins fall into)",
    ]

    # Named phylum-composition columns (Eric-specified, 2026-06-23): for each named
    # class, a count of this annogroup's orthogroups in that class then a
    # comma-delimited ID list. Built from the single source of truth in utils so
    # column order, Script 004 validation, and the resolver never drift apart. These
    # named classes are DISJOINT (each orthogroup contributes to at most one) and
    # are a curated SUBSET of all observed signatures — they do NOT necessarily sum
    # to Orthogroup_Count (unlisted signatures are not named; see Script 001).
    for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS:
        description = U.PHYLUM_COMPOSITION_CLASS_DESCRIPTIONS[ class_key ]
        header_columns.append( f"{class_key}_Orthogroup_Count (count of those orthogroups whose composition is {description})" )
    for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS:
        description = U.PHYLUM_COMPOSITION_CLASS_DESCRIPTIONS[ class_key ]
        header_columns.append( f"{class_key}_Orthogroup_IDs (comma delimited identifiers of those orthogroups whose composition is {description})" )

    annogroup_total = 0
    annogroup_kept = 0

    with open( output_table_path, 'w' ) as output_table:
        output_table.write( '\t'.join( header_columns ) + '\n' )

        for annogroup_id in sorted( annogroups___members ):
            members = annogroups___members[ annogroup_id ]
            annogroup_total += 1

            members_with_orthogroup = 0
            members_without_orthogroup = 0
            orthogroup_ids = set()
            for member in members:
                orthogroup_id = proteins___orthogroups.get( member )
                if orthogroup_id is None:
                    members_without_orthogroup += 1
                    continue
                members_with_orthogroup += 1
                orthogroup_ids.add( orthogroup_id )

            non_bilaterian_metazoan_ogs = []
            non_metazoan_only_ogs = []
            bilaterian_only_ogs = []
            mixed_with_bilaterian_ogs = []
            # Named phylum-composition tally (disjoint; some orthogroups match none).
            named_class___ogs = { class_key: [] for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS }
            for orthogroup_id in sorted( orthogroup_ids ):
                composition_class = orthogroups___classes.get( orthogroup_id )
                if composition_class == "non_bilaterian_metazoan":
                    non_bilaterian_metazoan_ogs.append( orthogroup_id )
                elif composition_class == "non_metazoan_only":
                    non_metazoan_only_ogs.append( orthogroup_id )
                elif composition_class == "bilaterian_only":
                    bilaterian_only_ogs.append( orthogroup_id )
                elif composition_class == "mixed_with_bilaterian":
                    mixed_with_bilaterian_ogs.append( orthogroup_id )
                # An orthogroup with no class would be a referential-integrity
                # error; Script 004 validates that none slip through.

                # Named phylum-composition class (lossless signature -> curated name).
                signature, has_nonmetazoan = orthogroups___phylum.get( orthogroup_id, ( frozenset(), False ) )
                named_class = U.named_phylum_class( signature, has_nonmetazoan )
                if named_class is not None:
                    named_class___ogs[ named_class ].append( orthogroup_id )

            # KEEP rule (user-approved): keep iff at least one orthogroup is
            # qualifying (non_bilaterian_metazoan). Drop everything else.
            if len( non_bilaterian_metazoan_ogs ) == 0:
                continue

            annogroup_type, accessions, definitions = annogroups___annotations.get(
                annogroup_id, ( "", "", "" )
            )

            all_ogs = sorted( orthogroup_ids )
            row_fields = [
                annogroup_id,
                annogroup_type,
                accessions,
                definitions,
                str( len( annogroups___species[ annogroup_id ] ) ),
                str( len( members ) ),
                str( members_with_orthogroup ),
                str( members_without_orthogroup ),
                str( len( orthogroup_ids ) ),
                str( len( non_bilaterian_metazoan_ogs ) ),
                str( len( non_metazoan_only_ogs ) ),
                str( len( bilaterian_only_ogs ) ),
                str( len( mixed_with_bilaterian_ogs ) ),
                U.DELIM.join( non_bilaterian_metazoan_ogs ),
                U.DELIM.join( non_metazoan_only_ogs ),
                U.DELIM.join( bilaterian_only_ogs ),
                U.DELIM.join( mixed_with_bilaterian_ogs ),
                U.DELIM.join( all_ogs ),
            ]
            # Named phylum-composition counts then ID lists (same order as header).
            for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS:
                row_fields.append( str( len( named_class___ogs[ class_key ] ) ) )
            for class_key in U.PHYLUM_COMPOSITION_CLASS_KEYS:
                row_fields.append( U.DELIM.join( named_class___ogs[ class_key ] ) )

            output_table.write( '\t'.join( row_fields ) + '\n' )
            annogroup_kept += 1

    print( f"[003] annogroups kept (>=1 qualifying orthogroup): {annogroup_kept} of {annogroup_total} -> {output_table_path}" )

    if annogroup_total == 0:
        print( "CRITICAL ERROR: zero annogroups read — membership appears empty for the configured types", file = sys.stderr )
        sys.exit( 1 )


if __name__ == '__main__':
    main()
