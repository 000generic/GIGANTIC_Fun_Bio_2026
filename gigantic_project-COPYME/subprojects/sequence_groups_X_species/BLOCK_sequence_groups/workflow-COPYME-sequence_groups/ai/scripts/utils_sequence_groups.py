# AI: Claude (Cursor) | Opus 4.8 | 2026 July 11 | Purpose: Shared helpers for sequence_groups_X_species — composite clades + clade resolution
# Human: Eric Edsinger

"""
Shared helpers for the sequence_groups_X_species subproject.

Join keys and delimiters: integrator/ai/utils_integrator_shared.py
(see integrator/ai/integrator_join_and_delimiter_contract.md).

This subproject RESOLVES any "sequence group" onto the species-tree clades via the
standard membership interchange:

    SequenceGroup_ID  Sequence_Identifier  Genus_Species
"""

import sys
from pathlib import Path

_INTEGRATOR_AI = Path( __file__ ).resolve().parents[ 5 ] / "integrator" / "ai"
if str( _INTEGRATOR_AI ) not in sys.path:
    sys.path.insert( 0, str( _INTEGRATOR_AI ) )

import utils_integrator_shared as _SHARED

DELIM = _SHARED.DELIM
SUBDELIM = _SHARED.SUBDELIM
NAME_DELIM = _SHARED.NAME_DELIM
NA = _SHARED.NA
GENE_GROUP_NAME_FALLBACKS = _SHARED.GENE_GROUP_NAME_FALLBACKS
DEFAULT_GENE_GROUPS_HGNC_METADATA = _SHARED.DEFAULT_GENE_GROUPS_HGNC_METADATA

load_config = _SHARED.load_config
workflow_root_from_output_dir = _SHARED.workflow_root_from_output_dir
resolve_input_path = _SHARED.resolve_input_path
genus_species_from_phyloname = _SHARED.genus_species_from_phyloname
parse_full_gigantic_id = _SHARED.parse_full_gigantic_id
genus_species_from_full_gigantic_id = _SHARED.genus_species_from_full_gigantic_id
build_header_index = _SHARED.build_header_index
guard_name = _SHARED.guard_name
annogroup_name_from_map_fields = _SHARED.annogroup_name_from_map_fields
load_gene_group_metadata = _SHARED.load_gene_group_metadata
resolve_gene_group_id_name = _SHARED.resolve_gene_group_id_name
sanitized_name_from_ags_path = _SHARED.sanitized_name_from_ags_path
find_output_pipeline_root = _SHARED.find_output_pipeline_root
resolve_workflow_run_timestamp_suffix = _SHARED.resolve_workflow_run_timestamp_suffix
build_timestamped_filename = _SHARED.build_timestamped_filename
stable_symlink_basename = _SHARED.stable_symlink_basename


def timestamped_output_path( output_dir: Path, stem: str, output_base: Path, extension: str = '.tsv' ) -> Path:
    """Build a timestamped output path under output_dir using the shared run suffix (§65)."""
    pipeline_root = find_output_pipeline_root( output_base )
    suffix = resolve_workflow_run_timestamp_suffix( pipeline_root )
    return output_dir / build_timestamped_filename( stem, suffix, extension )


def membership_output_path( output_base: Path, group_set_label: str ) -> Path:
    """Standard Script 001 membership table path (timestamped archival filename)."""
    return timestamped_output_path(
        output_base / "1-output",
        f"1_ai-{group_set_label}-sequence_group_membership",
        output_base,
    )


def genus_species_from_full_id( full_id: str ) -> str:
    """Backward-compatible alias used by Script 001 (empty string when unparsable)."""
    parsed = genus_species_from_full_gigantic_id( full_id )
    return parsed if parsed is not None else ''


def annotation_type_header_columns( prefix: str, label: str, names_blank: bool = False ) -> list:
    """Four self-documenting headers per annotation type (integrator catalog pattern)."""
    if names_blank:
        names_desc = (
            f"{prefix}_Names (intentionally blank; {label} has no separate human-readable name)"
        )
    else:
        names_desc = (
            f"{prefix}_Names (' // ' delimited {label} names aligned to {prefix}_Identifiers)"
        )
    return [
        f"{prefix}_Species_Count (non-redundant count of member species with >=1 {label} on this sequence group)",
        f"{prefix}_Sequence_Count (non-redundant count of member sequences with >=1 {label} on this sequence group)",
        f"{prefix}_Identifiers (comma delimited non-redundant {label} identifiers aggregated over member sequences)",
        names_desc,
    ]


