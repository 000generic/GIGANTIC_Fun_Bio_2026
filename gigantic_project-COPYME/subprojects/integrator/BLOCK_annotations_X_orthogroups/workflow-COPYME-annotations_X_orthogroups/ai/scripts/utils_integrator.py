# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 04 | Purpose: Shared helpers for the orthogroups_ocl_X_features integration scripts
# Human: Eric Edsinger

"""
Shared helpers for the integrator orthogroups_ocl_X_features pipeline.

Provides:
  - load_config / resolve_input_path : YAML config + path resolution
  - parse_full_gigantic_id           : split a GIGANTIC sequence ID into parts
  - genus_species_from_phyloname     : phyloname -> Genus_species
  - build_header_index               : self-documenting-header column lookup
  - DELIM                            : in-column list delimiter (bare comma, §34)

All scripts in this workflow import this module via:
    sys.path.insert( 0, str( Path( __file__ ).parent ) )
    import utils_integrator
"""

from pathlib import Path
import sys
import yaml

_INTEGRATOR_AI = Path( __file__ ).resolve().parents[ 4 ] / "ai"
if str( _INTEGRATOR_AI ) not in sys.path:
    sys.path.insert( 0, str( _INTEGRATOR_AI ) )

import utils_integrator_shared as _SHARED

find_output_pipeline_root = _SHARED.find_output_pipeline_root
resolve_workflow_run_timestamp_suffix = _SHARED.resolve_workflow_run_timestamp_suffix
build_timestamped_filename = _SHARED.build_timestamped_filename
resolve_timestamped_output_path = _SHARED.resolve_timestamped_output_path


def timestamped_output_path( output_dir: Path, stem: str, output_base: Path, extension: str = '.tsv' ) -> Path:
    """Build a timestamped archival path under output_dir using the shared run suffix (§65)."""
    pipeline_root = find_output_pipeline_root( output_base )
    suffix = resolve_workflow_run_timestamp_suffix( pipeline_root )
    return output_dir / build_timestamped_filename( stem, suffix, extension )


def resolve_composition_table_path( output_base: Path ) -> Path:
    """Script 001 composition table (timestamped filename, shared run suffix)."""
    return resolve_timestamped_output_path( output_base / "1-output", "1_ai-orthogroups-species_composition", output_base )

# In-column multi-value delimiter — bare comma per gigantic_conventions §34.
DELIM = ','


# ---------------------------------------------------------------------------
# Metazoan phylum composition (BLOCK_annotations_X_orthogroups, 2026-06-23)
# ---------------------------------------------------------------------------
# The five metazoan groups PARTITION Metazoa (each metazoan species falls in
# exactly one), verified fail-fast in Script 001. Display / signature order is
# fixed below: the first four are the non-bilaterian metazoan phyla; Bilateria is
# the fifth.
METAZOAN_PHYLA = [ "Ctenophora", "Porifera", "Placozoa", "Cnidaria", "Bilateria" ]
NON_BILATERIAN_PHYLA = frozenset( { "Ctenophora", "Porifera", "Placozoa", "Cnidaria" } )

