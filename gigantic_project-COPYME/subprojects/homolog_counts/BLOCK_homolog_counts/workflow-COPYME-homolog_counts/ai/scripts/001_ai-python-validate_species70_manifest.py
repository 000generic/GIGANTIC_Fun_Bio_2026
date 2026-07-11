#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 20 | Purpose: Validate species70 manifest and emit canonical alphabetical phyloname column order
# Human: Eric Edsinger

"""
GIGANTIC homolog_counts - Script 001: Validate species70 manifest

Reads the canonical species70 phyloname map and produces:

  1. 1-output/1_ai-species70_alphabetical_phylonames.tsv
     The canonical species column order used by ALL downstream count scripts
     (002, 003, 004). Sorted alphabetically by phyloname.

  2. 1-output/1_ai-log-validate_species70_manifest.log
     Validation log.

Fail-fast: exits with code 1 on any validation error.

Usage (invoked by main.nf):
    python3 001_ai-python-validate_species70_manifest.py \\
        --phyloname-map <path/to/species70_map-genus_species_X_phylonames.tsv> \\
        --output-dir 1-output
"""

import argparse
import logging
import sys
from pathlib import Path


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
        description = 'Validate species70 manifest and emit canonical phyloname column order'
    )
    parser.add_argument(
        '--workflow-root',
        required = True,
        help = 'Absolute path to the workflow directory (main.nf passes ${projectDir}/..); relative --phyloname-map is resolved against this'
    )
    parser.add_argument(
        '--phyloname-map',
        required = True,
        help = 'Path to species70 phyloname map TSV (columns: genus_species | phyloname | phyloname_taxonid)'
    )
    parser.add_argument(
        '--output-dir',
        required = True,
        help = 'Output directory (1-output)'
    )
    return parser.parse_args()


