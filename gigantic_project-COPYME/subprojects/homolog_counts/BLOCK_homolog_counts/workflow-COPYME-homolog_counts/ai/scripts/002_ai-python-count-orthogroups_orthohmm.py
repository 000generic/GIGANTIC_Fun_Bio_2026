#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 20 | Purpose: Count orthogroups per species from orthogroups/BLOCK_orthohmm output
# Human: Eric Edsinger

"""
GIGANTIC homolog_counts - Script 002: Count orthogroups from BLOCK_orthohmm

Reads the upstream OrthoHMM gene_count file and re-keys it into the canonical
species70 alphabetical phyloname column order produced by script 001. Adds
Total_Count and Total_Species_Count summary columns.

Outputs:

  1. 2-output/2_ai-counts-orthogroups_orthohmm.tsv
     Wide TSV with one row per orthogroup. Columns:
       Feature_ID | Total_Count | Total_Species_Count | <70 species phyloname columns>

  2. 2-output/2_ai-log-count-orthogroups_orthohmm.log

Upstream file format notes:
  - gene_count_gigantic_ids.tsv is WHITESPACE-delimited (not tab), inherited
    from OrthoFinder/OrthoHMM native format
  - Species columns are labeled <genus_species>.pep
  - Each data row starts with <orthogroup_id>: (trailing colon)
  - Counts per species per orthogroup are pre-computed

Fail-fast: exits with code 1 on any validation error (file missing, wrong
column count, species set mismatch with species70, non-integer counts, etc.).

Usage (invoked by main.nf):
    python3 002_ai-python-count-orthogroups_orthohmm.py \\
        --species-order <path/to/1-output/1_ai-species70_alphabetical_phylonames.tsv> \\
        --orthogroups-dir <path/to/orthogroups/output_to_input/BLOCK_orthohmm> \\
        --output-dir 2-output
"""

import argparse
import logging
import sys
from pathlib import Path


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


def extract_genus_species_from_phyloname( phyloname ):
    """Extract genus_species from a phyloname (parts[5:] joined)."""
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) < 7:
        raise ValueError( f'phyloname has fewer than 7 underscore-separated fields: {phyloname}' )
    return '_'.join( parts_phyloname[ 5: ] )


def parse_g_header( header_content ):
    """Parse a >g_ header (or token without the leading >) into (gene_id, protein_id, phyloname).

    Format: g_<gene_id>-t_<transcript_id>-p_<protein_id>-n_<phyloname>
    """
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
        description = 'Count orthogroups per species from BLOCK_orthohmm output'
    )
    parser.add_argument(
        '--workflow-root',
        required = True,
        help = 'Absolute path to the workflow directory (main.nf passes ${projectDir}/..); relative --orthogroups-dir is resolved against this'
    )
    parser.add_argument(
        '--species-order',
        required = True,
        help = 'Path to script 001 output (1_ai-species70_alphabetical_phylonames.tsv)'
    )
    parser.add_argument(
        '--orthogroups-dir',
        required = True,
        help = 'Path to orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC (contains gene_count_gigantic_ids.tsv)'
    )
    parser.add_argument(
        '--output-dir',
        required = True,
        help = 'Output directory (2-output)'
    )
    return parser.parse_args()


def setup_logging( output_dir ):
    log_path = Path( output_dir ) / '2_ai-log-count-orthogroups_orthohmm.log'
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = logging.getLogger( 'count_orthogroups_orthohmm' )
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


