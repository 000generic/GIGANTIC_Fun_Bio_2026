#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 20 | Purpose: Count curated gene family homologs per species from trees_gene_families output (additive, RGS + g_, no dedup)
# Human: Eric Edsinger

"""
GIGANTIC homolog_counts - Script 004: Count curated gene family homologs

Reads each gene family's AGS (all-gene-sets) `*-homologs.aa` FASTA from
trees_gene_families/output_to_input/<family>/STEP_1-homolog_discovery/ and
counts homolog sequences per species70 species per gene family.

IMPORTANT: only AGS FASTA files in STEP_1-homolog_discovery/ are read. Tree
files, alignments, ClipKit/FastTree outputs, and visualizations under
STEP_2-phylogenetic_analysis/ and STEP_3-tree_visualization/ are NOT touched.

KNOWN UPSTREAM BUG (May 2026): trees_gene_families STEP_1 AGS files contain
the SAME protein twice per gene family — once as `>rgs_` reference-query
AND once as `>g_*-n_<phyloname>` BLAST self-hit. Previous attempts at
upstream dedup did not resolve this.

For now (per user May 2026), this script counts ADDITIVELY: every RGS
header contributes +1 to its organism's mapped species70 species, AND
every >g_ header contributes +1 to its species. Counts are inflated for
species whose proteins also appear in the curated RGS set. The user will
fix the upstream AGS pipelines later and rerun homolog_counts; until then,
the counts here are over-inflated for any overlapping proteins.

Unknown RGS organism markers (anything beyond the mapping below) are
SKIPPED with a warning, not fatal-errored. Currently SKIPPED organisms
in trees_gene_families (per user May 2026):
  -mouse-   (1 RGS; Mus_musculus not in species70)
  -anemone- (1 RGS; ambiguous mapping among species70 cnidarians)

Outputs:

  1. 4-output/4_ai-counts-trees_gene_families.tsv
     Wide TSV: Feature_ID | Total_Count | Total_Species_Count | <70 species cols>

  2. 4-output/4_ai-log-count-trees_gene_families.log

FASTA header conventions:

  >rgs_<gene_family>-<organism>-<symbol>-<extra>-<protein_id>
      Curated reference. Mapped to a species70 species via
      RGS_ORGANISM___GENUS_SPECIES; skipped with warning if unknown.

  >g_<gene_id>-t_<transcript_id>-p_<protein_id>-n_<phyloname>
      Discovered homolog. Species identity from the `-n_<phyloname>` suffix.

Phyloname format mismatch handling: match on `genus_species`; use the
MANIFEST phyloname in output column headers; log substitutions.

Fail-fast: exits with code 1 on any malformed header, missing input file,
or genus_species not in species70 manifest. Unknown RGS organism markers
are tolerated (skipped + logged).

Usage (invoked by main.nf):
    python3 004_ai-python-count-trees_gene_families.py \\
        --species-order <path/to/1-output/1_ai-species70_alphabetical_phylonames.tsv> \\
        --gene-families-dir <path/to/trees_gene_families/output_to_input> \\
        --output-dir 4-output
"""

import argparse
import logging
import sys
from pathlib import Path


# Organism marker -> species70 genus_species mapping for RGS headers.
# Known markers (per user May 2026):
#   human/fly/worm    -> mapped (all in species70)
#   hydra             -> mapped (in species70, but not exercised in current data)
#   mouse/anemone     -> intentionally NOT mapped (skipped per user directive)
RGS_ORGANISM___GENUS_SPECIES = {
    'human': 'Homo_sapiens',
    'fly':   'Drosophila_melanogaster',
    'worm':  'Caenorhabditis_elegans',
    'hydra': 'Hydra_vulgaris',
}