# Named phylum-composition classes (Eric-specified, 2026-06-23). Each key maps to
# an EXACT metazoan phylum signature (frozenset of the names above). A signature
# class applies ONLY when the orthogroup has NO non-metazoan (outgroup) members —
# "...only" excludes non-metazoans (Eric, 2026-06-23). Mixed_With_NonMetazoan is
# the SEPARATE non-metazoan-bearing bucket and is resolved in named_phylum_class()
# (not in this dict). There is deliberately NO catch-all: signatures not listed
# here are simply not tallied in the named columns. This loses nothing because
# Script 001 records every orthogroup's exact Metazoan_Phylum_Signature, so any
# unlisted combination is always recoverable from the 1-output table.
PHYLUM_SIGNATURE___CLASS_KEY = {
    frozenset( { "Ctenophora" } ):                                          "Ctenophora_Only",
    frozenset( { "Porifera" } ):                                            "Porifera_Only",
    frozenset( { "Placozoa" } ):                                            "Placozoa_Only",
    frozenset( { "Cnidaria" } ):                                            "Cnidaria_Only",
    frozenset( { "Ctenophora", "Porifera" } ):                             "Mixed_Ctenophora_Porifera_Only",
    frozenset( { "Ctenophora", "Placozoa" } ):                             "Mixed_Ctenophora_Placozoa_Only",
    frozenset( { "Ctenophora", "Cnidaria" } ):                             "Mixed_Ctenophora_Cnidaria_Only",
    frozenset( { "Ctenophora", "Bilateria" } ):                            "Mixed_Ctenophora_Bilateria_Only",
    frozenset( { "Ctenophora", "Porifera", "Placozoa" } ):                 "Mixed_Ctenophora_Porifera_Placozoa_Only",
    frozenset( { "Ctenophora", "Porifera", "Placozoa", "Cnidaria" } ):     "Mixed_Ctenophora_Porifera_Placozoa_Cnidaria_Only",
    frozenset( { "Porifera", "Placozoa" } ):                               "Mixed_Porifera_Placozoa_Only",
    frozenset( { "Porifera", "Placozoa", "Cnidaria" } ):                   "Mixed_Porifera_Placozoa_Cnidaria_Only",
    frozenset( { "Placozoa", "Cnidaria" } ):                               "Mixed_Placozoa_Cnidaria_Only",
    frozenset( { "Placozoa", "Bilateria" } ):                              "Mixed_Placozoa_Bilateria_Only",
    frozenset( { "Cnidaria", "Bilateria" } ):                              "Mixed_Cnidaria_Bilateria_Only",
}

# Ordered list of every named phylum-composition column key — the signature
# classes in the dict's insertion order above, then Mixed_With_NonMetazoan last.
# Single source of truth for Table 1 column order (Script 003) and validation
# (Script 004).
PHYLUM_COMPOSITION_CLASS_KEYS = []
for _base_key in PHYLUM_SIGNATURE___CLASS_KEY.values():
    PHYLUM_COMPOSITION_CLASS_KEYS.append( _base_key )
    PHYLUM_COMPOSITION_CLASS_KEYS.append( _base_key + "_With_NonMetazoan" )


def _signature_in_order( signature: frozenset ) -> list:
    """Phyla present in `signature`, returned in the fixed METAZOAN_PHYLA order."""
    return [ phylum for phylum in METAZOAN_PHYLA if phylum in signature ]


# Human-readable phrase per class key, for self-documenting headers (§34).
PHYLUM_COMPOSITION_CLASS_DESCRIPTIONS = {}
for _signature, _base_key in PHYLUM_SIGNATURE___CLASS_KEY.items():
    _ordered = _signature_in_order( _signature )
    if len( _ordered ) == 1:
        _phyla_phrase = f"only { _ordered[ 0 ] } among metazoan phyla"
    else:
        _phyla_phrase = f"exactly { ' plus '.join( _ordered ) } among metazoan phyla"
    PHYLUM_COMPOSITION_CLASS_DESCRIPTIONS[ _base_key ] = f"{_phyla_phrase} and no non-metazoan members"
    PHYLUM_COMPOSITION_CLASS_DESCRIPTIONS[ _base_key + "_With_NonMetazoan" ] = f"{_phyla_phrase} plus one or more non-metazoan outgroup members"


def parse_signature_cell( signature_cell: str ) -> frozenset:
    """Metazoan_Phylum_Signature cell (comma-delimited, may be empty) -> frozenset."""
    return frozenset( token for token in signature_cell.split( DELIM ) if token )


