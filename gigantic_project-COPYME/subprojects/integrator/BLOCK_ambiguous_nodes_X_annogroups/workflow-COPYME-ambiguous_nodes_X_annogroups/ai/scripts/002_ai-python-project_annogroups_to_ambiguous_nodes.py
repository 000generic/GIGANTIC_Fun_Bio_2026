#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 27 | Purpose: Project the annogroups deconvolution onto only the ambiguous-node columns, in three structure scopes (one/some/all), per annotation source
# Human: Eric Edsinger

"""
Script 002 — Project annogroups onto ambiguous nodes (per source x scope).

The annogroups deconvolution all_structures table has one member-protein count
column per clade (the union of all clades across all species-tree structures),
plus the leading annogroup-identity columns. This script COLLAPSES that table to
ONLY the ambiguous-node columns (clades present in some but not all structures)
and writes three scoped views:

  2-output/<source>/all/  2_ai-<source>-ambiguous_nodes_X_annogroups-all_structures.tsv
       identity columns + every ambiguous node (union across all structures)
  2-output/<source>/one/  2_ai-<source>-ambiguous_nodes_X_annogroups-<structure_id>.tsv
       identity columns + the ambiguous nodes of one chosen structure
  2-output/<source>/some/ 2_ai-<source>-ambiguous_nodes_X_annogroups-some_structures.tsv
       identity columns + the ambiguous nodes across a chosen subset of structures

This is a PURE COLUMN PROJECTION of the deconvolution all_structures table — no
count is recomputed. A clade_id_name has the same species set, hence the same
per-annogroup count, in every structure it appears in (Rule 6), so the
all_structures table is the single value source for all three scopes; the
per-structure files (read in Script 001 / here only for their headers) decide
WHICH ambiguous columns the one/some scopes keep.

Fail-fast (§36): exits 1 if inputs are missing, a source has no ambiguous nodes,
or an enabled scope resolves to zero ambiguous columns.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_ambiguous_nodes as U


def scope_suffix( scope_name: str, one_structure_id: str ) -> str:
    """Filename suffix per scope: all -> all_structures, one -> <structure_id>, some -> some_structures."""
    if scope_name == "all":
        return "all_structures"
    if scope_name == "one":
        return one_structure_id
    return "some_structures"


def project_source( workflow_root: Path, config: dict, source: str, output_base: Path,
                    scope_flags: dict, some_structures: list ) -> None:
    """Stream the all_structures table once, writing each enabled scope's projection."""
    all_structures_path = U.source_all_structures_path( workflow_root, config, source )

    with open( all_structures_path, 'r' ) as input_all_structures:
        header_line = input_all_structures.readline().rstrip( '\n' )
        header_columns = header_line.split( '\t' )
        identity_indices, clades = U.parse_tree_counts_header( header_line )

        ambiguous_clades = [ clade for clade in clades if clade[ 'is_ambiguous' ] ]
        if not ambiguous_clades:
            print( f"CRITICAL ERROR: source '{source}' has ZERO ambiguous nodes to project", file = sys.stderr )
            print( f"  File: {all_structures_path}", file = sys.stderr )
            sys.exit( 1 )

        # Which ambiguous clade_id_names belong to the one / some scopes.
        one_clade_set = set()
        if scope_flags[ "one_enabled" ]:
            one_clade_set = U.read_structure_clade_set(
                U.source_per_structure_path( workflow_root, config, source, scope_flags[ "one_structure_id" ] ) )
        some_clade_set = set()
        if scope_flags[ "some_enabled" ]:
            for structure_id in some_structures:
                some_clade_set |= U.read_structure_clade_set(
                    U.source_per_structure_path( workflow_root, config, source, structure_id ) )

        # Build the per-scope selected column indices (identity columns first,
        # then the in-scope ambiguous clade columns in original column order).
        scope_clade_filters = {
            "all": lambda clade: True,
            "one": lambda clade: clade[ 'clade_id_name' ] in one_clade_set,
            "some": lambda clade: clade[ 'clade_id_name' ] in some_clade_set,
        }
        scope_enabled = {
            "all": scope_flags[ "all_enabled" ],
            "one": scope_flags[ "one_enabled" ],
            "some": scope_flags[ "some_enabled" ],
        }

        active_scopes = []  # ( scope_name, output_file, selected_indices )
        for scope_name in ( "all", "one", "some" ):
            if not scope_enabled[ scope_name ]:
                continue
            keep = scope_clade_filters[ scope_name ]
            clade_indices = [ clade[ 'index' ] for clade in ambiguous_clades if keep( clade ) ]
            if not clade_indices:
                print( f"CRITICAL ERROR: source '{source}' scope '{scope_name}' resolved to ZERO ambiguous columns", file = sys.stderr )
                print( "  Check the chosen structure(s) actually carry ambiguous nodes (Script 001 registry).", file = sys.stderr )
                sys.exit( 1 )
            selected_indices = identity_indices + clade_indices

            suffix = scope_suffix( scope_name, scope_flags[ "one_structure_id" ] )
            scope_dir = output_base / "2-output" / source / scope_name
            scope_dir.mkdir( parents = True, exist_ok = True )
            output_path = U.timestamped_output_path(
                scope_dir,
                f"2_ai-{source}-ambiguous_nodes_X_annogroups-{suffix}",
                output_base,
            )
            output_file = open( output_path, 'w' )
            output_file.write( '\t'.join( header_columns[ i ] for i in selected_indices ) + '\n' )
            active_scopes.append( ( scope_name, output_file, selected_indices, output_path, len( clade_indices ) ) )

        rows_written = 0
        for line in input_all_structures:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            for scope_name, output_file, selected_indices, _path, _ncols in active_scopes:
                output = '\t'.join( ( parts[ i ] if i < len( parts ) else '' ) for i in selected_indices )
                output_file.write( output + '\n' )
            rows_written += 1

    for scope_name, output_file, _selected_indices, output_path, clade_count in active_scopes:
        output_file.close()
        print( f"[002] {source} [{scope_name}]: {rows_written} annogroups x {clade_count} ambiguous nodes "
               f"-> {output_path.relative_to( output_base.parent )}" )


def main():
    parser = argparse.ArgumentParser( description = "Project annogroups onto ambiguous-node columns per source x scope" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )
    output_base = Path( args.output_dir )

    scopes = config.get( "structure_scopes", {} )
    one_scope = scopes.get( "one", {} ) or {}
    scope_flags = {
        "all_enabled": bool( ( scopes.get( "all", {} ) or {} ).get( "enabled", True ) ),
        "one_enabled": bool( one_scope.get( "enabled", False ) ),
        "one_structure_id": str( one_scope.get( "structure_id", "" ) ).strip(),
        "some_enabled": bool( ( scopes.get( "some", {} ) or {} ).get( "enabled", False ) ),
    }
    if scope_flags[ "one_enabled" ] and not scope_flags[ "one_structure_id" ]:
        print( "CRITICAL ERROR: structure_scopes.one is enabled but structure_id is empty", file = sys.stderr )
        sys.exit( 1 )

    sources = U.resolve_sources( workflow_root, config )
    some_structures = U.resolve_some_structures( workflow_root, config ) if scope_flags[ "some_enabled" ] else []

    if not any( ( scope_flags[ "all_enabled" ], scope_flags[ "one_enabled" ], scope_flags[ "some_enabled" ] ) ):
        print( "CRITICAL ERROR: no structure scope is enabled — enable at least one of all / one / some", file = sys.stderr )
        sys.exit( 1 )

    for source in sources:
        project_source( workflow_root, config, source, output_base, scope_flags, some_structures )


if __name__ == '__main__':
    main()
