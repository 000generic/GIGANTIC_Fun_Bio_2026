#!/usr/bin/env python3
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Validate proteome manifest for MetaPredict workflow
# Human: Eric Edsinger

"""
001_ai-python-validate_proteome_manifest.py

Validates the input proteome manifest TSV file for the MetaPredict disorder
prediction workflow. Checks that all listed proteome files exist, are non-empty,
and contain valid FASTA sequences. Outputs a validated manifest with sequence
counts appended.

Input:
    --manifest-path: Path to proteome_manifest.tsv (tab-separated)
        Expected columns:
        - species_name (identifier for the species)
        - proteome_path (path to the proteome FASTA file)
        - phyloname (GIGANTIC phyloname)

Output:
    1_ai-validated_manifest.tsv
        Tab-separated file with columns:
        - Species_Name (species identifier from manifest)
        - Proteome_Path (validated absolute path to proteome file)
        - Phyloname (GIGANTIC phyloname from manifest)
        - Sequence_Count (number of protein sequences in the file)

    1_ai-log-validate_proteome_manifest.log

Usage:
    python3 001_ai-python-validate_proteome_manifest.py \\
        --manifest-path INPUT_user/proteome_manifest.tsv \\
        --output-dir .
"""

import argparse
import logging
import sys
from pathlib import Path


def setup_logging( output_directory: Path ) -> logging.Logger:
    """Configure logging to both console and file."""

    logger = logging.getLogger( '001_validate_proteome_manifest' )
    logger.setLevel( logging.DEBUG )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel( logging.INFO )
    console_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    console_handler.setFormatter( console_format )
    logger.addHandler( console_handler )

    # File handler
    log_file = output_directory / '1_ai-log-validate_proteome_manifest.log'
    file_handler = logging.FileHandler( log_file )
    file_handler.setLevel( logging.DEBUG )
    file_format = logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' )
    file_handler.setFormatter( file_format )
    logger.addHandler( file_handler )

    return logger


def count_sequences_in_fasta( fasta_path: Path ) -> int:
    """Count the number of sequences in a FASTA file by counting header lines."""

    sequence_count = 0
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if line.startswith( '>' ):
                sequence_count += 1

    return sequence_count