def setup_logging( output_dir ):
    log_path = Path( output_dir ) / '1_ai-log-validate_species70_manifest.log'
    log_path.parent.mkdir( parents = True, exist_ok = True )

    logger = logging.getLogger( 'validate_species70_manifest' )
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
    logger.info( 'GIGANTIC homolog_counts Script 001: Validate species70 manifest' )
    logger.info( '====================================================================' )
    logger.info( f'Input phyloname map: {args.phyloname_map}' )
    logger.info( f'Output directory:    {output_dir}' )
    logger.info( '' )

    # ========================================================================
    # Validate input file exists
    # ========================================================================

    input_phyloname_map_path = resolve_against_workflow_root( args.phyloname_map, args.workflow_root )
    if not input_phyloname_map_path.exists():
        logger.error( 'CRITICAL ERROR: phyloname map file not found' )
        logger.error( f'Expected at: {input_phyloname_map_path}' )
        logger.error( 'Set inputs.species70_phyloname_map in START_HERE-user_config.yaml.' )
        sys.exit( 1 )

    # ========================================================================
    # Read input file
    # ========================================================================
    # genus_species	phyloname	phyloname_taxonid
    # Abeoforma_whisleri	Kingdom10919_Phylum10918_Ichthyosporea_Ichthyophonida_Family10931_Abeoforma_whisleri	Kingdom10919_Phylum10918_Ichthyosporea_Ichthyophonida_Family10931_Abeoforma_whisleri___749232

    phylonames___records = {}
    genus_species_values = []
    line_number = 0
    header_seen = False

    with open( input_phyloname_map_path, 'r' ) as input_phyloname_map:
        for line in input_phyloname_map:
            line = line.strip()
            line_number += 1

            if not line:
                continue
            if line.startswith( '#' ):
                continue

            parts = line.split( '\t' )

            if not header_seen:
                if len( parts ) < 3:
                    logger.error( f'CRITICAL ERROR: header has fewer than 3 columns (got {len( parts )})' )
                    logger.error( f'Line {line_number}: {line}' )
                    logger.error( 'Expected: genus_species<TAB>phyloname<TAB>phyloname_taxonid' )
                    sys.exit( 1 )
                logger.info( f'Header columns: {parts[ :3 ]}' )
                header_seen = True
                continue

            if len( parts ) < 3:
                logger.error( f'CRITICAL ERROR: data row has fewer than 3 columns (got {len( parts )})' )
                logger.error( f'Line {line_number}: {line}' )
                sys.exit( 1 )

            genus_species = parts[ 0 ].strip()
            phyloname = parts[ 1 ].strip()
            phyloname_taxonid = parts[ 2 ].strip()

            if not genus_species or not phyloname or not phyloname_taxonid:
                logger.error( f'CRITICAL ERROR: empty field on line {line_number}' )
                logger.error( f'  genus_species     = {repr( genus_species )}' )
                logger.error( f'  phyloname         = {repr( phyloname )}' )
                logger.error( f'  phyloname_taxonid = {repr( phyloname_taxonid )}' )
                sys.exit( 1 )

            # Validate phyloname structure: must have >= 7 underscore-separated
            # fields per GIGANTIC convention (Kingdom_Phylum_Class_Order_Family_Genus_species)
            parts_phyloname = phyloname.split( '_' )
            if len( parts_phyloname ) < 7:
                logger.error( f'CRITICAL ERROR: phyloname has fewer than 7 underscore-separated fields on line {line_number}' )
                logger.error( f'  phyloname: {phyloname}' )
                logger.error( f'  fields:    {parts_phyloname}' )
                sys.exit( 1 )

            if phyloname in phylonames___records:
                logger.error( f'CRITICAL ERROR: duplicate phyloname on line {line_number}: {phyloname}' )
                sys.exit( 1 )

            if genus_species in genus_species_values:
                logger.error( f'CRITICAL ERROR: duplicate genus_species on line {line_number}: {genus_species}' )
                sys.exit( 1 )

            phylonames___records[ phyloname ] = {
                'genus_species': genus_species,
                'phyloname_taxonid': phyloname_taxonid,
            }
            genus_species_values.append( genus_species )

    species_count = len( phylonames___records )
    logger.info( f'Species rows read: {species_count}' )

    # ========================================================================
    # Validate species count == 70
    # ========================================================================

    if species_count != 70:
        logger.error( f'CRITICAL ERROR: expected exactly 70 species, got {species_count}' )
        logger.error( 'species70 is the canonical GIGANTIC species set; deviating breaks downstream column order.' )
        logger.error( 'Verify inputs.species70_phyloname_map in START_HERE-user_config.yaml points to the canonical species70 manifest.' )
        sys.exit( 1 )

    logger.info( '[OK] Species count == 70' )
    logger.info( '[OK] No duplicate phylonames' )
    logger.info( '[OK] No duplicate genus_species' )
    logger.info( '[OK] All phylonames have >= 7 underscore-separated fields' )

    # ========================================================================
    # Sort alphabetically by phyloname (canonical column order)
    # ========================================================================

    phylonames_sorted = sorted( phylonames___records.keys() )

    logger.info( '' )
    logger.info( 'Canonical alphabetical species70 column order (first 5):' )
    for column_index, phyloname in enumerate( phylonames_sorted[ :5 ], start = 1 ):
        genus_species = phylonames___records[ phyloname ][ 'genus_species' ]
        logger.info( f'  [{column_index:2d}] {genus_species}' )
    logger.info( '  ...' )
    logger.info( 'Canonical alphabetical species70 column order (last 5):' )
    for offset, phyloname in enumerate( phylonames_sorted[ -5: ], start = 0 ):
        column_index = species_count - 4 + offset
        genus_species = phylonames___records[ phyloname ][ 'genus_species' ]
        logger.info( f'  [{column_index:2d}] {genus_species}' )

    # ========================================================================
    # Write canonical species order TSV
    # ========================================================================
    # Headers follow GIGANTIC self-documenting convention: Header_ID (description)

    output_species_order_path = output_dir / '1_ai-species70_alphabetical_phylonames.tsv'

    header_parts = [
        'Column_Index (1-based position in the canonical species70 alphabetical phyloname order; matches species column position in downstream count TSVs)',
        'Phyloname (full GIGANTIC phylogenetic name; canonical column header used in downstream count TSVs; this column is sorted alphabetically)',
        'Genus_Species (binomial format Genus_species; for matching against upstream subproject outputs keyed on genus_species)',
        'Phyloname_Taxonid (phyloname suffixed with NCBI taxonomy ID after a triple underscore)',
    ]
    output = '\t'.join( header_parts ) + '\n'

    with open( output_species_order_path, 'w' ) as output_species_order:
        output_species_order.write( output )

        for column_index, phyloname in enumerate( phylonames_sorted, start = 1 ):
            record = phylonames___records[ phyloname ]
            output = '\t'.join( [
                str( column_index ),
                phyloname,
                record[ 'genus_species' ],
                record[ 'phyloname_taxonid' ],
            ] ) + '\n'
            output_species_order.write( output )

    logger.info( '' )
    logger.info( f'[OK] Wrote canonical species order to: {output_species_order_path}' )
    logger.info( f'     Rows: {species_count} (excluding header)' )
    logger.info( f'     Columns: 4 (Column_Index, Phyloname, Genus_Species, Phyloname_Taxonid)' )

    # ========================================================================
    # Done
    # ========================================================================

    logger.info( '' )
    logger.info( '====================================================================' )
    logger.info( 'Script 001 complete: species70 manifest validated and canonical column order emitted.' )
    logger.info( '====================================================================' )


if __name__ == '__main__':
    main()