# Integrator catalog annotation types (Script 006 index + Script 004 detail columns).
# Tuple: ( prefix, human label for headers, names_blank )
ANNOTATION_TYPE_SPECS = [
    ( "Pfam", "Pfam domain", False ),
    ( "GO", "GO term", False ),
    ( "PANTHER", "PANTHER family", False ),
    ( "Annogroups_Pfam", "pfam annogroup", False ),
    ( "Annogroups_GO", "go annogroup", False ),
    ( "Annogroups_PANTHER", "panther annogroup", False ),
    ( "Gene_Families", "gene family", False ),
    ( "Gene_Groups", "gene group", False ),
    ( "Dark_Proteome", "dark proteome status", False ),
    ( "Hotspots", "hotspot", True ),
]


# ============================================================================
# Composite Clades (configurable species-tree clade groupings, 2026-06-27)
# ============================================================================
# A "composite clade" is a user-defined named group of one or more species-tree
# clades, used to ask a focused question about where a feature unit's member
# species fall on the species tree. The building-block GROUPS are defined in
# START_HERE-user_config.yaml under `composite_clades` (default: the five metazoan
# clades Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria within the Metazoa
# scope; members outside the scope carry the outside label, e.g. NonMetazoa).
# These are CLADES, not phyla — Bilateria is a clade (not a phylum); the machinery
# operates on ANY species-tree clades. The composite clades to REPORT are curated in
# INPUT_user/composite_clades_manifest.tsv. This GENERALIZES the earlier hardcoded
# analysis that fixed those five metazoan clades.
#
# Each manifest row names an ALGORITHM that tests a sequence group's member species:
#   - exact            : members come from EXACTLY the listed component clades
#                        (one-per-sequence group; auto-named cc_<components>-exact)
#   - absent           : members are ABSENT from ALL listed clades
#   - core_urclade     : members in >=1 OUTGROUP of the target clade AND >=1 listed
#                        ingroup -> the target's Ur (last-common-ancestor) core
#   - core_early_clade : members in >=2 listed ingroups, where the ingroups are the
#                        ambiguous (unresolved) nodes defining the target's "Early"
#                        window (its early descendant branches)
# `Ur` = last common ancestor of a clade; `Early` = the early descendants of a
# clade (the phylogenetic window spanned by the species tree's ambiguous nodes).
# absent / core_urclade / core_early_clade are independent membership tests, so one
# sequence group may match several composite clades of those algorithms at once.
# NOTE: composition is over the trees_species clade groupings, NOT the raw NCBI
# Phylum field used by phylum_from_phyloname() elsewhere in this module.


