# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Species-tree deconvolution of a sequence-group set — per group, member SEQUENCE and member SPECIES counts within every non-redundant species-tree clade
# Human: Eric Edsinger

"""
Script 002 — Species-tree deconvolution (one sequence-group set).

For every sequence group, adds one column per NON-REDUNDANT clade (node or tip)
across all 105 species-tree structures, holding the count of the group's members
within that clade. TWO parallel overlays are produced:
  - SEQUENCE counts  : member sequences (proteins) per clade
  - SPECIES counts   : DISTINCT member species per clade
A clade that covers all species (a tree root) equals the group's Sequence_Count
(sequence overlay) / Species_Count (species overlay) — checked, fail-fast.

Why one file per overlay covers all 105 structures (Rule 6): a clade_id_name names a
fixed species set, so a group's count at that clade is identical in every structure
it appears in. The 105 structures contribute a UNION of distinct clades; each unique
clade is one column, computed once. A companion per-structure file lays each
structure's own clades out root -> tips.

Input (the standard membership from Script 001):
  1-output/1_ai-<group_set_label>-sequence_group_membership.tsv
      SequenceGroup_ID  Sequence_Identifier  Genus_Species
plus the trees_species clade->species mapping (all structures).

Outputs (2-output/), for unit in { sequences, species }:
  2_ai-<label>-tree_counts-<unit>-all_structures.tsv          (union of all clades)
  tree_counts_per_structure/2_ai-<label>-tree_counts-<unit>-<structure>.tsv  (x105)

Fail-fast (§36): exits 1 on missing inputs, a Rule-6 clade species mismatch, a
membership species absent from the tree, or a full-coverage clade whose count !=
the group's Sequence_Count / Species_Count.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U


def load_clade_data( clade_map_path: Path ):
    """
    Clades from the trees_species clade->species map (all structures): the
    non-redundant union (single combined table) + each structure's clade set +
    parent/child topology (per-structure tables). Validates Rule 6 (a clade_id_name
    has the SAME species set in every structure).

    Returns:
        clades___species          { clade_id_name: frozenset( Genus_species ) }
        clades___descendant_count { clade_id_name: int }   (0 for tips)
        clades___structure_count  { clade_id_name: int }
        tip_species               set of Genus_species (the leaves)
        structures___parents_children { structure: { parent: [child,...] } }
        structures___clades       { structure: set(clade_id_name) }
        all_structures            sorted list of structure ids
    """
    clades___species = {}
    clades___descendant_count = {}
    clades___structures = defaultdict( set )
    tip_species = set()
    structures___parents_children = defaultdict( lambda: defaultdict( list ) )
    structures___clades = defaultdict( set )
    all_structures = set()

    with open( clade_map_path, 'r' ) as input_clade_map:
        header_ids___indices = U.build_header_index( input_clade_map.readline() )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_block = header_ids___indices[ "Phylogenetic_Block" ]
        index_descendant_count = header_ids___indices[ "Descendant_Species_Count" ]
        index_descendant_list = header_ids___indices[ "Descendant_Species_List" ]

        for line in input_clade_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ index_structure ]
            clade_id_name = parts[ index_clade ]
            descendant_count = int( parts[ index_descendant_count ] ) if parts[ index_descendant_count ] else 0
            descendant_list = parts[ index_descendant_list ] if index_descendant_list < len( parts ) else ''

            all_structures.add( structure_id )
            clades___structures[ clade_id_name ].add( structure_id )
            structures___clades[ structure_id ].add( clade_id_name )

            block = parts[ index_block ]
            if '::' in block:
                parent_clade = block.split( '::' )[ 0 ]
                structures___parents_children[ structure_id ][ parent_clade ].append( clade_id_name )

            if descendant_count > 0:
                species = frozenset( name.strip() for name in descendant_list.split( ',' ) if name.strip() )
            else:
                species_name = clade_id_name.split( '_', 1 )[ 1 ] if '_' in clade_id_name else clade_id_name
                species = frozenset( [ species_name ] )
                tip_species.add( species_name )

            if clade_id_name in clades___species:
                if clades___species[ clade_id_name ] != species:
                    print( f"CRITICAL ERROR: clade {clade_id_name} has DIFFERENT species sets across structures "
                           f"(Rule 6 violation) -- counts would be ill-defined", file = sys.stderr )
                    sys.exit( 1 )
            else:
                clades___species[ clade_id_name ] = species
                clades___descendant_count[ clade_id_name ] = descendant_count

    if not clades___species:
        print( f"CRITICAL ERROR: no clades found in {clade_map_path}", file = sys.stderr )
        sys.exit( 1 )

    clades___structure_count = { clade: len( structures ) for clade, structures in clades___structures.items() }
    return ( clades___species, clades___descendant_count, clades___structure_count, tip_species,
             structures___parents_children, structures___clades, sorted( all_structures ) )


def order_structure_clades_root_to_tips( parents_children, structure_clades, clades___descendant_count ):
    """Depth-first pre-order (root -> tips) for ONE structure; children largest-first."""
    clades___parents = {}
    for parent_clade, children in parents_children.items():
        for child_clade in children:
            clades___parents[ child_clade ] = parent_clade
    roots = [ clade for clade in structure_clades if clades___parents.get( clade ) not in structure_clades ]
    root = max( roots, key = lambda clade: clades___descendant_count.get( clade, 0 ) )

    ordered = []
    stack = [ root ]
    while stack:
        clade = stack.pop()
        ordered.append( clade )
        children = sorted( parents_children.get( clade, [] ),
                           key = lambda child: ( -clades___descendant_count.get( child, 0 ), child ) )
        for child in reversed( children ):
            stack.append( child )
    return ordered


def load_group_species_counts( membership_path: Path ):
    """
    From the standard membership: sequence_group_id -> { Genus_species: member_sequence_count },
    plus group order (first-seen) and the full set of membership species.
    """
    groups___species_counts = defaultdict( lambda: defaultdict( int ) )
    group_order = []
    seen_groups = set()
    all_membership_species = set()
    # SequenceGroup_ID (...)	Sequence_Identifier (...)	Genus_Species (...)
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_group = header_ids___indices[ "SequenceGroup_ID" ]
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
            groups___species_counts[ sequence_group_id ][ genus_species ] += 1
            all_membership_species.add( genus_species )
    return groups___species_counts, group_order, all_membership_species


def main():
    parser = argparse.ArgumentParser( description = "Species-tree deconvolution of a sequence-group set (sequence + species counts per clade)" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    group_set_label = config[ "group_set_label" ]
    # The union table already holds every clade's count (Rule 6 => stable across
    # structures), so the per-structure re-layout (2 x 105 files) is optional.
    emit_per_structure = bool( config.get( "emit_per_structure", False ) )

    # Optional per-group attributes carried (opaque) after SequenceGroup_ID; reserve the
    # engine's own identity/count columns so they are never duplicated.
    carried_headers, group_ids___carried_cells = U.load_group_attributes(
        workflow_root, config, { "SequenceGroup_ID", "Sequence_Count", "Species_Count" } )
    empty_carried = [ '' ] * len( carried_headers )

    output_base = Path( args.output_dir )
    membership_path = output_base / "1-output" / f"1_ai-{group_set_label}-sequence_group_membership.tsv"
    clade_map_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "clade_species_mappings" ] )
    for required in ( membership_path, clade_map_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required file not found: {required}", file = sys.stderr )
            sys.exit( 1 )

    # ---- clades -------------------------------------------------------------
    ( clades___species, clades___descendant_count, clades___structure_count, tip_species,
      structures___parents_children, structures___clades, all_structures ) = load_clade_data( clade_map_path )
    total_structures = len( all_structures )

    union_ordered_clades = sorted( clades___species.keys(),
                                   key = lambda clade: ( -clades___descendant_count[ clade ], clade ) )
    full_coverage_clades = [ clade for clade in union_ordered_clades if clades___species[ clade ] == frozenset( tip_species ) ]
    structures___ordered_clades = {
        structure: order_structure_clades_root_to_tips(
            structures___parents_children[ structure ], structures___clades[ structure ], clades___descendant_count )
        for structure in all_structures
    }
    print( f"[002 {group_set_label}] {len( union_ordered_clades )} non-redundant clades across {total_structures} structures "
           f"({len( tip_species )} tips); {len( full_coverage_clades )} full-coverage root clade(s)" )

    species___ancestor_clades = defaultdict( list )
    for clade_id_name, species in clades___species.items():
        for species_name in species:
            species___ancestor_clades[ species_name ].append( clade_id_name )

    # ---- per-group per-species member counts --------------------------------
    groups___species_counts, group_order, all_membership_species = load_group_species_counts( membership_path )
    print( f"[002 {group_set_label}] read {len( group_order )} sequence groups from membership" )

    species_not_in_tree = sorted( all_membership_species - tip_species )
    if species_not_in_tree:
        print( f"CRITICAL ERROR: {len( species_not_in_tree )} membership species are not tree tips "
               f"(members would be silently uncounted): {species_not_in_tree[ :5 ]}", file = sys.stderr )
        sys.exit( 1 )

    # ---- self-documenting clade header (per unit) ---------------------------
    def clade_header( clade, unit ):
        present = f"present in {clades___structure_count[ clade ]} of {total_structures} structures"
        if clades___descendant_count[ clade ] == 0:
            species_name = next( iter( clades___species[ clade ] ) )
            return f"{clade} (member-{unit} count of this sequence group within tip {clade} = species {species_name}; {present})"
        return ( f"{clade} (member-{unit} count of this sequence group within clade {clade}; "
                 f"{clades___descendant_count[ clade ]} descendant species; {present})" )

    fixed_header = (
        [ "SequenceGroup_ID (identifier of the sequence group from the producer)" ]
        + carried_headers
        + [ "Sequence_Count (number of member sequences in this group)",
            "Species_Count (number of distinct member species in this group)" ]
    )

    # ---- open the union + per-structure files for BOTH units ----------------
    units = ( "sequences", "species" )
    output_dir = output_base / "2-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    per_structure_dir = output_dir / "tree_counts_per_structure"
    per_structure_dir.mkdir( parents = True, exist_ok = True )

    union_files = {}
    structures___files = { unit: {} for unit in units }
    for unit in units:
        union_path = output_dir / f"2_ai-{group_set_label}-tree_counts-{unit}-all_structures.tsv"
        union_file = open( union_path, 'w' )
        union_file.write( '\t'.join( fixed_header + [ clade_header( clade, unit ) for clade in union_ordered_clades ] ) + '\n' )
        union_files[ unit ] = union_file
        if emit_per_structure:
            for structure in all_structures:
                per_structure_path = per_structure_dir / f"2_ai-{group_set_label}-tree_counts-{unit}-{structure}.tsv"
                output_file = open( per_structure_path, 'w' )
                output_file.write( '\t'.join( fixed_header + [ clade_header( clade, unit ) for clade in structures___ordered_clades[ structure ] ] ) + '\n' )
                structures___files[ unit ][ structure ] = output_file

    # ---- per-group: compute per-clade sequence + species counts -------------
    rows_written = 0
    for sequence_group_id in group_order:
        species___counts = groups___species_counts[ sequence_group_id ]
        sequence_count = sum( species___counts.values() )
        species_count = len( species___counts )

        clades___sequence_counts = defaultdict( int )
        clades___species_counts = defaultdict( int )
        for species_name, count in species___counts.items():
            for clade_id_name in species___ancestor_clades[ species_name ]:
                clades___sequence_counts[ clade_id_name ] += count       # proteins
                clades___species_counts[ clade_id_name ] += 1            # distinct species (one per member species)

        # research-integrity: every full-coverage (root) clade must total the group's counts
        for clade in full_coverage_clades:
            if clades___sequence_counts.get( clade, 0 ) != sequence_count:
                print( f"CRITICAL ERROR: group {sequence_group_id} sequence count at full-coverage clade {clade} "
                       f"({clades___sequence_counts.get( clade, 0 )}) != Sequence_Count {sequence_count}", file = sys.stderr )
                sys.exit( 1 )
            if clades___species_counts.get( clade, 0 ) != species_count:
                print( f"CRITICAL ERROR: group {sequence_group_id} species count at full-coverage clade {clade} "
                       f"({clades___species_counts.get( clade, 0 )}) != Species_Count {species_count}", file = sys.stderr )
                sys.exit( 1 )

        carried = group_ids___carried_cells.get( sequence_group_id, empty_carried )
        prefix = [ sequence_group_id ] + carried + [ str( sequence_count ), str( species_count ) ]
        clades___counts_by_unit = { "sequences": clades___sequence_counts, "species": clades___species_counts }
        for unit in units:
            clades___counts = clades___counts_by_unit[ unit ]
            union_files[ unit ].write( '\t'.join( prefix + [ str( clades___counts.get( clade, 0 ) ) for clade in union_ordered_clades ] ) + '\n' )
            if emit_per_structure:
                for structure in all_structures:
                    structures___files[ unit ][ structure ].write(
                        '\t'.join( prefix + [ str( clades___counts.get( clade, 0 ) ) for clade in structures___ordered_clades[ structure ] ] ) + '\n' )
        rows_written += 1

    for unit in units:
        union_files[ unit ].close()
        for output_file in structures___files[ unit ].values():
            output_file.close()

    per_structure_note = f"+ {len( units ) * total_structures} per-structure files" if emit_per_structure else "(per-structure layout disabled)"
    print( f"[002 {group_set_label}] wrote {rows_written} group rows x {len( union_ordered_clades )} clades for "
           f"{len( units )} units (sequences, species): 2 union tables {per_structure_note}" )


if __name__ == '__main__':
    main()
