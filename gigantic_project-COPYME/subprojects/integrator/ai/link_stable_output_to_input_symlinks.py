# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Stable-name symlinks from timestamped OUTPUT_pipeline files to output_to_input (§65)
# Human: Eric Edsinger

"""
Create output_to_input symlinks with STABLE basenames pointing at timestamped (or
legacy stable) files under OUTPUT_pipeline.

Preserves relative subdirectory layout under OUTPUT_pipeline when --preserve-subdirs
is set (e.g. species70_X_orthogroups/4-output/composite_clades_detail_tables/).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator_shared as U


def link_file( source_file: Path, shared_dir: Path, output_pipeline: Path, workflow_relative: str, preserve_subdirs: bool, strip_stage_prefix: bool ):
    if preserve_subdirs:
        rel = source_file.relative_to( output_pipeline )
        if strip_stage_prefix and rel.parts and rel.parts[ 0 ].endswith( '-output' ) and rel.parts[ 0 ][ 0 ].isdigit():
            rel = Path( *rel.parts[ 1: ] ) if len( rel.parts ) > 1 else Path( '.' )
        stable_name = U.stable_symlink_basename( rel.name )
        dest = shared_dir / rel.parent / stable_name
    else:
        stable_name = U.stable_symlink_basename( source_file.name )
        dest = shared_dir / stable_name
    dest.parent.mkdir( parents = True, exist_ok = True )
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    rel_from_pipeline = source_file.relative_to( output_pipeline )
    target = Path( workflow_relative ) / rel_from_pipeline
    dest.symlink_to( target.as_posix() )
    return dest


def main():
    parser = argparse.ArgumentParser( description = "Link timestamped outputs to stable output_to_input symlinks" )
    parser.add_argument( '--output-pipeline', required = True )
    parser.add_argument( '--shared-dir', required = True )
    parser.add_argument( '--workflow-relative', required = True,
                           help = "Relative path from shared-dir entry to this run's OUTPUT_pipeline root" )
    parser.add_argument( '--strip-stage-prefix', action = 'store_true',
                           help = "Drop N-output/ from mirrored paths (species, ambiguous_nodes layouts)" )
    parser.add_argument( '--preserve-subdirs', action = 'store_true',
                           help = "Mirror OUTPUT_pipeline subdirectory layout under shared-dir" )
    parser.add_argument( '--glob', action = 'append', default = [],
                           help = "Glob under OUTPUT_pipeline (repeatable), default **/*.tsv and **/*.txt" )
    args = parser.parse_args()

    output_pipeline = Path( args.output_pipeline ).resolve()
    shared_dir = Path( args.shared_dir ).resolve()
    shared_dir.mkdir( parents = True, exist_ok = True )

    globs = args.glob if args.glob else [ '**/*.tsv', '**/*.txt' ]
    linked = 0
    for pattern in globs:
        for source_file in sorted( output_pipeline.glob( pattern ) ):
            if not source_file.is_file():
                continue
            if source_file.name.startswith( '.' ):
                continue
            link_file( source_file, shared_dir, output_pipeline, args.workflow_relative, args.preserve_subdirs, args.strip_stage_prefix )
            linked += 1

    print( f"[link_stable_output_to_input] {linked} symlinks -> {shared_dir}" )


if __name__ == '__main__':
    main()