def load_composite_clades( config: dict, mappings_path: Path ) -> dict:
    """
    Load composite-clade definitions from config['composite_clades'] and resolve
    each group + the scope to species sets (from the trees_species clade->species
    mapping at the configured reference structure; Rule 6 => stable across trees).

    config['composite_clades'] schema:
        reference_structure : str       (structure whose clade->species to read)
        scope_clade_id_name : str       (ancestor the groups ideally partition)
        outside_label       : str       (name for members outside the scope)
        groups : [ { name: str, clade_id_names: [ clade_id_name, ... ] }, ... ]

    Returns dict { names, names___species, scope_species, outside_label } where
    `names` preserves config order (the signature order).

    Fail-fast: exits 1 if the block, a group's clades, or the scope resolve to zero
    species (a typo must not silently mis-classify every feature).
    """
    block = config.get( "composite_clades" )
    if not block:
        print( "CRITICAL ERROR: config is missing the 'composite_clades' block", file = sys.stderr )
        sys.exit( 1 )
    reference_structure = block[ "reference_structure" ]
    scope_clade_id_name = block[ "scope_clade_id_name" ]
    outside_label = block[ "outside_label" ]

    scope_species = load_clade_species( mappings_path, reference_structure, scope_clade_id_name )
    if not scope_species:
        print( f"CRITICAL ERROR: scope clade '{scope_clade_id_name}' resolved to zero species for {reference_structure}", file = sys.stderr )
        sys.exit( 1 )

    names = []
    names___species = {}
    for group in block[ "groups" ]:
        group_name = group[ "name" ]
        group_species = set()
        for clade_id_name in group[ "clade_id_names" ]:
            group_species |= load_clade_species( mappings_path, reference_structure, clade_id_name )
        if not group_species:
            print( f"CRITICAL ERROR: composite clade '{group_name}' resolved to zero species "
                   f"(clades {group[ 'clade_id_names' ]}, {reference_structure})", file = sys.stderr )
            sys.exit( 1 )
        names.append( group_name )
        names___species[ group_name ] = group_species

    # Display name for the scope clade (e.g. "Metazoa" from "C082_Metazoa"), so the
    # manifest can name the scope as a target without the clade_id prefix.
    scope_name = scope_clade_id_name.split( '_', 1 )[ 1 ] if '_' in scope_clade_id_name else scope_clade_id_name

    return { "names": names, "names___species": names___species,
             "scope_species": scope_species, "outside_label": outside_label,
             "scope_clade_id_name": scope_clade_id_name, "scope_name": scope_name,
             "reference_structure": reference_structure, "mappings_path": mappings_path }


def exact_components_of_species( member_species: set, composites: dict ) -> list:
    """
    The EXACT set of composite-clade components a feature unit occupies, from its
    member species, as an ordered list: the configured groups it has >=1 member
    species in (in config order), then the outside label when it has any member
    species outside the scope clade. This ordered list canonically names the
    feature's composite clade (see composite_clade_id).
    """
    components = [ name for name in composites[ "names" ]
                  if member_species & composites[ "names___species" ][ name ] ]
    if member_species - composites[ "scope_species" ]:
        components.append( composites[ "outside_label" ] )
    return components


def composite_clade_id_auto( ordered_tokens: list, algorithm: str ) -> str:
    """
    Auto-derived identifier for the DETERMINISTIC algorithms (exact, absent), which
    do not vary for a given clade set and therefore need no user name or number:
        cc_<token1>_<token2>_..._-<algorithm>
    e.g. composite_clade_id_auto( [ 'NonMetazoa' ], 'absent' ) -> 'cc_NonMetazoa-absent';
         composite_clade_id_auto( [ 'Porifera', 'Cnidaria' ], 'exact' ) -> 'cc_Porifera_Cnidaria-exact'.
    """
    return "cc_" + "_".join( ordered_tokens ) + "-" + algorithm


def composite_clade_id( ordered_components: list ) -> str:
    """Exact composite-clade identifier: cc_<components>-exact (see composite_clade_id_auto)."""
    return composite_clade_id_auto( ordered_components, "exact" )


# The four composite-clade algorithms (see the module header for definitions).
COMPOSITE_CLADE_ALGORITHMS = ( "exact", "absent", "core_urclade", "core_early_clade" )


def composite_clade_id_named( name: str, algorithm: str ) -> str:
    """
    Canonical identifier for a user-named composite clade (absent / core_urclade /
    core_early_clade):  cc_<Name>-<algorithm>
    e.g. composite_clade_id_named( 'Urmetazoa_001', 'core_urclade' )
         -> 'cc_Urmetazoa_001-core_urclade'.
    (`exact` composite clades are auto-named from their components by composite_clade_id.)
    """
    return f"cc_{name}-{algorithm}"


def resolve_clade_species( name: str, composites: dict ) -> set:
    """
    Resolve a composite-clades manifest clade NAME to its species set. A name may be
    a config group name (e.g. Ctenophora), the scope clade's display name or its
    clade_id_name (Metazoa / C082_Metazoa), or any raw clade_id_name present in the
    trees_species mapping at the reference structure. Fail-fast on an unresolvable
    name (a typo must not silently mis-classify every sequence group).
    """
    if name in composites[ "names___species" ]:
        return composites[ "names___species" ][ name ]
    if name == composites[ "scope_name" ] or name == composites[ "scope_clade_id_name" ]:
        return composites[ "scope_species" ]
    species = load_clade_species( composites[ "mappings_path" ], composites[ "reference_structure" ], name )
    if not species:
        print( f"CRITICAL ERROR: composite_clades manifest clade '{name}' is not a config group, "
               f"the scope ({composites[ 'scope_name' ]}), or a known clade_id_name for "
               f"{composites[ 'reference_structure' ]}", file = sys.stderr )
        sys.exit( 1 )
    return species


