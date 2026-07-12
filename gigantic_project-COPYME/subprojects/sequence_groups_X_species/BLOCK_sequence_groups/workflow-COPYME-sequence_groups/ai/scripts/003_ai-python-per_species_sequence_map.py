# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Per-species sequence map — pivot the sequence-group membership into a wide table of member sequence identifiers per species
# Human: Eric Edsinger

"""
Script 003 — Per-species sequence map (one sequence-group set).

The companion to the deconvolution (Script 002): the same wide per-species layout,
but each cell holds the member SEQUENCE IDENTIFIERS instead of a count. Rows are
sequence groups; columns are species (Genus_species); each cell is the
comma-delimited member sequence identifiers of that group whose species is that
column (empty when the group has no member in that species). This is the wide form
of the long standard membership.

Input (the standard membership from Script 001):
  1-output/1_ai-<group_set_label>-sequence_group_membership.tsv
      SequenceGroup_ID  Sequence_Identifier  Genus_Species

Output (3-output/):
  3_ai-<group_set_label>-sequences_per_species.tsv
      SequenceGroup_ID, Sequence_Count, Species_Count, then one column per species.

Fail-fast (§36): exits 1 if the membership is missing or empty.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U


def main():
    parser = argparse.ArgumentParser( description = "Per-species sequence map — sequence group x species -> member sequence identifiers" )
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

    # Optional per-group attributes carried (opaque) after SequenceGroup_ID; reserve the
    # engine's own identity/count columns so they are never duplicated.
    carried_headers, group_ids___carried_cells = U.load_group_attributes(
        workflow_root, config, { "SequenceGroup_ID", "Sequence_Count", "Species_Count" },
        override_group_attributes = args.group_attributes )
    empty_carried = [ '' ] * len( carried_headers )

    membership_path = U.membership_output_path( output_base, group_set_label )
    if not membership_path.is_file():
        print( f"CRITICAL ERROR: required file not found: {membership_path}", file = sys.stderr )
        sys.exit( 1 )

    # ---- group -> species -> [sequence identifiers] (from the standard membership) ----
    # SequenceGroup_ID (...)	Sequence_Identifier (...)	Genus_Species (...)
    groups___species___sequences = defaultdict( lambda: defaultdict( list ) )
    group_order = []
    seen_groups = set()
    all_species = set()
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
            groups___species___sequences[ sequence_group_id ][ genus_species ].append( parts[ index_sequence ] )
            all_species.add( genus_species )

    if not group_order:
        print( f"CRITICAL ERROR: zero member rows in {membership_path.name}", file = sys.stderr )
        sys.exit( 1 )

    species_columns = sorted( all_species )

    output_dir = output_base / "3-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_path = U.timestamped_output_path(
        output_dir,
        f"3_ai-{group_set_label}-sequences_per_species",
        output_base,
    )

    header = (
        [ "SequenceGroup_ID (identifier of the sequence group from the producer)" ]
        + carried_headers
        + [ "Sequence_Count (number of member sequences in this group)",
            "Species_Count (number of distinct member species in this group)" ]
        + [ f"{species} (comma delimited member sequence identifiers of this sequence group whose species is {species})"
            for species in species_columns ]
    )

    with open( output_path, 'w' ) as output_file:
        output_file.write( '\t'.join( header ) + '\n' )
        for sequence_group_id in group_order:
            species___sequences = groups___species___sequences[ sequence_group_id ]
            sequence_count = sum( len( sequences ) for sequences in species___sequences.values() )
            species_count = len( species___sequences )
            cells = [ U.DELIM.join( sorted( species___sequences.get( species, [] ) ) ) for species in species_columns ]
            carried = group_ids___carried_cells.get( sequence_group_id, empty_carried )
            output = '\t'.join( [ sequence_group_id ] + carried + [ str( sequence_count ), str( species_count ) ] + cells ) + '\n'
            output_file.write( output )

    print( f"[003 {group_set_label}] wrote {len( group_order )} sequence groups x {len( species_columns )} species "
           f"sequence map -> {output_path.name}" )


if __name__ == '__main__':
    main()
