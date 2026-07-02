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

Fail-fast (§36): exits 1 if inputs / config / manifest are missing or invalid.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U


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
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    group_set_label = config[ "group_set_label" ]
    output_base = Path( args.output_dir )

    # Optional per-group attributes carried (opaque) after SequenceGroup_ID on the per-group
    # table; reserve the engine's own identity/count columns so they are never duplicated.
    carried_headers, group_ids___carried_cells = U.load_group_attributes(
        workflow_root, config, { "SequenceGroup_ID", "Sequence_Count", "Species_Count" } )
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

    # ---- Deliverable 3: one detail table per manifest composite clade -------
    detail_dir = output_dir / "composite_clades_detail_tables"
    detail_dir.mkdir( parents = True, exist_ok = True )
    detail_tables_written = 0
    for entry in manifest:
        cc_id = entry[ "cc_id" ]
        detail_columns = entry[ "detail_columns" ]
        groups = sorted( cc_id___groups.get( cc_id, [] ) )
        detail_path = detail_dir / f"4_ai-{group_set_label}-composite_clades-{cc_id}.tsv"
        detail_header = [
            "SequenceGroup_ID (sequence group identifier; matches the composite clade)",
        ] + [ detail_column_header( label, kind ) for ( label, kind, species_set ) in detail_columns ]
        with open( detail_path, 'w' ) as output_detail:
            output_detail.write( '\t'.join( detail_header ) + '\n' )
            for sequence_group_id in groups:
                sequences = groups___sequences[ sequence_group_id ]
                column_cells = []
                for ( label, kind, species_set ) in detail_columns:
                    sequence_ids = [ sequence_id for ( sequence_id, genus_species ) in sequences
                                     if sequence_in_detail_column( genus_species, kind, species_set ) ]
                    column_cells.append( U.DELIM.join( sorted( sequence_ids ) ) )
                output_detail.write( '\t'.join( [ sequence_group_id ] + column_cells ) + '\n' )
        detail_tables_written += 1

    matched_total = len( { sequence_group_id for groups in cc_id___groups.values() for sequence_group_id in groups } )
    print( f"[004 {group_set_label}] {len( group_order )} groups classified; {matched_total} in >=1 curated composite clade; "
           f"per-group + summary ({len( manifest )} composite clades) + {detail_tables_written} detail tables" )


if __name__ == '__main__':
    main()