def _component_detail_column( component: str, composites: dict ) -> tuple:
    """
    Build one detail-table column spec ( label, kind, species_set ) for a building-
    block component. The outside label is a complement column ('out' = species NOT
    in the scope); a group is an 'in' column (species in that group).
    """
    if component == composites[ "outside_label" ]:
        return ( component, "out", composites[ "scope_species" ] )
    return ( component, "in", composites[ "names___species" ][ component ] )


def _order_absent_clades( clades: list, composites: dict ) -> list:
    """
    Canonical order for an absent composite clade's clade list (so its auto-derived
    cc_id is deterministic regardless of how the user listed them): building-block
    groups + the outside label in config order, then the scope name, then any other
    names alphabetically.
    """
    valid_components = list( composites[ "names" ] ) + [ composites[ "outside_label" ] ]
    component_order = { component: index for index, component in enumerate( valid_components ) }

    def order_key( name ):
        if name in component_order:
            return ( 0, component_order[ name ], name )
        if name == composites[ "scope_name" ] or name == composites[ "scope_clade_id_name" ]:
            return ( 1, 0, name )
        return ( 2, 0, name )

    return sorted( set( clades ), key = order_key )


def load_composite_clades_manifest( manifest_path: Path, composites: dict ) -> list:
    """
    Read the curated composite-clades manifest — a columnar TSV, one composite clade
    per row, with columns:

        Algorithm <TAB> Name <TAB> Target_Clade <TAB> Clades

      - Algorithm    : exact | absent | core_urclade | core_early_clade
      - Name         : the composite clade's short name (blank for exact, which
                       auto-names from its components); required for the others
      - Target_Clade : the focal clade (core_urclade / core_early_clade); blank for
                       exact and absent
      - Clades       : comma-delimited clade names — the COMPONENTS (exact), the
                       clades the members must be ABSENT from (absent), or the
                       INGROUPS (core_urclade / core_early_clade)

    Blank lines, '#'-comment lines, and a header row (column 0 == 'Algorithm') are
    skipped. Each clade name resolves via resolve_clade_species. Returns a list of
    entry dicts (config/manifest order), each carrying its algorithm, cc_id, a human-
    readable definition, the resolved species sets the matching test needs, and the
    detail-table column specs. Fail-fast on unknown algorithm, missing fields, an
    unknown clade, or an empty manifest.
    """
    entries = []
    seen_ids = set()
    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.rstrip( '\n' )
            if not line.strip() or line.lstrip().startswith( '#' ):
                continue
            parts = line.split( '\t' )
            while len( parts ) < 4:
                parts.append( '' )
            algorithm = parts[ 0 ].strip()
            name = parts[ 1 ].strip()
            target_name = parts[ 2 ].strip()
            clades = [ token.strip() for token in parts[ 3 ].split( ',' ) if token.strip() ]

            if algorithm.lower() == "algorithm":           # header row
                continue
            if algorithm not in COMPOSITE_CLADE_ALGORITHMS:
                print( f"CRITICAL ERROR: composite_clades manifest row '{line}' has unknown algorithm "
                       f"'{algorithm}'; valid: {', '.join( COMPOSITE_CLADE_ALGORITHMS )}", file = sys.stderr )
                sys.exit( 1 )
            if not clades:
                print( f"CRITICAL ERROR: composite_clades manifest row '{line}' lists no clades (column 4)", file = sys.stderr )
                sys.exit( 1 )

            entry = _build_composite_clade_entry( algorithm, name, target_name, clades, composites, line )
            if entry[ "cc_id" ] in seen_ids:
                continue
            seen_ids.add( entry[ "cc_id" ] )
            entries.append( entry )

    if not entries:
        print( f"CRITICAL ERROR: composite_clades manifest has no entries: {manifest_path}", file = sys.stderr )
        sys.exit( 1 )
    return entries