# species70 species classified by Phylum-of-interest for the 4 phylum-list
# columns appended to the output (per user May 2026).
GENUS_SPECIES___PHYLUM_OF_INTEREST = {
    # Ctenophora
    'Beroe_ovata':                'Ctenophora',
    'Hormiphora_californensis':   'Ctenophora',
    'Pleurobrachia_bachei':       'Ctenophora',
    'Bolinopsis_microptera':      'Ctenophora',
    'Mnemiopsis_leidyi':          'Ctenophora',
    # Porifera
    'Sycon_ciliatum':             'Porifera',
    'Chondrosia_reniformis':      'Porifera',
    'Dysidea_avara':              'Porifera',
    'Ephydatia_muelleri':         'Porifera',
    'Halichondria_panicea':       'Porifera',
    'Oscarella_lobularis':        'Porifera',
    'Corticium_candelabrum':      'Porifera',
    # Placozoa (incl. Hoilungia)
    'Cladtertia_collaboinventa':  'Placozoa',
    'Trichoplax_adhaerens':       'Placozoa',
    'Trichoplax_sp_H2':           'Placozoa',
    'Hoilungia_hongkongensis_H13':'Placozoa',
    # Cnidaria
    'Nematostella_vectensis':     'Cnidaria',
    'Acropora_muricata':          'Cnidaria',
    'Pocillopora_verrucosa':      'Cnidaria',
    'Hydractinia_symbiolongicarpus':'Cnidaria',
    'Hydra_vulgaris':             'Cnidaria',
}

PHYLUM_LIST_ORDER = [ 'Ctenophora', 'Porifera', 'Placozoa', 'Cnidaria' ]


def resolve_against_workflow_root( raw_path, workflow_root ):
    """Resolve an upstream input path so it survives NextFlow work/ execution.

    Config paths are relative to the workflow directory (where
    START_HERE-user_config.yaml lives). NextFlow runs each task in a work/
    subdir, so a bare relative path would resolve against the wrong CWD.
    Anchor relative paths against workflow_root (an absolute path passed by
    main.nf as ${projectDir}/..); leave already-absolute paths untouched.
    """
    path = Path( raw_path )
    if path.is_absolute():
        return path
    return ( Path( workflow_root ) / path ).resolve()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description = 'Count curated gene family homologs per species from trees_gene_families output'
    )
    parser.add_argument(
        '--workflow-root',
        required = True,
        help = 'Absolute path to the workflow directory (main.nf passes ${projectDir}/..); relative --gene-families-dir is resolved against this'
    )
    parser.add_argument(
        '--species-order',
        required = True,
        help = 'Path to script 001 output (1_ai-species70_alphabetical_phylonames.tsv)'
    )
    parser.add_argument(
        '--gene-families-dir',
        required = True,
        help = 'Path to trees_gene_families/output_to_input (contains one subdir per gene family)'
    )
    parser.add_argument(
        '--output-dir',
        required = True,
        help = 'Output directory (4-output)'
    )
    return parser.parse_args()


def setup_logging( output_dir ):
    log_path = Path( output_dir ) / '4_ai-log-count-trees_gene_families.log'
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = logging.getLogger( 'count_trees_gene_families' )
    logger.setLevel( logging.INFO )
    logger.handlers.clear()

    formatter = logging.Formatter( '%(asctime)s | %(levelname)s | %(message)s' )

    file_handler = logging.FileHandler( log_path, mode = 'w' )
    file_handler.setFormatter( formatter )
    logger.addHandler( file_handler )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter( formatter )
    logger.addHandler( stream_handler )

    return logger


def extract_genus_species_from_phyloname( phyloname ):
    """Extract genus_species from a phyloname (parts[5:] joined)."""
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) < 7:
        raise ValueError( f'phyloname has fewer than 7 underscore-separated fields: {phyloname}' )
    return '_'.join( parts_phyloname[ 5: ] )


def parse_rgs_header( header_content ):
    """Parse an >rgs_ header into (organism, protein_id)."""
    parts = header_content.split( '-' )
    if len( parts ) < 4:
        raise ValueError( f'RGS header has fewer than 4 dash-separated fields: {header_content}' )
    return parts[ 1 ], parts[ -1 ]


def parse_g_header( header_content ):
    """Parse a >g_ header into (gene_id, protein_id, phyloname)."""
    if not header_content.startswith( 'g_' ):
        raise ValueError( f'g_ header does not start with g_: {header_content}' )
    if '-n_' not in header_content:
        raise ValueError( f'g_ header missing -n_ phyloname suffix: {header_content}' )
    before_n, phyloname = header_content.rsplit( '-n_', 1 )
    if '-p_' not in before_n:
        raise ValueError( f'g_ header missing -p_ protein_id field: {header_content}' )
    before_p, protein_id = before_n.rsplit( '-p_', 1 )
    if '-t_' not in before_p:
        raise ValueError( f'g_ header missing -t_ transcript_id field: {header_content}' )
    g_part, _ = before_p.split( '-t_', 1 )
    gene_id = g_part[ len( 'g_' ): ]
    return gene_id, protein_id, phyloname