def named_phylum_class( signature: frozenset, has_nonmetazoan: bool ):
    """
    Resolve one orthogroup's named phylum-composition class from its EXACT
    metazoan phylum signature plus whether it has any non-metazoan member.

    Returns the column key (one of PHYLUM_COMPOSITION_CLASS_KEYS) or None when the
    orthogroup matches no named class (deliberately uncounted — see note above).

    Disjoint by construction: has_nonmetazoan True can only yield
    Mixed_With_NonMetazoan; has_nonmetazoan False can only yield a signature class.
    So each orthogroup contributes to at most one named class.
    """
    base_key = PHYLUM_SIGNATURE___CLASS_KEY.get( signature )
    if base_key is None:
        return None
    return base_key + "_With_NonMetazoan" if has_nonmetazoan else base_key


def load_config( config_path: str ) -> dict:
    """Load the START_HERE-user_config.yaml into a nested dict."""
    with open( config_path, 'r' ) as input_config:
        config = yaml.safe_load( input_config )
    return config


def workflow_root_from_output_dir( output_dir: str ) -> Path:
    """
    The workflow root is the parent of OUTPUT_pipeline. Input paths in the
    YAML are written relative to the workflow root (per gigantic_conventions §5).
    """
    return Path( output_dir ).resolve().parent


def resolve_input_path( workflow_root: Path, relative_path: str ) -> Path:
    """Resolve a YAML-relative input path against the workflow root."""
    return ( workflow_root / relative_path ).resolve()


def parse_full_gigantic_id( full_id: str ) -> tuple:
    """
    Split a full GIGANTIC sequence identifier into ( source_gene_field,
    phyloname, genus_species ).

    Format: g_<gene>-t_<rna>-p_<protein>-n_<phyloname>
    Delimiters '-t_', '-p_', '-n_' are hyphen-prefixed; phylonames and gene
    fields use underscores (no hyphens), so the splits are unambiguous.

    Returns ( None, None, None ) if the ID does not contain the expected
    markers (caller decides how to handle).
    """
    if '-n_' not in full_id or not full_id.startswith( 'g_' ):
        return ( None, None, None )

    # g_ field: between leading 'g_' and the first '-t_'
    source_gene_field = full_id.split( '-t_' )[ 0 ][ 2: ]

    # phyloname: everything after the final '-n_'
    phyloname = full_id.split( '-n_' )[ -1 ]

    genus_species = genus_species_from_phyloname( phyloname )

    return ( source_gene_field, phyloname, genus_species )


def genus_species_from_phyloname( phyloname: str ) -> str:
    """
    Extract Genus_species from a GIGANTIC phyloname.

    Phyloname = Kingdom_Phylum_Class_Order_Family_Genus_species (7+ fields);
    genus + species occupy positions 5.. (0-indexed). Multi-word species
    (e.g. Hoilungia_hongkongensis_H13) are preserved by joining parts[5:].
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 7:
        return '_'.join( parts_phyloname[ 5: ] )
    # Fallback: phyloname is non-standard; return as-is so the caller can
    # surface the mismatch rather than silently mis-joining.
    return phyloname


def build_header_index( header_line: str ) -> dict:
    """
    Map self-documenting header IDs to column indices.

    GIGANTIC TSV headers look like 'Status (DARK if all three axes False ...)';
    the header_ID is the text before ' (' . Returns { header_ID : index }.
    """
    header_ids___indices = {}
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( parts_header_line ):
        header_id = column.split( ' (' )[ 0 ].strip()
        header_ids___indices[ header_id ] = index
    return header_ids___indices


def species_label_from_filename( filename: str, marker: str ) -> str:
    """
    Derive the Genus_species (or token) that follows `marker` in a per-species
    output filename. Example: marker='dark_proteome-' on
    '3_ai-dark_proteome-Homo_sapiens.tsv' -> 'Homo_sapiens'.
    """
    stem = filename
    if stem.endswith( '.tsv' ):
        stem = stem[ :-4 ]
    if marker in stem:
        return stem.split( marker, 1 )[ 1 ]
    return stem
