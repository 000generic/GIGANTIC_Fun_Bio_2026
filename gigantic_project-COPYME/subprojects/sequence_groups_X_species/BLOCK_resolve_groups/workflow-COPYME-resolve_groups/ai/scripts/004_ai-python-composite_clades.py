# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Composite clades — classify each sequence group by where its member species fall on the species tree (four algorithms: exact, absent, core_urclade, core_early_clade)
# Human: Eric Edsinger

"""
Script 004 — Composite clades (one sequence-group set).

For every sequence group, classifies WHERE its member species fall on the species
tree, using the building-block clade GROUPS (config 'composite_clades') and the
curated manifest. Each manifest row picks one ALGORITHM testing the group's member
species:
  - exact            : members come from EXACTLY the listed component clades
  - absent           : members are ABSENT from ALL listed clades
  - core_urclade     : members in an OUTGROUP of the target AND in an ingroup
                       (the target's Ur = last-common-ancestor core)
  - core_early_clade : members in two or more ingroups (the target's "Early" window
                       = its early descendant branches / the species tree's ambiguous nodes)
This is structure-independent (member species are stable across structures, Rule 6).

Input (the standard membership from Script 001):
  1-output/1_ai-<group_set_label>-sequence_group_membership.tsv
plus the clade->species mapping + the composite_clades config block + the manifest.

Outputs (4-output/):
  4_ai-<label>-composite_clades-per_group.tsv       (one column per algorithm)
  4_ai-<label>-composite_clades-summary_counts.tsv  (one row per manifest composite clade)
  composite_clades_detail_tables/4_ai-<label>-composite_clades-<cc_id>.tsv
        (rows = matching groups; columns = member SEQUENCE identifiers per relevant clade)
        When config declares annotation_index, each row ALSO carries, right after
        SequenceGroup_ID, the distinct annotation identifiers + names aggregated over
        ALL member sequences of the group, one <mode>_Identifiers/<mode>_Names pair per
        mode (PFAM, PANTHER, GO, Gene_Families, Gene_Groups) from the Script 006 index.

Fail-fast (§36): exits 1 if inputs / config / manifest are missing or invalid, or if
annotation_index is configured but the Script 006 index is missing.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U

# Identifiers use the bare comma (§34); the aligned *_Names cells use ' // ' because
# names carry commas (must match Script 006's annotation index).
NAME_DELIM = ' // '


def load_annotation_index( index_path: Path, member_sequences: set ):
    """
    Load the cross-producer annotation index (Script 006) restricted to member_sequences.

    Returns ( annotation_modes, sequences___mode_pairs ):
        annotation_modes         ordered list of modes (from the index header's
                                 '<mode>_Identifiers' columns), e.g. [ PFAM, PANTHER, ... ]
        sequences___mode_pairs   { sequence_id: { mode: [ ( identifier, name ), ... ] } }
    Only sequences present in member_sequences (and carrying >=1 annotation) are kept.
    """
    # Sequence_Identifier (...)	PFAM_Identifiers (...)	PFAM_Names (...)	PANTHER_Identifiers (...)	...
    with open( index_path, 'r' ) as input_index:
        header_ids___indices = U.build_header_index( input_index.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        annotation_modes = [ header_id[ : -len( "_Identifiers" ) ]
                             for header_id in header_ids___indices
                             if header_id.endswith( "_Identifiers" ) ]
        # Preserve the index's physical column order (build_header_index dict is
        # insertion-ordered from the header line).
        annotation_modes = sorted( annotation_modes, key = lambda mode: header_ids___indices[ f"{mode}_Identifiers" ] )
        modes___id_index = { mode: header_ids___indices[ f"{mode}_Identifiers" ] for mode in annotation_modes }
        modes___name_index = { mode: header_ids___indices[ f"{mode}_Names" ] for mode in annotation_modes }

        sequences___mode_pairs = {}
        for line in input_index:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_id = parts[ index_sequence ]
            if sequence_id not in member_sequences:
                continue
            mode_pairs = {}
            for mode in annotation_modes:
                identifiers_cell = parts[ modes___id_index[ mode ] ] if modes___id_index[ mode ] < len( parts ) else ''
                names_cell = parts[ modes___name_index[ mode ] ] if modes___name_index[ mode ] < len( parts ) else ''
                if not identifiers_cell:
                    continue
                identifiers = identifiers_cell.split( U.DELIM )
                names = names_cell.split( NAME_DELIM ) if names_cell else [ '' ] * len( identifiers )
                if len( names ) != len( identifiers ):
                    names = ( names + [ '' ] * len( identifiers ) )[ : len( identifiers ) ]
                mode_pairs[ mode ] = list( zip( identifiers, names ) )
            if mode_pairs:
                sequences___mode_pairs[ sequence_id ] = mode_pairs
    return annotation_modes, sequences___mode_pairs


def build_group_annotation_cells( annotation_modes, group_order, groups___sequences, sequences___mode_pairs ):
    """
    Per sequence group, aggregate the DISTINCT annotation ( identifier, name ) pairs over
    ALL of its member sequences, for each mode. Returns
        { group_id: { mode: ( identifiers_cell, names_cell ) } }
    identifiers_cell is comma delimited (sorted, distinct); names_cell is ' // ' delimited,
    aligned to the identifiers.
    """
    groups___mode_cells = {}
    for group_id in group_order:
        modes___ids_names = { mode: {} for mode in annotation_modes }
        for ( sequence_id, genus_species ) in groups___sequences[ group_id ]:
            mode_pairs = sequences___mode_pairs.get( sequence_id )
            if not mode_pairs:
                continue
            for mode, pairs in mode_pairs.items():
                for ( identifier, name ) in pairs:
                    modes___ids_names[ mode ][ identifier ] = name
        mode_cells = {}
        for mode in annotation_modes:
            identifiers = sorted( modes___ids_names[ mode ].keys() )
            names = [ modes___ids_names[ mode ][ identifier ] for identifier in identifiers ]
            mode_cells[ mode ] = ( U.DELIM.join( identifiers ), NAME_DELIM.join( names ) )
        groups___mode_cells[ group_id ] = mode_cells
    return groups___mode_cells


def sequence_in_detail_column( genus_species, kind, species_set ):
    """True if a member belongs in a detail-table column ('in' = its species in the clade; 'out' = outside)."""
    return ( genus_species in species_set ) if kind == "in" else ( genus_species not in species_set )


def detail_column_header( label, kind ):
    if kind == "in":
        return f"{label} (comma delimited member sequence identifiers of this group whose species is in {label})"
    return f"{label} (comma delimited member sequence identifiers of this group outside the focal clade; the {label} members)"


def main():
    parser = argparse.ArgumentParser( description = "Composite clades for a sequence-group set (four algorithms over member species)" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    # Optional per-producer overrides (multi-producer runner); fall back to config.
    parser.add_argument( '--group_set_label', default = None )
    parser.add_argument( '--group_attributes', default = None )
    parser.add_argument( '--workflow_root', default = None )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = Path( args.workflow_root ).resolve() if args.workflow_root else U.workflow_root_from_output_dir( args.output_dir )
    group_set_label = args.group_set_label if args.group_set_label else config[ "group_set_label" ]
    output_base = Path( args.output_dir )

    # Optional per-group attributes carried (opaque) after SequenceGroup_ID on the per-group
    # table; reserve the engine's own identity/count columns so they are never duplicated.
    carried_headers, group_ids___carried_cells = U.load_group_attributes(
        workflow_root, config, { "SequenceGroup_ID", "Sequence_Count", "Species_Count" },
        override_group_attributes = args.group_attributes )
    empty_carried = [ '' ] * len( carried_headers )

    membership_path = output_base / "1-output" / f"1_ai-{group_set_label}-sequence_group_membership.tsv"
    mappings_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "clade_species_mappings" ] )
    manifest_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "composite_clades_manifest" ] )
    for required in ( membership_path, mappings_path, manifest_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required input not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    composites = U.load_composite_clades( config, mappings_path )
    manifest = U.load_composite_clades_manifest( manifest_path, composites )
    manifest_exact_ids = { entry[ "cc_id" ] for entry in manifest if entry[ "algorithm" ] == "exact" }
    non_exact_entries = [ entry for entry in manifest if entry[ "algorithm" ] != "exact" ]

    # ---- read membership: group -> member species + group -> [(sequence, species)] ----
    # SequenceGroup_ID (...)	Sequence_Identifier (...)	Genus_Species (...)
    group_order = []
    seen_groups = set()
    groups___species = defaultdict( set )
    groups___sequences = defaultdict( list )   # list of ( sequence_id, genus_species )
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_group = header_ids___indices[ "SequenceGroup_ID" ]
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_genus_species = header_ids___indices[ "Genus_Species" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_group_id = parts[ index_group ]
            genus_species = parts[ index_genus_species ]
            if sequence_group_id not in seen_groups:
                seen_groups.add( sequence_group_id )
                group_order.append( sequence_group_id )
            groups___species[ sequence_group_id ].add( genus_species )
            groups___sequences[ sequence_group_id ].append( ( parts[ index_sequence ], genus_species ) )

    if not group_order:
        print( f"CRITICAL ERROR: zero member rows in {membership_path.name}", file = sys.stderr )
        sys.exit( 1 )

    # ---- classify every group by its member species -------------------------
    groups___matches = defaultdict( lambda: defaultdict( list ) )
    cc_id___groups = defaultdict( list )
    for sequence_group_id in group_order:
        member_species = groups___species[ sequence_group_id ]
        own_exact_id = U.composite_clade_id( U.exact_components_of_species( member_species, composites ) )
        if own_exact_id in manifest_exact_ids:
            groups___matches[ sequence_group_id ][ "exact" ].append( own_exact_id )
            cc_id___groups[ own_exact_id ].append( sequence_group_id )
        for entry in non_exact_entries:
            if U.sequence_group_matches_composite_clade( entry, member_species, composites ):
                groups___matches[ sequence_group_id ][ entry[ "algorithm" ] ].append( entry[ "cc_id" ] )
                cc_id___groups[ entry[ "cc_id" ] ].append( sequence_group_id )

    output_dir = output_base / "4-output"
    output_dir.mkdir( parents = True, exist_ok = True )

    # ---- Deliverable 1: per-group table (one column per algorithm) ----------
    per_group_path = output_dir / f"4_ai-{group_set_label}-composite_clades-per_group.tsv"
    per_group_header = (
        [ "SequenceGroup_ID (identifier of the sequence group from the producer)" ]
        + carried_headers
        + [
            "Composite_Clade-exact (the group's exact composite clade cc_<components>-exact when curated, else None; one per group)",
            "Composite_Clades-absent (comma delimited absent composite clades this group matches i.e. members absent from all those clades, else None)",
            "Composite_Clades-core_urclade (comma delimited core_urclade composite clades matched i.e. members in an outgroup of the target and in an ingroup, else None)",
            "Composite_Clades-core_early_clade (comma delimited core_early_clade composite clades matched i.e. members in two or more early ingroup branches, else None)",
        ]
    )
    with open( per_group_path, 'w' ) as output_per_group:
        output_per_group.write( '\t'.join( per_group_header ) + '\n' )
        for sequence_group_id in group_order:
            matches = groups___matches.get( sequence_group_id, {} )
            cells = []
            for algorithm in U.COMPOSITE_CLADE_ALGORITHMS:
                matched = matches.get( algorithm, [] )
                cells.append( U.DELIM.join( matched ) if matched else "None" )
            carried = group_ids___carried_cells.get( sequence_group_id, empty_carried )
            output_per_group.write( '\t'.join( [ sequence_group_id ] + carried + cells ) + '\n' )

    # ---- Deliverable 2: summary counts --------------------------------------
    summary_path = output_dir / f"4_ai-{group_set_label}-composite_clades-summary_counts.tsv"
    summary_header = [
        "Composite_Clade (composite clade identifier cc_<name or components>-<algorithm>)",
        "Algorithm (exact, absent, core_urclade, or core_early_clade)",
        "Definition (the components for exact, the absent-from clades for absent, or the target and ingroups for the core algorithms)",
        "SequenceGroup_Count (count of sequence groups that match this composite clade)",
    ]
    with open( summary_path, 'w' ) as output_summary:
        output_summary.write( '\t'.join( summary_header ) + '\n' )
        for entry in manifest:
            count = len( cc_id___groups.get( entry[ "cc_id" ], [] ) )
            output_summary.write( f"{entry[ 'cc_id' ]}\t{entry[ 'algorithm' ]}\t{entry[ 'definition' ]}\t{count}\n" )

    # ---- Annotation columns for the detail tables (Leonid 2026-07) ----------
    # Per sequence group, the distinct annotation identifiers + names aggregated over
    # ALL member sequences, for each mode (PFAM/PANTHER/GO/Gene_Families/Gene_Groups),
    # from the cross-producer index (Script 006). Required when config declares
    # annotation_index; otherwise the detail tables keep their prior schema.
    annotation_index_configured = bool( config.get( "annotation_index" ) )
    annotation_modes = []
    groups___annotation_cells = {}
    if annotation_index_configured:
        annotation_index_path = output_base.parent / "annotation_index" / "6_ai-sequence_annotation_index.tsv"
        if not annotation_index_path.is_file():
            print( f"CRITICAL ERROR: annotation_index is configured but the index is missing: {annotation_index_path}\n"
                   f"Run Script 006 (build_annotation_index) before Script 004.", file = sys.stderr )
            sys.exit( 1 )
        member_sequences = { sequence_id for sequences in groups___sequences.values()
                             for ( sequence_id, genus_species ) in sequences }
        annotation_modes, sequences___mode_pairs = load_annotation_index( annotation_index_path, member_sequences )
        groups___annotation_cells = build_group_annotation_cells( annotation_modes, group_order,
                                                                  groups___sequences, sequences___mode_pairs )
        print( f"[004 {group_set_label}] annotation index: {len( sequences___mode_pairs )} of {len( member_sequences )} "
               f"member sequences annotated across modes {annotation_modes}" )

    annotation_headers = []
    for mode in annotation_modes:
        annotation_headers.append( f"{mode}_Identifiers (comma delimited distinct {mode} identifiers aggregated over ALL member sequences of this sequence group)" )
        annotation_headers.append( f"{mode}_Names (' // ' delimited {mode} names aligned to {mode}_Identifiers)" )
    empty_annotation_cells = [ '' ] * len( annotation_headers )

    def annotation_cells_for( sequence_group_id ):
        mode_cells = groups___annotation_cells.get( sequence_group_id )
        if not mode_cells:
            return list( empty_annotation_cells )
        cells = []
        for mode in annotation_modes:
            identifiers_cell, names_cell = mode_cells.get( mode, ( '', '' ) )
            cells.append( identifiers_cell )
            cells.append( names_cell )
        return cells

    # ---- Deliverable 3: one detail table per manifest composite clade -------
    detail_dir = output_dir / "composite_clades_detail_tables"
    detail_dir.mkdir( parents = True, exist_ok = True )
    detail_tables_written = 0
    for entry in manifest:
        cc_id = entry[ "cc_id" ]
        detail_columns = entry[ "detail_columns" ]
        groups = sorted( cc_id___groups.get( cc_id, [] ) )
        detail_path = detail_dir / f"4_ai-{group_set_label}-composite_clades-{cc_id}.tsv"
        detail_header = (
            [ "SequenceGroup_ID (sequence group identifier; matches the composite clade)" ]
            + annotation_headers
            + [ detail_column_header( label, kind ) for ( label, kind, species_set ) in detail_columns ]
        )
        with open( detail_path, 'w' ) as output_detail:
            output_detail.write( '\t'.join( detail_header ) + '\n' )
            for sequence_group_id in groups:
                sequences = groups___sequences[ sequence_group_id ]
                column_cells = []
                for ( label, kind, species_set ) in detail_columns:
                    sequence_ids = [ sequence_id for ( sequence_id, genus_species ) in sequences
                                     if sequence_in_detail_column( genus_species, kind, species_set ) ]
                    column_cells.append( U.DELIM.join( sorted( sequence_ids ) ) )
                output_detail.write( '\t'.join( [ sequence_group_id ] + annotation_cells_for( sequence_group_id ) + column_cells ) + '\n' )
        detail_tables_written += 1

    matched_total = len( { sequence_group_id for groups in cc_id___groups.values() for sequence_group_id in groups } )
    print( f"[004 {group_set_label}] {len( group_order )} groups classified; {matched_total} in >=1 curated composite clade; "
           f"per-group + summary ({len( manifest )} composite clades) + {detail_tables_written} detail tables" )


if __name__ == '__main__':
    main()