def _build_composite_clade_entry( algorithm, name, target_name, clades, composites, raw_line ):
    """Validate one manifest row and build its composite-clade entry (per algorithm)."""
    valid_components = list( composites[ "names" ] ) + [ composites[ "outside_label" ] ]
    component_order = { component: index for index, component in enumerate( valid_components ) }

    if algorithm == "exact":
        unknown = [ token for token in clades if token not in component_order ]
        if unknown:
            print( f"CRITICAL ERROR: composite_clades exact row '{raw_line}' has unknown component(s) {unknown}; "
                   f"valid components are {valid_components}", file = sys.stderr )
            sys.exit( 1 )
        ordered = sorted( set( clades ), key = lambda token: component_order[ token ] )
        return { "algorithm": "exact", "name": "", "cc_id": composite_clade_id( ordered ),
                 "components": ordered, "components_frozenset": frozenset( ordered ),
                 "definition": ','.join( ordered ),
                 "detail_columns": [ _component_detail_column( component, composites ) for component in ordered ] }

    if algorithm == "absent":
        # exact / absent do not vary for a given clade set -> auto-named, no user Name.
        # The outside label (e.g. NonMetazoa) is allowed: "absent from <outside>" means
        # no members fall outside the scope clade.
        absent_from_outside = composites[ "outside_label" ] in clades
        union_species = set()
        for clade in ( clade for clade in clades if clade != composites[ "outside_label" ] ):
            union_species |= resolve_clade_species( clade, composites )
        ordered_clades = _order_absent_clades( clades, composites )
        # Detail columns show where the members ARE (the building-block groups +
        # outside) -- by definition none fall in the absent-from clades.
        detail_columns = [ _component_detail_column( group, composites ) for group in composites[ "names" ] ]
        detail_columns.append( ( composites[ "outside_label" ], "out", composites[ "scope_species" ] ) )
        return { "algorithm": "absent", "name": "", "cc_id": composite_clade_id_auto( ordered_clades, "absent" ),
                 "clades": ordered_clades, "union_species": union_species, "absent_from_outside": absent_from_outside,
                 "definition": "absent from " + ','.join( ordered_clades ),
                 "detail_columns": detail_columns }

    # core_urclade / core_early_clade -- need a user Name + a target clade + ingroups
    if not name:
        print( f"CRITICAL ERROR: composite_clades {algorithm} row '{raw_line}' needs a Name (column 2)", file = sys.stderr )
        sys.exit( 1 )
    if not target_name:
        print( f"CRITICAL ERROR: composite_clades {algorithm} row '{raw_line}' needs a Target_Clade (column 3)", file = sys.stderr )
        sys.exit( 1 )
    target_species = resolve_clade_species( target_name, composites )
    ingroups___species = { ingroup: resolve_clade_species( ingroup, composites ) for ingroup in clades }
    ingroup_union = set().union( *ingroups___species.values() )

    if algorithm == "core_urclade":
        detail_columns = [ ( ingroup, "in", ingroups___species[ ingroup ] ) for ingroup in clades ]
        detail_columns.append( ( f"Outside_{target_name}", "out", target_species ) )
        return { "algorithm": "core_urclade", "name": name, "cc_id": composite_clade_id_named( name, "core_urclade" ),
                 "target_name": target_name, "target_species": target_species,
                 "ingroups": clades, "ingroups___species": ingroups___species, "ingroup_union": ingroup_union,
                 "definition": f"target {target_name}; ingroups " + ','.join( clades ),
                 "detail_columns": detail_columns }

    # core_early_clade
    detail_columns = [ ( ingroup, "in", ingroups___species[ ingroup ] ) for ingroup in clades ]
    return { "algorithm": "core_early_clade", "name": name, "cc_id": composite_clade_id_named( name, "core_early_clade" ),
             "target_name": target_name, "target_species": target_species,
             "ingroups": clades, "ingroups___species": ingroups___species, "ingroup_union": ingroup_union,
             "definition": f"target {target_name}; ingroups " + ','.join( clades ) + " (present in >=2)",
             "detail_columns": detail_columns }