def validate_manifest( manifest_path: Path, output_directory: Path, logger: logging.Logger ) -> None:
    """
    Validate the proteome manifest and create a validated output manifest
    with sequence counts for each proteome.
    """

    logger.info( f"Validating proteome manifest: {manifest_path}" )

    # =========================================================================
    # Validate manifest file exists
    # =========================================================================

    if not manifest_path.exists():
        logger.error( "CRITICAL ERROR: Manifest file does not exist!" )
        logger.error( f"Expected path: {manifest_path}" )
        logger.error( "Create a proteome_manifest.tsv in INPUT_user/ with columns:" )
        logger.error( "  species_name\\tproteome_path\\tphyloname" )
        sys.exit( 1 )

    if manifest_path.stat().st_size == 0:
        logger.error( "CRITICAL ERROR: Manifest file is empty!" )
        logger.error( f"Path: {manifest_path}" )
        sys.exit( 1 )

    # =========================================================================
    # Read and parse manifest
    # =========================================================================

    validated_records = []
    error_count = 0
    line_number = 0

    with open( manifest_path, 'r' ) as input_manifest:
        # species_name	proteome_path	phyloname
        # Homo_sapiens	/path/to/Homo_sapiens.aa	Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
        for line in input_manifest:
            line = line.strip()
            line_number += 1

            # Skip empty lines and comments
            if not line or line.startswith( '#' ):
                continue

            # Skip header line
            if line_number == 1 and line.lower().startswith( 'species' ):
                logger.info( f"Skipping header line: {line}" )
                continue

            parts = line.split( '\t' )

            if len( parts ) < 3:
                logger.error( f"Line {line_number}: Expected at least 3 tab-separated columns, got {len( parts )}" )
                logger.error( f"Line content: {line}" )
                error_count += 1
                continue

            species_name = parts[ 0 ].strip()
            proteome_path_string = parts[ 1 ].strip()
            phyloname = parts[ 2 ].strip()

            # Validate species name is not empty
            if not species_name:
                logger.error( f"Line {line_number}: Empty species_name" )
                error_count += 1
                continue

            # Validate phyloname is not empty
            if not phyloname:
                logger.error( f"Line {line_number}: Empty phyloname for species {species_name}" )
                error_count += 1
                continue

            # Resolve proteome path
            proteome_path = Path( proteome_path_string )

            # If path is relative, try resolving from manifest directory
            if not proteome_path.is_absolute():
                proteome_path = ( manifest_path.parent / proteome_path ).resolve()

            # Validate proteome file exists
            if not proteome_path.exists():
                logger.error( f"Line {line_number}: Proteome file does not exist for {species_name}" )
                logger.error( f"  Path: {proteome_path}" )
                error_count += 1
                continue

            # Validate proteome file is not empty
            if proteome_path.stat().st_size == 0:
                logger.error( f"Line {line_number}: Proteome file is empty for {species_name}" )
                logger.error( f"  Path: {proteome_path}" )
                error_count += 1
                continue

            # Count sequences
            sequence_count = count_sequences_in_fasta( proteome_path )

            if sequence_count == 0:
                logger.error( f"Line {line_number}: No FASTA sequences found for {species_name}" )
                logger.error( f"  Path: {proteome_path}" )
                logger.error( "  File exists but contains no '>' header lines." )
                error_count += 1
                continue

            logger.debug( f"  {species_name}: {sequence_count} sequences ({phyloname})" )

            validated_records.append( {
                'species_name': species_name,
                'proteome_path': str( proteome_path ),
                'phyloname': phyloname,
                'sequence_count': sequence_count
            } )

    # =========================================================================
    # Check for critical failures
    # =========================================================================

    if error_count > 0:
        logger.error( f"CRITICAL ERROR: {error_count} validation error(s) found in manifest!" )
        logger.error( "Fix the errors above and re-run the pipeline." )
        sys.exit( 1 )

    if len( validated_records ) == 0:
        logger.error( "CRITICAL ERROR: No valid proteome entries found in manifest!" )
        logger.error( f"Manifest path: {manifest_path}" )
        logger.error( "Ensure the manifest has at least one valid species entry." )
        sys.exit( 1 )

    # =========================================================================
    # Calculate totals
    # =========================================================================

    total_sequences = sum( record[ 'sequence_count' ] for record in validated_records )
    logger.info( f"Validated {len( validated_records )} species proteomes" )
    logger.info( f"Total sequences across all proteomes: {total_sequences}" )

    # =========================================================================
    # Write validated manifest
    # =========================================================================

    output_file = output_directory / '1_ai-validated_manifest.tsv'

    with open( output_file, 'w' ) as output_validated_manifest:
        # Write header
        header = 'Species_Name (species identifier from manifest)' + '\t'
        header += 'Proteome_Path (validated absolute path to proteome file)' + '\t'
        header += 'Phyloname (GIGANTIC phyloname from manifest)' + '\t'
        header += 'Sequence_Count (number of protein sequences in file)' + '\n'
        output_validated_manifest.write( header )

        # Write data rows
        for record in validated_records:
            output = record[ 'species_name' ] + '\t'
            output += record[ 'proteome_path' ] + '\t'
            output += record[ 'phyloname' ] + '\t'
            output += str( record[ 'sequence_count' ] ) + '\n'
            output_validated_manifest.write( output )

    logger.info( f"Wrote validated manifest to: {output_file}" )

    # =========================================================================
    # Summary
    # =========================================================================

    logger.info( "" )
    logger.info( "========================================" )
    logger.info( "Script 001 completed successfully" )
    logger.info( "========================================" )
    logger.info( f"  Species count: {len( validated_records )}" )
    logger.info( f"  Total sequences: {total_sequences}" )
    logger.info( f"  Output file: {output_file}" )


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description = 'Validate proteome manifest for MetaPredict disorder prediction workflow'
    )

    parser.add_argument(
        '--manifest-path',
        type = str,
        required = True,
        help = 'Path to proteome_manifest.tsv (tab-separated with species_name, proteome_path, phyloname)'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = 'OUTPUT_pipeline/1-output',
        help = 'Output directory (default: OUTPUT_pipeline/1-output)'
    )

    arguments = parser.parse_args()

    # Convert to Path objects
    manifest_path = Path( arguments.manifest_path )
    output_directory = Path( arguments.output_dir )

    # Create output directory
    output_directory.mkdir( parents = True, exist_ok = True )

    # Setup logging
    logger = setup_logging( output_directory )

    logger.info( "=" * 70 )
    logger.info( "Script 001: Validate Proteome Manifest" )
    logger.info( "=" * 70 )

    # Run validation
    validate_manifest( manifest_path, output_directory, logger )


if __name__ == '__main__':
    main()
