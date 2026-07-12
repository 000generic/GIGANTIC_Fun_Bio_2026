# AI: Claude | Opus 4.8 | 2026 July 08 | Purpose: Generate an all-clades composite_clades manifest — absent per named clade + core_urclade per internal clade (ingroups = its direct children), plus the preserved curated metazoan exact block + the Early_Metazoa ambiguous-zone early clade
# Human: Eric Edsinger

"""
Script 000 — Generate the all-clades composite_clades manifest.

This is a ONE-TIME (re-runnable) generator for INPUT_user/composite_clades_manifest.tsv.
It expands the composite-clade analysis to EVERY clade of the reference species-tree
structure, while preserving the curated, hand-authored metazoan entries.

What it emits (four algorithms; see the manifest header + Script 004 for definitions):

  - exact            : PRESERVED verbatim from the curated seed below (the metazoan
                       building-block partition). 'exact' is defined over the config
                       `composite_clades.groups` partition, so it stays metazoan.
  - absent           : ONE row per NAMED clade of the reference structure (a clade is
                       named by its clade_id_name, e.g. C082_Metazoa). Meaning: the
                       sequence group has ZERO member species in that clade. The root
                       (which covers all species) is skipped — "absent from everything"
                       matches nothing. The special 'absent from NonMetazoa' (the scope
                       outside label, not a clade) is preserved from the curated seed.
  - core_urclade     : ONE row per INTERNAL clade (a clade that has children). Target =
                       that clade; ingroups = its DIRECT children (from the structure's
                       parent-child table). Meaning: members in an OUTGROUP of the clade
                       AND in an ingroup -> the clade's Ur (last-common-ancestor core).
                       The root is skipped (it has no outgroup, so Ur is vacuous).
  - core_early_clade : PRESERVED from the curated seed — the single Early_Metazoa entry,
                       the species70 unresolved (ambiguous) base of Metazoa. 'Early'
                       clades are for user-defined ambiguous zones, so they are curated,
                       not auto-generated for every clade.

Ur/absent rows reference clades by clade_id_name (resolve_clade_species falls through
to the trees_species clade->species mapping at the reference structure). The curated
seed's exact rows reference the config building-block GROUP names (Ctenophora, ...),
which is required for the exact algorithm.

Usage (from the workflow directory, or via defaults):
  python3 ai/scripts/000_ai-python-generate_composite_clades_manifest-all_clades.py \
      [--parent_child_relationships <path>] [--output <path>]

Fail-fast (§36): exits 1 if the parent-child table is missing/empty or a root cannot
be identified.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path


# ============================================================================
# Curated seed — hand-authored metazoan entries preserved across regenerations.
# exact  : the metazoan building-block partition (uses config GROUP names, required
#          by the exact algorithm; do NOT convert these to clade_id_names).
# absent : only the special 'NonMetazoa' outside-label row (not a clade; cannot be
#          auto-generated from the clade table). Per-clade absent is generated below.
# core_early_clade : the single Early_Metazoa ambiguous-zone entry.
# ============================================================================
CURATED_SEED = """\
# ---- exact: PRESERVED curated metazoan building-block partition ----
# (exact is defined over composite_clades.groups; these use GROUP names, not clade_id_names)
exact\t\t\tCtenophora
exact\t\t\tPorifera
exact\t\t\tPlacozoa
exact\t\t\tCnidaria
exact\t\t\tBilateria
exact\t\t\tPorifera,Bilateria
exact\t\t\tCtenophora,Porifera
exact\t\t\tCtenophora,Placozoa
exact\t\t\tCtenophora,Cnidaria
exact\t\t\tCtenophora,Bilateria
exact\t\t\tCtenophora,Porifera,Placozoa
exact\t\t\tCtenophora,Porifera,Placozoa,Cnidaria
exact\t\t\tPorifera,Placozoa
exact\t\t\tPorifera,Placozoa,Cnidaria
exact\t\t\tPlacozoa,Cnidaria
exact\t\t\tPlacozoa,Bilateria
exact\t\t\tCnidaria,Bilateria
exact\t\t\tCtenophora,NonMetazoa
exact\t\t\tPorifera,NonMetazoa
exact\t\t\tPlacozoa,NonMetazoa
exact\t\t\tCnidaria,NonMetazoa
exact\t\t\tCtenophora,Porifera,NonMetazoa
exact\t\t\tCtenophora,Placozoa,NonMetazoa
exact\t\t\tCtenophora,Cnidaria,NonMetazoa
exact\t\t\tCtenophora,Bilateria,NonMetazoa
exact\t\t\tCtenophora,Porifera,Placozoa,NonMetazoa
exact\t\t\tCtenophora,Porifera,Placozoa,Cnidaria,NonMetazoa
exact\t\t\tPorifera,Placozoa,NonMetazoa
exact\t\t\tPorifera,Placozoa,Cnidaria,NonMetazoa
exact\t\t\tPlacozoa,Cnidaria,NonMetazoa
exact\t\t\tPlacozoa,Bilateria,NonMetazoa
exact\t\t\tCnidaria,Bilateria,NonMetazoa