def sequence_group_matches_composite_clade( entry: dict, member_species: set, composites: dict ) -> bool:
    """
    True if a sequence group (its set of member Genus_species) matches one composite-clade
    manifest entry, per that entry's algorithm:
      - exact            : the sequence group's exact component set equals the entry's
      - absent           : no member species in ANY of the entry's clades
      - core_urclade     : >=1 member outside the target AND >=1 member in an ingroup
      - core_early_clade : members in >=2 of the entry's ingroups
    """
    algorithm = entry[ "algorithm" ]
    if algorithm == "exact":
        return frozenset( exact_components_of_species( member_species, composites ) ) == entry[ "components_frozenset" ]
    if algorithm == "absent":
        if member_species & entry[ "union_species" ]:
            return False
        if entry[ "absent_from_outside" ] and ( member_species - composites[ "scope_species" ] ):
            return False
        return True
    if algorithm == "core_urclade":
        return bool( member_species - entry[ "target_species" ] ) and bool( member_species & entry[ "ingroup_union" ] )
    if algorithm == "core_early_clade":
        present = sum( 1 for ingroup_species in entry[ "ingroups___species" ].values() if member_species & ingroup_species )
        return present >= 2
    return False


def load_clade_species( mappings_path: Path, reference_structure: str, clade_id_name: str ) -> set:
    """
    Read a clade's descendant-species set (Genus_species) for one structure from
    the trees_species clade->species mapping. Returns a set; empty if not found
    (caller should fail-fast on empty for required clades).

    Tip (leaf) clades carry an empty Descendant_Species_List in the mapping (their
    Descendant_Species_Count is 0). A tip IS a single species named in its
    clade_id_name (C###_Genus_species), so when the row is found but the species list
    is empty the single species is derived from the clade_id_name. This mirrors
    Script 002's tip handling and lets leaf clades resolve to their one species
    (required for e.g. per-leaf 'absent' composite clades).
    """
    structure_clades = _load_structure_clade_species( mappings_path, reference_structure )
    return set( structure_clades.get( clade_id_name, set() ) )


# Cache of { ( mappings_path_str, reference_structure ): { clade_id_name: frozenset( species ) } }
# so the (large) clade->species mapping is scanned ONCE per structure even when hundreds
# of composite-clade manifest entries resolve clades (all-clades manifests).
_STRUCTURE_CLADE_SPECIES_CACHE = {}


def _load_structure_clade_species( mappings_path: Path, reference_structure: str ) -> dict:
    """
    Load ALL clade->species sets for one structure in a single pass (cached). Tip clades
    carry an empty Descendant_Species_List; their single species is derived from the
    clade_id_name (C###_Genus_species), matching Script 002's tip handling.
    """
    cache_key = ( str( mappings_path ), reference_structure )
    if cache_key in _STRUCTURE_CLADE_SPECIES_CACHE:
        return _STRUCTURE_CLADE_SPECIES_CACHE[ cache_key ]

    clades___species = {}
    with open( mappings_path, 'r' ) as input_mappings:
        header_ids___indices = build_header_index( input_mappings.readline() )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_species_list = header_ids___indices[ "Descendant_Species_List" ]
        for line in input_mappings:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_structure ] != reference_structure:
                continue
            clade_id_name = parts[ index_clade ]
            species_cell = parts[ index_species_list ] if index_species_list < len( parts ) else ""
            clade_species = { s for s in species_cell.split( ',' ) if s }
            # Tip clade: empty descendant list -> the single species is in the name.
            if not clade_species and '_' in clade_id_name:
                clade_species = { clade_id_name.split( '_', 1 )[ 1 ] }
            clades___species[ clade_id_name ] = frozenset( clade_species )

    _STRUCTURE_CLADE_SPECIES_CACHE[ cache_key ] = clades___species
    return clades___species


def bare_header_id( header: str ) -> str:
    """The bare column id of a self-documenting 'id (description)' header (text before ' (')."""
    return header.split( ' (' )[ 0 ].strip()