def main():
    args = parse_arguments()
    output_dir = Path( args.output_dir )

    logger = setup_logging( output_dir )

    logger.info( '====================================================================' )
    logger.info( 'GIGANTIC homolog_counts Script 004: Count trees_gene_families homologs' )
    logger.info( '====================================================================' )
    logger.info( f'Input species order:     {args.species_order}' )
    logger.info( f'Input gene_families dir: {args.gene_families_dir}' )
    logger.info( f'Output directory:        {output_dir}' )
    logger.info( '' )
    logger.info( 'Counting mode: ADDITIVE (RGS + >g_; no dedup).' )
    logger.info( '  Upstream AGS pipeline currently emits the same protein twice (RGS + BLAST self-hit).' )
    logger.info( '  Counts for species with RGS contributions are inflated for overlapping proteins.' )
    logger.info( '  Resolves after upstream AGS fix + rerun.' )
    logger.info( '' )

    # ========================================================================
    # Read canonical species order from script 001 output
    # ========================================================================
    # Column_Index (...)	Phyloname (...)	Genus_Species (...)	Phyloname_Taxonid (...)
    # 1	Kingdom10919_..._Abeoforma_whisleri	Abeoforma_whisleri	Kingdom10919_..._Abeoforma_whisleri___749232

    input_species_order_path = Path( args.species_order )
    if not input_species_order_path.exists():
        logger.error( 'CRITICAL ERROR: species order file not found' )
        logger.error( f'Expected at: {input_species_order_path}' )
        logger.error( 'Script 001 must run successfully before script 004.' )
        sys.exit( 1 )

    canonical_phylonames_in_order = []
    genus_species___manifest_phyloname = {}
    manifest_phyloname___canonical_index = {}
    line_number = 0
    header_seen = False

    with open( input_species_order_path, 'r' ) as input_species_order:
        for line in input_species_order:
            line = line.strip()
            line_number += 1

            if not line:
                continue

            parts = line.split( '\t' )

            if not header_seen:
                header_seen = True
                continue

            if len( parts ) < 4:
                logger.error( f'CRITICAL ERROR: species_order row {line_number} has fewer than 4 columns' )
                sys.exit( 1 )

            manifest_phyloname = parts[ 1 ].strip()
            genus_species = parts[ 2 ].strip()

            canonical_phylonames_in_order.append( manifest_phyloname )
            genus_species___manifest_phyloname[ genus_species ] = manifest_phyloname
            manifest_phyloname___canonical_index[ manifest_phyloname ] = len( canonical_phylonames_in_order ) - 1

    species70_count = len( canonical_phylonames_in_order )
    if species70_count != 70:
        logger.error( f'CRITICAL ERROR: expected 70 species in species_order, got {species70_count}' )
        sys.exit( 1 )

    logger.info( f'[OK] Read {species70_count} species from canonical species order' )

    # Validate RGS organism mappings target species70 species
    for organism, expected_genus_species in RGS_ORGANISM___GENUS_SPECIES.items():
        if expected_genus_species not in genus_species___manifest_phyloname:
            logger.error( f'CRITICAL ERROR: RGS_ORGANISM___GENUS_SPECIES maps -{organism}- to {expected_genus_species!r} which is not in species70.' )
            sys.exit( 1 )

    logger.info( '[OK] RGS organism mapping validated:' )
    for organism in sorted( RGS_ORGANISM___GENUS_SPECIES ):
        logger.info( f'    -{organism}- -> {RGS_ORGANISM___GENUS_SPECIES[ organism ]}' )

    # ========================================================================
    # Enumerate gene family directories
    # ========================================================================

    input_gene_families_dir = resolve_against_workflow_root( args.gene_families_dir, args.workflow_root )

    if not input_gene_families_dir.is_dir():
        logger.error( f'CRITICAL ERROR: gene_families_dir is not a directory: {input_gene_families_dir}' )
        sys.exit( 1 )

    gene_family_dirs = sorted( [
        path for path in input_gene_families_dir.iterdir()
        if path.is_dir()
    ] )

    gene_family_dir_count = len( gene_family_dirs )
    if gene_family_dir_count == 0:
        logger.error( f'CRITICAL ERROR: zero gene family directories under {input_gene_families_dir}' )
        sys.exit( 1 )

    logger.info( f'[OK] Found {gene_family_dir_count} gene family directories' )

    # ========================================================================
    # Process each gene family
    # ========================================================================

    output_rows = []
    total_rgs_headers_counted = 0
    total_rgs_headers_skipped = 0
    total_g_headers_counted = 0
    organism___rgs_counted = {}
    organism___rgs_skipped = {}
    phyloname_substitutions___count = {}

    for gene_family_dir in gene_family_dirs:
        gene_family_name = gene_family_dir.name
        step_1_dir = gene_family_dir / 'STEP_1-homolog_discovery'

        if not step_1_dir.is_dir():
            logger.error( f'CRITICAL ERROR: missing STEP_1-homolog_discovery in {gene_family_dir}' )
            sys.exit( 1 )

        homologs_files = sorted( step_1_dir.glob( '*-homologs.aa' ) )

        if len( homologs_files ) == 0:
            logger.error( f'CRITICAL ERROR: no AGS *-homologs.aa file in {step_1_dir}' )
            sys.exit( 1 )

        if len( homologs_files ) > 1:
            logger.error( f'CRITICAL ERROR: multiple *-homologs.aa files in {step_1_dir}:' )
            for path in homologs_files:
                logger.error( f'    - {path.name}' )
            sys.exit( 1 )

        input_homologs_path = homologs_files[ 0 ]

        # Per-family integer counters + extra-column tracking
        canonical_counts = [ 0 ] * species70_count
        human_gene_names_seen = set()
        human_gene_names_order = []
        phylum___gene_ids = { phylum: [] for phylum in PHYLUM_LIST_ORDER }

        with open( input_homologs_path, 'r' ) as input_homologs:
            for line in input_homologs:
                line = line.strip()
                if not line.startswith( '>' ):
                    continue

                header_content = line[ 1: ]

                if header_content.startswith( 'rgs_' ):
                    try:
                        organism, _ = parse_rgs_header( header_content )
                    except ValueError as parse_error:
                        logger.error( f'CRITICAL ERROR: malformed RGS header in {input_homologs_path}' )
                        logger.error( f'  Header: >{header_content}' )
                        logger.error( f'  Error: {parse_error}' )
                        sys.exit( 1 )

                    rgs_genus_species = RGS_ORGANISM___GENUS_SPECIES.get( organism )
                    if rgs_genus_species is None:
                        organism___rgs_skipped[ organism ] = organism___rgs_skipped.get( organism, 0 ) + 1
                        total_rgs_headers_skipped += 1
                        continue

                    manifest_phyloname = genus_species___manifest_phyloname.get( rgs_genus_species )
                    if manifest_phyloname is None:
                        logger.error( f'CRITICAL ERROR: RGS organism {organism!r} maps to {rgs_genus_species!r} which is not in species70.' )
                        sys.exit( 1 )

                    canonical_index = manifest_phyloname___canonical_index[ manifest_phyloname ]
                    canonical_counts[ canonical_index ] += 1

                    # RGS human contribution to the human-gene-names column.
                    # RGS format: rgs_<group>-<organism>-<gene_name>-<extra>-<protein_id>
                    if rgs_genus_species == 'Homo_sapiens':
                        parts_header = header_content.split( '-' )
                        if len( parts_header ) >= 3:
                            gene_name = parts_header[ 2 ]
                            if gene_name not in human_gene_names_seen:
                                human_gene_names_seen.add( gene_name )
                                human_gene_names_order.append( gene_name )

                    organism___rgs_counted[ organism ] = organism___rgs_counted.get( organism, 0 ) + 1
                    total_rgs_headers_counted += 1

                elif header_content.startswith( 'g_' ):
                    try:
                        gene_id, _, fasta_phyloname = parse_g_header( header_content )
                    except ValueError as parse_error:
                        logger.error( f'CRITICAL ERROR: malformed g_ header in {input_homologs_path}' )
                        logger.error( f'  Header: >{header_content}' )
                        logger.error( f'  Error: {parse_error}' )
                        sys.exit( 1 )

                    try:
                        genus_species = extract_genus_species_from_phyloname( fasta_phyloname )
                    except ValueError as parse_error:
                        logger.error( f'CRITICAL ERROR: cannot extract genus_species from FASTA phyloname in {input_homologs_path}' )
                        logger.error( f'  Header: >{header_content}' )
                        logger.error( f'  Error: {parse_error}' )
                        sys.exit( 1 )

                    manifest_phyloname = genus_species___manifest_phyloname.get( genus_species )
                    if manifest_phyloname is None:
                        logger.error( f'CRITICAL ERROR: genus_species not in species70 manifest: {genus_species}' )
                        logger.error( f'  Source file:     {input_homologs_path}' )
                        logger.error( f'  FASTA phyloname: {fasta_phyloname}' )
                        sys.exit( 1 )

                    if fasta_phyloname != manifest_phyloname:
                        substitution_key = ( fasta_phyloname, manifest_phyloname )
                        phyloname_substitutions___count[ substitution_key ] = phyloname_substitutions___count.get( substitution_key, 0 ) + 1

                    canonical_index = manifest_phyloname___canonical_index[ manifest_phyloname ]
                    canonical_counts[ canonical_index ] += 1
                    total_g_headers_counted += 1

                    # Human gene names: gene_id for Homo_sapiens (dedup)
                    if genus_species == 'Homo_sapiens':
                        if gene_id not in human_gene_names_seen:
                            human_gene_names_seen.add( gene_id )
                            human_gene_names_order.append( gene_id )

                    # Phylum-of-interest sequence IDs
                    phylum = GENUS_SPECIES___PHYLUM_OF_INTEREST.get( genus_species )
                    if phylum is not None:
                        phylum___gene_ids[ phylum ].append( gene_id )

                else:
                    logger.error( f'CRITICAL ERROR: unexpected FASTA header format in {input_homologs_path}' )
                    logger.error( f'  Header: >{header_content}' )
                    logger.error( '  Expected prefix: >rgs_ or >g_.' )
                    sys.exit( 1 )

        total_count = sum( canonical_counts )
        total_species_count = sum( 1 for count in canonical_counts if count >= 1 )

        human_gene_names_column = ';'.join( human_gene_names_order )
        phylum_columns = [ ';'.join( phylum___gene_ids[ phylum ] ) for phylum in PHYLUM_LIST_ORDER ]

        output_rows.append( (
            gene_family_name,
            total_count,
            total_species_count,
            canonical_counts,
            human_gene_names_column,
            phylum_columns,
        ) )

    logger.info( f'[OK] Parsed {gene_family_dir_count} gene family AGS FASTA files' )
    logger.info( f'     Total RGS headers counted:           {total_rgs_headers_counted}' )
    logger.info( f'     Total RGS headers skipped (unknown): {total_rgs_headers_skipped}' )
    logger.info( f'     Total >g_ headers counted:           {total_g_headers_counted}' )

    # ========================================================================
    # Report RGS organism markers
    # ========================================================================

    if organism___rgs_counted:
        logger.info( '' )
        logger.info( 'RGS headers counted, grouped by organism marker:' )
        for organism in sorted( organism___rgs_counted ):
            species = RGS_ORGANISM___GENUS_SPECIES[ organism ]
            logger.info( f'  -{organism}- -> {species}: {organism___rgs_counted[ organism ]}' )

    if organism___rgs_skipped:
        logger.info( '' )
        logger.info( 'RGS headers SKIPPED (unknown organism marker; no species70 mapping):' )
        for organism in sorted( organism___rgs_skipped ):
            logger.info( f'  -{organism}-: {organism___rgs_skipped[ organism ]} (decide mapping or accept as not-in-species70)' )

    # ========================================================================
    # Report phyloname substitutions
    # ========================================================================

    if phyloname_substitutions___count:
        logger.info( '' )
        logger.info( 'Phyloname substitutions applied (FASTA stale -> manifest current):' )
        for ( fasta_phyloname, manifest_phyloname ), occurrence_count in sorted( phyloname_substitutions___count.items() ):
            genus_species = extract_genus_species_from_phyloname( manifest_phyloname )
            logger.info( f'  {genus_species}:' )
            logger.info( f'    FASTA:    {fasta_phyloname}' )
            logger.info( f'    Manifest: {manifest_phyloname}' )
            logger.info( f'    Header occurrences substituted: {occurrence_count}' )

    # ========================================================================
    # Write output TSV
    # ========================================================================

    output_counts_path = output_dir / '4_ai-counts-trees_gene_families.tsv'

    header_parts = [
        'Feature_ID (curated gene family name from trees_gene_families/output_to_input/<family>/)',
        'Total_Count (sum of homolog protein header counts across all 70 species in this gene family; ADDITIVE across RGS and >g_ sources; may include duplicates from the known upstream AGS pipeline bug)',
        'Total_Species_Count (number of species with at least 1 RGS or >g_ header in this gene family)',
    ]
    for canonical_phyloname in canonical_phylonames_in_order:
        header_parts.append( f'{canonical_phyloname} (homolog protein header count for this species in this gene family; ADDITIVE across RGS and >g_ sources; may include duplicates pending upstream AGS pipeline fix)' )

    header_parts.extend( [
        'Human_Gene_Names_List (semicolon delimited list of human HGNC symbols from >rgs_*-human- entries combined with gene_id values from >g_*-Homo_sapiens entries in this gene family; deduplicated)',
        'Ctenophore_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<ctenophore species> entries in this gene family; species: Beroe_ovata, Hormiphora_californensis, Pleurobrachia_bachei, Bolinopsis_microptera, Mnemiopsis_leidyi)',
        'Sponge_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<sponge species> entries in this gene family; species: Sycon_ciliatum, Chondrosia_reniformis, Dysidea_avara, Ephydatia_muelleri, Halichondria_panicea, Oscarella_lobularis, Corticium_candelabrum)',
        'Placozoan_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<placozoan species> entries in this gene family; species: Cladtertia_collaboinventa, Trichoplax_adhaerens, Trichoplax_sp_H2, Hoilungia_hongkongensis_H13)',
        'Cnidarian_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<cnidarian species> entries in this gene family; species: Nematostella_vectensis, Acropora_muricata, Pocillopora_verrucosa, Hydractinia_symbiolongicarpus, Hydra_vulgaris)',
    ] )

    output = '\t'.join( header_parts ) + '\n'

    with open( output_counts_path, 'w' ) as output_counts:
        output_counts.write( output )

        for gene_family_name, total_count, total_species_count, canonical_counts, human_gene_names_column, phylum_columns in output_rows:
            row_parts = [ gene_family_name, str( total_count ), str( total_species_count ) ]
            row_parts.extend( str( count ) for count in canonical_counts )
            row_parts.append( human_gene_names_column )
            row_parts.extend( phylum_columns )
            output = '\t'.join( row_parts ) + '\n'
            output_counts.write( output )

    logger.info( '' )
    logger.info( f'[OK] Wrote count table to: {output_counts_path}' )
    logger.info( f'     Rows: {gene_family_dir_count} (excluding header)' )
    logger.info( f'     Columns: 3 summary + 70 species + 5 extra = 78' )

    # ========================================================================
    # Summary stats
    # ========================================================================

    gene_families_zero = sum( 1 for row in output_rows if row[ 2 ] == 0 )
    gene_families_singleton_species = sum( 1 for row in output_rows if row[ 2 ] == 1 )
    gene_families_universal = sum( 1 for row in output_rows if row[ 2 ] == 70 )

    logger.info( '' )
    logger.info( 'Summary:' )
    logger.info( f'  Total gene families:                          {gene_family_dir_count}' )
    logger.info( f'  Total RGS headers counted:                    {total_rgs_headers_counted}' )
    logger.info( f'  Total RGS headers skipped (unknown):          {total_rgs_headers_skipped}' )
    logger.info( f'  Total >g_ headers counted:                    {total_g_headers_counted}' )
    logger.info( f'  Gene families with 0 species (no homologs):   {gene_families_zero}' )
    logger.info( f'  Gene families present in only 1 species:      {gene_families_singleton_species}' )
    logger.info( f'  Gene families present in all 70 species:      {gene_families_universal}' )

    logger.info( '' )
    logger.info( '====================================================================' )
    logger.info( 'Script 004 complete: trees_gene_families counts (additive, RGS+>g_) re-keyed to species70 canonical order.' )
    logger.info( '====================================================================' )


if __name__ == '__main__':
    main()
