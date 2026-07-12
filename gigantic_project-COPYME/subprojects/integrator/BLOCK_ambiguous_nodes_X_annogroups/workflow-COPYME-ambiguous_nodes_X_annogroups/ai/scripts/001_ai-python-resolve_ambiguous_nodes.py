#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Resolve the ambiguous nodes (clades present in some but not all structures) and the one/some/all structure scopes, per annotation source
# Human: Eric Edsinger

"""
Script 001 — Resolve ambiguous nodes + structure scopes (per source).

The annogroups species-tree deconvolution writes, per annogroup, one member-protein
count column per clade, with a self-documenting header that ends
'... present in N of M structures'. A clade is an AMBIGUOUS NODE iff N < M: it
exists in some but not all species-tree structures — i.e. it is one of the
unresolved basal-metazoan groupings whose membership depends on the branching
order. Fixed backbone clades have N == M.

For each annotation source this script reads the deconvolution headers (no data
rows) and writes two small tables:

  1-output/<source>/1_ai-<source>-ambiguous_node_registry.tsv
      one row per ambiguous node: its clade_id_name, descendant-species count,
      how many structures it appears in, and membership flags for the chosen
      one / some / all scopes.

  1-output/<source>/1_ai-<source>-structure_sets.tsv
      one row per scope (all / one / some): whether it is enabled, the structures
      it covers, and how many ambiguous nodes fall in it.

Scopes (per the ambiguous_nodes series design):
  - all  : every ambiguous node across all M structures
  - one  : the ambiguous nodes of one user-chosen structure
  - some : the ambiguous nodes across a user-chosen subset of structures

ONE / SOME membership is read from the per-structure deconvolution files (each
contains only that structure's own clades as columns). Structure-independent
counts (Rule 6) mean nothing is recomputed here — this only resolves WHICH nodes.

Fail-fast (§36): exits 1 if inputs are missing, a source has no ambiguous nodes,
or a requested structure file is absent.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_ambiguous_nodes as U


def resolve_scopes( config: dict ) -> dict:
    """Read the three scope blocks from config, with their enabled flags."""
    scopes = config.get( "structure_scopes", {} )
    all_scope = scopes.get( "all", {} ) or {}
    one_scope = scopes.get( "one", {} ) or {}
    some_scope = scopes.get( "some", {} ) or {}
    return {
        "all_enabled": bool( all_scope.get( "enabled", True ) ),
        "one_enabled": bool( one_scope.get( "enabled", False ) ),
        "one_structure_id": str( one_scope.get( "structure_id", "" ) ).strip(),
        "some_enabled": bool( some_scope.get( "enabled", False ) ),
    }


def write_registry( output_dir: Path, output_base: Path, source: str, ambiguous_clades: list,
                    total_structures: int, one_clade_set: set, some_clade_set: set,
                    scope_flags: dict ) -> Path:
    """One row per ambiguous node with its scope-membership flags."""
    registry_path = U.timestamped_output_path( output_dir, f"1_ai-{source}-ambiguous_node_registry", output_base )
    header_columns = [
        "Clade_ID_Name (atomic clade identifier of an ambiguous node e.g. C096_Planulozoa)",
        "Descendant_Species_Count (count of species descending from this clade; stable across structures per Rule 6)",
        "Appears_In_Structures_Count (number of species-tree structures in which this clade exists)",
        "Total_Structures (total number of species-tree structures in the deconvolution)",
        "In_All_Scope (yes when this ambiguous node is included in the all scope; always yes by definition)",
        "In_One_Scope (yes when this ambiguous node exists in the chosen one-scope structure)",
        "In_Some_Scope (yes when this ambiguous node exists in at least one chosen some-scope structure)",
    ]
    output_lines = [ '\t'.join( header_columns ) ]
    for clade in ambiguous_clades:
        clade_id_name = clade[ 'clade_id_name' ]
        in_one = "yes" if ( scope_flags[ "one_enabled" ] and clade_id_name in one_clade_set ) else "no"
        in_some = "yes" if ( scope_flags[ "some_enabled" ] and clade_id_name in some_clade_set ) else "no"
        output = '\t'.join( [
            clade_id_name,
            str( clade[ 'descendant_species_count' ] ),
            str( clade[ 'present_count' ] ),
            str( total_structures ),
            "yes",
            in_one,
            in_some,
        ] )
        output_lines.append( output )
    with open( registry_path, 'w' ) as output_registry:
        output_registry.write( '\n'.join( output_lines ) + '\n' )
    return registry_path


def write_structure_sets( output_dir: Path, output_base: Path, source: str, total_structures: int,
                          ambiguous_clades: list, one_clade_set: set, some_clade_set: set,
                          some_structures: list, scope_flags: dict ) -> Path:
    """One row per scope (all / one / some): coverage + ambiguous-node count."""
    structure_sets_path = U.timestamped_output_path( output_dir, f"1_ai-{source}-structure_sets", output_base )
    header_columns = [
        "Scope (the structure scope: all, one, or some)",
        "Enabled (yes when this scope is produced)",
        "Structure_Count (number of species-tree structures covered by this scope)",
        "Structure_IDs (comma delimited structures in this scope; ALL means every structure)",
        "Ambiguous_Node_Count (count of ambiguous nodes projected for this scope)",
    ]
    ambiguous_count = len( ambiguous_clades )
    one_count = sum( 1 for clade in ambiguous_clades if clade[ 'clade_id_name' ] in one_clade_set )
    some_count = sum( 1 for clade in ambiguous_clades if clade[ 'clade_id_name' ] in some_clade_set )

    rows = [
        ( "all", scope_flags[ "all_enabled" ], total_structures, "ALL", ambiguous_count ),
        ( "one", scope_flags[ "one_enabled" ], ( 1 if scope_flags[ "one_structure_id" ] else 0 ),
          scope_flags[ "one_structure_id" ] or "", one_count ),
        ( "some", scope_flags[ "some_enabled" ], len( some_structures ),
          U.DELIM.join( some_structures ), some_count ),
    ]
    output_lines = [ '\t'.join( header_columns ) ]
    for scope_name, enabled, structure_count, structure_ids_cell, node_count in rows:
        output = '\t'.join( [
            scope_name,
            "yes" if enabled else "no",
            str( structure_count ),
            structure_ids_cell,
            str( node_count ),
        ] )
        output_lines.append( output )
    with open( structure_sets_path, 'w' ) as output_structure_sets:
        output_structure_sets.write( '\n'.join( output_lines ) + '\n' )
    return structure_sets_path


def main():
    parser = argparse.ArgumentParser( description = "Resolve ambiguous nodes + structure scopes per annotation source" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    scope_flags = resolve_scopes( config )

    sources = U.resolve_sources( workflow_root, config )
    print( f"[001] sources: {', '.join( sources )}" )

    # SOME structure set is source-independent (it is a set of structure ids).
    some_structures = U.resolve_some_structures( workflow_root, config ) if scope_flags[ "some_enabled" ] else []
    if scope_flags[ "some_enabled" ]:
        print( f"[001] some scope: {len( some_structures )} structures -> {U.DELIM.join( some_structures )}" )

    for source in sources:
        all_structures_path = U.source_all_structures_path( workflow_root, config, source )
        with open( all_structures_path, 'r' ) as input_all_structures:
            _identity_indices, clades = U.parse_tree_counts_header( input_all_structures.readline() )

        ambiguous_clades = [ clade for clade in clades if clade[ 'is_ambiguous' ] ]
        if not ambiguous_clades:
            print( f"CRITICAL ERROR: source '{source}' has ZERO ambiguous nodes "
                   f"(every clade present in all structures)", file = sys.stderr )
            print( f"  File: {all_structures_path}", file = sys.stderr )
            print( "  An unresolved input species tree should yield ambiguous nodes; verify the deconvolution.", file = sys.stderr )
            sys.exit( 1 )
        total_structures = clades[ 0 ][ 'total_count' ]

        # ONE / SOME clade membership from the per-structure files (header only).
        one_clade_set = set()
        if scope_flags[ "one_enabled" ]:
            if not scope_flags[ "one_structure_id" ]:
                print( "CRITICAL ERROR: structure_scopes.one is enabled but structure_id is empty", file = sys.stderr )
                sys.exit( 1 )
            one_clade_set = U.read_structure_clade_set(
                U.source_per_structure_path( workflow_root, config, source, scope_flags[ "one_structure_id" ] ) )

        some_clade_set = set()
        if scope_flags[ "some_enabled" ]:
            for structure_id in some_structures:
                some_clade_set |= U.read_structure_clade_set(
                    U.source_per_structure_path( workflow_root, config, source, structure_id ) )

        output_dir = Path( args.output_dir ) / "1-output" / source
        output_dir.mkdir( parents = True, exist_ok = True )
        output_base = Path( args.output_dir )
        registry_path = write_registry( output_dir, output_base, source, ambiguous_clades, total_structures,
                                        one_clade_set, some_clade_set, scope_flags )
        structure_sets_path = write_structure_sets( output_dir, output_base, source, total_structures, ambiguous_clades,
                                                    one_clade_set, some_clade_set, some_structures, scope_flags )

        one_count = sum( 1 for clade in ambiguous_clades if clade[ 'clade_id_name' ] in one_clade_set )
        some_count = sum( 1 for clade in ambiguous_clades if clade[ 'clade_id_name' ] in some_clade_set )
        print( f"[001] {source}: {len( ambiguous_clades )} ambiguous nodes of {len( clades )} clades "
               f"({total_structures} structures); one={one_count} some={some_count} "
               f"-> {registry_path.name}, {structure_sets_path.name}" )


if __name__ == '__main__':
    main()