# ---- absent: special outside-label row (NonMetazoa is the scope outside label, not a clade) ----
absent\t\t\tNonMetazoa

# ---- core_early_clade: the species70 unresolved (ambiguous) base of Metazoa ----
core_early_clade\tEarly_Metazoa\tMetazoa\tCtenophora,Porifera,Placozoa,Cnidaria,Bilateria
"""


# The manifest column header (matches Script 004 / utils_sequence_groups loader).
MANIFEST_HEADER = "Algorithm\tName\tTarget_Clade\tClades"

# Default paths, relative to the workflow directory (this script lives in ai/scripts/).
DEFAULT_PARENT_CHILD = (
    "../../../trees_species/output_to_input/BLOCK_permutations_and_features/"
    "Species_Parent_Child_Relationships/5_ai-structure_001_parent_child_relationships.tsv"
)
DEFAULT_OUTPUT = "INPUT_user/composite_clades_manifest.tsv"


def load_parent_child( parent_child_path: Path ):
    """
    Read the reference structure's parent-child table:
        Phylogenetic_Block (Parent::Child)  Parent_Clade_ID_Name  Child_Clade_ID_Name

    Returns:
        parents___children  { parent_clade_id_name: [ child_clade_id_name, ... ] } (input order)
        all_clades          set of every clade_id_name that appears (parent or child)
        root                the clade that is a parent but never a child
    Fail-fast: exits 1 if the file is missing/empty or no unique root is found.
    """
    if not parent_child_path.is_file():
        print( f"CRITICAL ERROR: parent-child relationships file not found: {parent_child_path}", file = sys.stderr )
        sys.exit( 1 )

    parents___children = defaultdict( list )
    all_clades = set()
    children_seen = set()
    parents_seen = set()

    # Phylogenetic_Block (...)	Parent_Clade_ID_Name (...)	Child_Clade_ID_Name (...)
    # C000_OOL::C071_Basal	C000_OOL	C071_Basal
    with open( parent_child_path, 'r' ) as input_parent_child:
        header_line = input_parent_child.readline()
        header_ids___indices = {}
        for index, column in enumerate( header_line.rstrip( '\n' ).split( '\t' ) ):
            header_ids___indices[ column.split( ' (' )[ 0 ].strip() ] = index
        index_parent = header_ids___indices[ "Parent_Clade_ID_Name" ]
        index_child = header_ids___indices[ "Child_Clade_ID_Name" ]

        for line in input_parent_child:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            parent = parts[ index_parent ].strip()
            child = parts[ index_child ].strip()
            if not parent or not child:
                continue
            parents___children[ parent ].append( child )
            all_clades.add( parent )
            all_clades.add( child )
            parents_seen.add( parent )
            children_seen.add( child )

    if not parents___children:
        print( f"CRITICAL ERROR: no parent-child edges parsed from {parent_child_path}", file = sys.stderr )
        sys.exit( 1 )

    roots = sorted( parents_seen - children_seen )
    if len( roots ) != 1:
        print( f"CRITICAL ERROR: expected exactly one root (a parent that is never a child); found {roots}", file = sys.stderr )
        sys.exit( 1 )
    root = roots[ 0 ]

    return parents___children, all_clades, root


def main():
    parser = argparse.ArgumentParser( description = "Generate the all-clades composite_clades manifest" )
    parser.add_argument( '--parent_child_relationships', default = DEFAULT_PARENT_CHILD,
                         help = "reference-structure parent-child table (default: structure_001)" )
    parser.add_argument( '--output', default = DEFAULT_OUTPUT,
                         help = "manifest output path (default: INPUT_user/composite_clades_manifest.tsv)" )
    args = parser.parse_args()

    parent_child_path = Path( args.parent_child_relationships )
    output_path = Path( args.output )

    parents___children, all_clades, root = load_parent_child( parent_child_path )

    # absent: every named clade EXCEPT the root (absent from all species matches nothing).
    absent_clades = sorted( clade for clade in all_clades if clade != root )
    # core_urclade: every INTERNAL clade (has children) EXCEPT the root (no outgroup).
    internal_clades = sorted( parent for parent in parents___children if parent != root )

    lines = []
    lines.append( "# GIGANTIC composite_clades manifest — ALL CLADES (auto-generated)" )
    lines.append( "# ============================================================================" )
    lines.append( "# Generated by 000_ai-python-generate_composite_clades_manifest-all_clades.py" )
    lines.append( f"# Reference parent-child table: {parent_child_path}" )
    lines.append( f"# Root (skipped for absent/urclade): {root}" )
    lines.append( f"# absent rows: {len( absent_clades )} (one per named clade)   "
                  f"core_urclade rows: {len( internal_clades )} (one per internal clade)" )
    lines.append( "#" )
    lines.append( "# Columns (tab-separated): Algorithm  Name  Target_Clade  Clades" )
    lines.append( "#   Algorithm    : exact | absent | core_urclade | core_early_clade" )
    lines.append( "#   Name         : blank for exact/absent (auto-named); required for the core_* algorithms" )
    lines.append( "#   Target_Clade : the focal clade for core_urclade / core_early_clade; blank otherwise" )
    lines.append( "#   Clades       : components (exact), absent-from clades (absent), or ingroups (core_*)" )
    lines.append( "# absent/urclade reference clades by clade_id_name; exact uses config GROUP names." )
    lines.append( "# ============================================================================" )
    lines.append( MANIFEST_HEADER )
    lines.append( "" )

    # ---- curated seed (exact + NonMetazoa absent + Early_Metazoa) ----
    lines.append( CURATED_SEED.rstrip( '\n' ) )
    lines.append( "" )

    # ---- generated: absent per named clade ----
    lines.append( "# ---- absent: one per named clade (members have ZERO species in the clade) ----" )
    for clade in absent_clades:
        lines.append( f"absent\t\t\t{clade}" )
    lines.append( "" )

    # ---- generated: core_urclade per internal clade ----
    lines.append( "# ---- core_urclade: one per internal clade (target = clade; ingroups = its direct children) ----" )
    for clade in internal_clades:
        children = parents___children[ clade ]
        clades_column = ','.join( children )
        lines.append( f"core_urclade\t{clade}\t{clade}\t{clades_column}" )
    lines.append( "" )

    output = '\n'.join( lines ) + '\n'
    output_path.parent.mkdir( parents = True, exist_ok = True )
    with open( output_path, 'w' ) as output_manifest:
        output_manifest.write( output )

    exact_count = CURATED_SEED.count( "\nexact\t" ) + ( 1 if CURATED_SEED.startswith( "exact\t" ) else 0 )
    print( f"[000] wrote composite_clades manifest -> {output_path}" )
    print( f"[000]   exact (curated, preserved) : {exact_count}" )
    print( f"[000]   absent (NonMetazoa + per-clade) : {1 + len( absent_clades )}" )
    print( f"[000]   core_urclade (per internal clade) : {len( internal_clades )}" )
    print( f"[000]   core_early_clade (Early_Metazoa) : 1" )
    print( f"[000]   root skipped for absent/urclade : {root}" )


if __name__ == '__main__':
    main()