def phylum_from_phyloname( phyloname: str ) -> str:
    """
    Phylum field from a GIGANTIC phyloname
    (Kingdom_Phylum_Class_Order_Family_Genus_species; Phylum at parts[1]).
    May be 'UNOFFICIAL' or 'PhylumNNNNN' for unplaced taxa — returned as-is.
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 2:
        return parts_phyloname[ 1 ]
    return ''


def phylum_from_full_id( full_id: str ) -> str:
    """Phylum from a full GIGANTIC sequence ID (… -n_<phyloname>)."""
    if '-n_' not in full_id:
        return ''
    return phylum_from_phyloname( full_id.split( '-n_' )[ -1 ] )


def load_group_attributes( workflow_root: Path, config: dict, reserved_header_ids: set, override_group_attributes = None ):
    """
    Load the OPTIONAL per-group attributes table (config inputs.group_attributes) so its
    columns can be carried, as OPAQUE PASS-THROUGH, onto the per-group rows of the overlay
    outputs (deconvolution / per-species / composite). This keeps the engine
    producer-agnostic while letting each producer enrich its outputs with whatever per-group
    metadata it has:
      - annogroups    supplies 2_ai-<source>-annogroup_map.tsv (Source, Annogroup_Type,
                      Defining_Features, Annotation_Definitions, Species_List, ...)
      - orthogroups / gene families / gene groups supply their own table, or none.

    Table convention: the FIRST column is the join key (matched to SequenceGroup_ID); every
    other column is an attribute. Attribute columns whose bare id is already emitted by the
    calling script (reserved_header_ids, e.g. Sequence_Count / Species_Count) are skipped so
    the engine's own computed columns are never duplicated. The engine never interprets the
    attribute VALUES — it only carries them.

    Returns ( carried_headers, group_ids___carried_cells ):
        carried_headers            self-documenting headers to insert right after SequenceGroup_ID
        group_ids___carried_cells  { group_id: [ cell, ... ] } aligned to carried_headers
    Returns ( [], {} ) when inputs.group_attributes is unset/empty (join disabled).

    override_group_attributes: when not None, this value REPLACES config's
    inputs.group_attributes (used by the multi-producer runner, which passes each
    producer's own attributes path on the command line; an empty string disables the
    join for that producer). When None, the config value is used (single-producer mode).

    Fail-fast (§36): exits 1 if a path is configured but missing / malformed / has no rows.
    """
    if override_group_attributes is not None:
        raw_path = override_group_attributes
    else:
        inputs = config.get( "inputs", {} ) or {}
        raw_path = inputs.get( "group_attributes", "" )
    if not raw_path or not str( raw_path ).strip():
        return [], {}

    attributes_path = resolve_input_path( workflow_root, str( raw_path ).strip() )
    if not attributes_path.is_file():
        print( f"CRITICAL ERROR: group_attributes configured but not found: {attributes_path}", file = sys.stderr )
        sys.exit( 1 )

    with open( attributes_path, 'r' ) as input_attributes:
        parts_header = input_attributes.readline().rstrip( '\n' ).split( '\t' )
        if len( parts_header ) < 2:
            print( f"CRITICAL ERROR: group_attributes needs a key column plus >=1 attribute column: {attributes_path}", file = sys.stderr )
            sys.exit( 1 )
        # Column 0 is the join key; the rest are candidate attribute columns. Keep only the
        # candidates the calling script does not already emit (avoids duplicate columns).
        attribute_headers = parts_header[ 1: ]
        carried_indices = [ index for index, header in enumerate( attribute_headers )
                            if bare_header_id( header ) not in reserved_header_ids ]
        carried_headers = [ attribute_headers[ index ] for index in carried_indices ]

        group_ids___carried_cells = {}
        for line in input_attributes:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            group_id = parts[ 0 ]
            attribute_cells = parts[ 1: ]
            group_ids___carried_cells[ group_id ] = [
                attribute_cells[ index ] if index < len( attribute_cells ) else '' for index in carried_indices ]

    if not group_ids___carried_cells:
        print( f"CRITICAL ERROR: group_attributes table has a header but no data rows: {attributes_path}", file = sys.stderr )
        sys.exit( 1 )

    return carried_headers, group_ids___carried_cells