def main():
    args = parse_arguments()
    output_dir = Path( args.output_dir )

    logger = setup_logging( output_dir )

    logger.info( '====================================================================' )
    logger.info( 'GIGANTIC homolog_counts Script 002: Count orthogroups from BLOCK_orthohmm' )
    logger.info( '====================================================================' )
    logger.info( f'Input species order:    {args.species_order}' )
    logger.info( f'Input orthogroups dir:  {args.orthogroups_dir}' )
    logger.info( f'Output directory:       {output_dir}' )
    logger.info( '' )

    # ========================================================================
    # Read canonical species order from script 001 output
    # ========================================================================
    # Column_Index (...)	Phyloname (...)	Genus_Species (...)	Phyloname_Taxonid (...)
    # 1	Kingdom10919_Phylum10918_Ichthyosporea_Ichthyophonida_Family10931_Abeoforma_whisleri	Abeoforma_whisleri	Kingdom10919_..._Abeoforma_whisleri___749232

    input_species_order_path = Path( args.species_order )
    if not input_species_order_path.exists():
        logger.error( 'CRITICAL ERROR: species order file not found' )
        logger.error( f'Expected at: {input_species_order_path}' )
        logger.error( 'Script 001 must run successfully before script 002.' )
        sys.exit( 1 )

    canonical_phylonames_in_order = []
    genus_species___phyloname = {}
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
                logger.error( f'Line: {line}' )
                sys.exit( 1 )

            phyloname = parts[ 1 ].strip()
            genus_species = parts[ 2 ].strip()

            canonical_phylonames_in_order.append( phyloname )
            genus_species___phyloname[ genus_species ] = phyloname

    species70_count = len( canonical_phylonames_in_order )
    if species70_count != 70:
        logger.error( f'CRITICAL ERROR: expected 70 species in species_order, got {species70_count}' )
        sys.exit( 1 )

    logger.info( f'[OK] Read {species70_count} species from canonical species order' )

    # ========================================================================
    # Locate upstream gene_count file
    # ========================================================================

    input_orthogroups_dir = resolve_against_workflow_root( args.orthogroups_dir, args.workflow_root )
    input_gene_count_path = input_orthogroups_dir / 'gene_count_gigantic_ids.tsv'
    input_orthogroups_membership_path = input_orthogroups_dir / 'orthogroups_gigantic_ids.tsv'

    if not input_gene_count_path.exists():
        logger.error( 'CRITICAL ERROR: orthohmm gene_count file not found' )
        logger.error( f'Expected at: {input_gene_count_path}' )
        logger.error( 'Run BLOCK_orthohmm first; verify its output_to_input/ is populated.' )
        sys.exit( 1 )

    if not input_orthogroups_membership_path.exists():
        logger.error( 'CRITICAL ERROR: orthohmm orthogroups membership file not found' )
        logger.error( f'Expected at: {input_orthogroups_membership_path}' )
        logger.error( 'Needed for human/phylum identifier columns. Run BLOCK_orthohmm first.' )
        sys.exit( 1 )

    logger.info( f'[OK] Found upstream gene_count:   {input_gene_count_path}' )
    logger.info( f'[OK] Found upstream orthogroups:  {input_orthogroups_membership_path}' )

    # ========================================================================
    # Read upstream gene_count file
    # ========================================================================
    # files: Bolinopsis_microptera.pep Monosiga_brevicollis_MX1.pep Lissachatina_fulica.pep ...
    # OG000000: 92 0 282 93 255 0 23 268 0 20 146 213 170 140 0 162 398 145 152 667 ...
    #
    # NOTE: this file is WHITESPACE-delimited (not tab), inherited from
    # OrthoFinder/OrthoHMM native format. Species columns: <genus_species>.pep
    # Each data row: <orthogroup_id>: followed by per-species integer counts.

    upstream_genus_species_in_order = []
    orthogroup_count = 0
    output_rows = []
    line_number = 0
    header_seen = False
    upstream_to_canonical_index = None

    with open( input_gene_count_path, 'r' ) as input_gene_count, \
         open( input_orthogroups_membership_path, 'r' ) as input_orthogroups_membership:
        for line in input_gene_count:
            line = line.strip()
            line_number += 1

            if not line:
                continue

            parts = line.split()

            if not header_seen:
                # Header: "files: <gs1>.pep <gs2>.pep ..."
                if not parts or parts[ 0 ].rstrip( ':' ) != 'files':
                    logger.error( f'CRITICAL ERROR: unexpected header on line {line_number}' )
                    logger.error( f'Expected first token to be "files:", got: {parts[ :3 ] if parts else "empty"}' )
                    sys.exit( 1 )

                upstream_species_tokens = parts[ 1: ]

                for token in upstream_species_tokens:
                    if not token.endswith( '.pep' ):
                        logger.error( f'CRITICAL ERROR: upstream species column does not end with ".pep": {token}' )
                        sys.exit( 1 )
                    parts_token = token.rsplit( '.', 1 )
                    genus_species = parts_token[ 0 ]
                    upstream_genus_species_in_order.append( genus_species )

                upstream_species_count = len( upstream_genus_species_in_order )
                logger.info( f'Upstream species count: {upstream_species_count}' )

                # ----------------------------------------------------------------
                # FAIL-FAST: species count must equal 70
                # ----------------------------------------------------------------

                if upstream_species_count != 70:
                    logger.error( f'CRITICAL ERROR: upstream orthohmm output has {upstream_species_count} species, expected 70 (species70).' )
                    logger.error( 'The orthohmm run that produced this output_to_input/ was NOT run on the species70 set.' )
                    logger.error( f'Upstream species: {sorted( upstream_genus_species_in_order )}' )
                    logger.error( f'Either re-run BLOCK_orthohmm on species70, or update inputs.species70_phyloname_map to match.' )
                    sys.exit( 1 )

                # ----------------------------------------------------------------
                # FAIL-FAST: species SET must match species70 exactly
                # ----------------------------------------------------------------

                canonical_genus_species_set = set( genus_species___phyloname.keys() )
                upstream_genus_species_set = set( upstream_genus_species_in_order )

                if canonical_genus_species_set != upstream_genus_species_set:
                    missing_in_upstream = canonical_genus_species_set - upstream_genus_species_set
                    extra_in_upstream = upstream_genus_species_set - canonical_genus_species_set
                    logger.error( 'CRITICAL ERROR: upstream orthohmm species set does NOT match species70 manifest.' )
                    if missing_in_upstream:
                        logger.error( f'In species70 manifest but missing from orthohmm output ({len( missing_in_upstream )}):' )
                        for species_name in sorted( missing_in_upstream ):
                            logger.error( f'    - {species_name}' )
                    if extra_in_upstream:
                        logger.error( f'In orthohmm output but NOT in species70 manifest ({len( extra_in_upstream )}):' )
                        for species_name in sorted( extra_in_upstream ):
                            logger.error( f'    - {species_name}' )
                    logger.error( 'Re-run BLOCK_orthohmm on the species70 set, or update inputs.species70_phyloname_map.' )
                    sys.exit( 1 )

                logger.info( '[OK] Upstream species set matches species70 manifest exactly' )

                # ----------------------------------------------------------------
                # Build permutation: upstream column index -> canonical column index
                # ----------------------------------------------------------------

                upstream_to_canonical_index = []
                canonical_phyloname___canonical_index = {
                    phyloname: index for index, phyloname in enumerate( canonical_phylonames_in_order )
                }
                for upstream_genus_species in upstream_genus_species_in_order:
                    canonical_phyloname = genus_species___phyloname[ upstream_genus_species ]
                    canonical_index = canonical_phyloname___canonical_index[ canonical_phyloname ]
                    upstream_to_canonical_index.append( canonical_index )

                logger.info( '[OK] Built upstream -> canonical column index permutation' )

                header_seen = True
                continue

            # ----------------------------------------------------------------
            # Data row: "<OG_ID>: <count_1> <count_2> ... <count_70>"
            # ----------------------------------------------------------------

            orthogroup_token = parts[ 0 ]
            if not orthogroup_token.endswith( ':' ):
                logger.error( f'CRITICAL ERROR: data row {line_number} first token does not end with ":": {orthogroup_token}' )
                sys.exit( 1 )
            orthogroup_id = orthogroup_token.rstrip( ':' )

            count_tokens = parts[ 1: ]
            if len( count_tokens ) != 70:
                logger.error( f'CRITICAL ERROR: data row {line_number} has {len( count_tokens )} count columns, expected 70' )
                logger.error( f'Orthogroup: {orthogroup_id}' )
                sys.exit( 1 )

            # Parse counts as integers (fail-fast on non-integer)
            try:
                upstream_counts = [ int( token ) for token in count_tokens ]
            except ValueError as parse_error:
                logger.error( f'CRITICAL ERROR: non-integer count on data row {line_number}: {parse_error}' )
                logger.error( f'Orthogroup: {orthogroup_id}' )
                logger.error( f'Tokens: {count_tokens[ :10 ]}...' )
                sys.exit( 1 )

            # Permute to canonical order
            canonical_counts = [ 0 ] * 70
            for upstream_index, count in enumerate( upstream_counts ):
                canonical_index = upstream_to_canonical_index[ upstream_index ]
                canonical_counts[ canonical_index ] = count

            total_count = sum( canonical_counts )
            total_species_count = sum( 1 for count in canonical_counts if count >= 1 )

            # ----------------------------------------------------------------
            # Read corresponding line from orthogroups membership file and
            # compute the 5 extra columns (human gene names + 4 phylum lists)
            # ----------------------------------------------------------------
            # orthogroups_gigantic_ids.tsv format (NO header row):
            #   OG000000<TAB>g_<id>-t_<tid>-p_<pid>-n_<phyloname><TAB>...<TAB>g_...
            # OG IDs appear in the SAME order as the gene_count file's data rows.

            try:
                membership_line = next( input_orthogroups_membership )
            except StopIteration:
                logger.error( f'CRITICAL ERROR: orthogroups membership file ended before gene_count at {orthogroup_id}' )
                sys.exit( 1 )

            membership_line = membership_line.rstrip( '\n' )
            membership_parts = membership_line.split( '\t' )
            if not membership_parts:
                logger.error( f'CRITICAL ERROR: empty orthogroups membership row at {orthogroup_id}' )
                sys.exit( 1 )

            membership_og_id = membership_parts[ 0 ]
            if membership_og_id != orthogroup_id:
                logger.error( f'CRITICAL ERROR: orthogroups OG order mismatch.' )
                logger.error( f'  gene_count OG_ID:    {orthogroup_id}' )
                logger.error( f'  orthogroups OG_ID:   {membership_og_id}' )
                logger.error( '  Both files must be from the same BLOCK_orthohmm run with matching row order.' )
                sys.exit( 1 )

            human_gene_names_seen = set()
            human_gene_names_order = []
            phylum___gene_ids = { phylum: [] for phylum in PHYLUM_LIST_ORDER }

            for token in membership_parts[ 1: ]:
                try:
                    gene_id, _, token_phyloname = parse_g_header( token )
                except ValueError as parse_error:
                    logger.error( f'CRITICAL ERROR: malformed gene token in orthogroup {orthogroup_id}' )
                    logger.error( f'  Token: {token}' )
                    logger.error( f'  Error: {parse_error}' )
                    sys.exit( 1 )

                try:
                    token_genus_species = extract_genus_species_from_phyloname( token_phyloname )
                except ValueError as parse_error:
                    logger.error( f'CRITICAL ERROR: cannot extract genus_species from token phyloname in orthogroup {orthogroup_id}' )
                    logger.error( f'  Token: {token}' )
                    logger.error( f'  Error: {parse_error}' )
                    sys.exit( 1 )

                if token_genus_species == 'Homo_sapiens':
                    if gene_id not in human_gene_names_seen:
                        human_gene_names_seen.add( gene_id )
                        human_gene_names_order.append( gene_id )

                phylum = GENUS_SPECIES___PHYLUM_OF_INTEREST.get( token_genus_species )
                if phylum is not None:
                    phylum___gene_ids[ phylum ].append( gene_id )

            human_gene_names_column = ';'.join( human_gene_names_order )
            phylum_columns = [ ';'.join( phylum___gene_ids[ phylum ] ) for phylum in PHYLUM_LIST_ORDER ]

            output_rows.append( (
                orthogroup_id,
                total_count,
                total_species_count,
                canonical_counts,
                human_gene_names_column,
                phylum_columns,
            ) )
            orthogroup_count += 1

    logger.info( f'[OK] Read {orthogroup_count} orthogroups from upstream' )

    if orthogroup_count == 0:
        logger.error( 'CRITICAL ERROR: zero orthogroups read from upstream gene_count file.' )
        logger.error( f'File: {input_gene_count_path}' )
        sys.exit( 1 )

    # ========================================================================
    # Write output TSV
    # ========================================================================
    # Headers follow GIGANTIC self-documenting convention: Header_ID (description)
    # Per-species columns use the full phyloname + count description (option c).

    output_counts_path = output_dir / '2_ai-counts-orthogroups_orthohmm.tsv'

    header_parts = [
        'Feature_ID (orthogroup ID from OrthoHMM BLOCK_orthohmm output)',
        'Total_Count (sum of gene counts across all 70 species in this orthogroup)',
        'Total_Species_Count (number of species with at least 1 gene in this orthogroup)',
    ]
    for phyloname in canonical_phylonames_in_order:
        header_parts.append( f'{phyloname} (gene count for this species in this orthogroup)' )

    header_parts.extend( [
        'Human_Gene_Names_List (semicolon delimited list of gene_id values from >g_*-Homo_sapiens entries in this orthogroup; deduplicated)',
        'Ctenophore_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<ctenophore species> entries in this orthogroup; species: Beroe_ovata, Hormiphora_californensis, Pleurobrachia_bachei, Bolinopsis_microptera, Mnemiopsis_leidyi)',
        'Sponge_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<sponge species> entries in this orthogroup; species: Sycon_ciliatum, Chondrosia_reniformis, Dysidea_avara, Ephydatia_muelleri, Halichondria_panicea, Oscarella_lobularis, Corticium_candelabrum)',
        'Placozoan_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<placozoan species> entries in this orthogroup; species: Cladtertia_collaboinventa, Trichoplax_adhaerens, Trichoplax_sp_H2, Hoilungia_hongkongensis_H13)',
        'Cnidarian_Sequence_IDs_List (semicolon delimited list of gene_id values from >g_*-<cnidarian species> entries in this orthogroup; species: Nematostella_vectensis, Acropora_muricata, Pocillopora_verrucosa, Hydractinia_symbiolongicarpus, Hydra_vulgaris)',
    ] )

    output = '\t'.join( header_parts ) + '\n'

    with open( output_counts_path, 'w' ) as output_counts:
        output_counts.write( output )

        for orthogroup_id, total_count, total_species_count, canonical_counts, human_gene_names_column, phylum_columns in output_rows:
            row_parts = [ orthogroup_id, str( total_count ), str( total_species_count ) ]
            row_parts.extend( str( count ) for count in canonical_counts )
            row_parts.append( human_gene_names_column )
            row_parts.extend( phylum_columns )
            output = '\t'.join( row_parts ) + '\n'
            output_counts.write( output )

    logger.info( '' )
    logger.info( f'[OK] Wrote count table to: {output_counts_path}' )
    logger.info( f'     Rows: {orthogroup_count} (excluding header)' )
    logger.info( f'     Columns: 3 summary + 70 species + 5 extra = 78' )

    # ========================================================================
    # Summary stats
    # ========================================================================

    total_genes = sum( row[ 1 ] for row in output_rows )
    orthogroups_singleton = sum( 1 for row in output_rows if row[ 2 ] == 1 )
    orthogroups_universal = sum( 1 for row in output_rows if row[ 2 ] == 70 )

    logger.info( '' )
    logger.info( 'Summary:' )
    logger.info( f'  Total orthogroups:                      {orthogroup_count}' )
    logger.info( f'  Total gene memberships (sum of counts): {total_genes}' )
    logger.info( f'  Orthogroups present in only 1 species:  {orthogroups_singleton}' )
    logger.info( f'  Orthogroups present in all 70 species:  {orthogroups_universal}' )

    logger.info( '' )
    logger.info( '====================================================================' )
    logger.info( 'Script 002 complete: orthogroups counts re-keyed to species70 canonical order.' )
    logger.info( '====================================================================' )


if __name__ == '__main__':
    main()
