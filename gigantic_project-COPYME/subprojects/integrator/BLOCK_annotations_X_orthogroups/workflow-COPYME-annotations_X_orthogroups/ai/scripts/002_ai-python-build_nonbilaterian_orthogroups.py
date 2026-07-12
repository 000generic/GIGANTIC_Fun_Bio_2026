#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Build Table 2 — qualifying orthogroups (non-bilaterian metazoan, no bilaterians)
# Human: Eric Edsinger

"""
Script 002 — Table 2: qualifying orthogroups.

Reads the orthogroup species-composition classification (Script 001, 1-output)
and keeps the orthogroups classified non_bilaterian_metazoan — orthogroups with
ZERO bilaterian members AND at least one non-bilaterian metazoan member (sponge,
cnidarian, ctenophore, placozoan). Non-metazoan / unicellular outgroup members
may ride along; orthogroups made of only non-metazoan unicells do NOT qualify.

One row per kept orthogroup. Fail-fast: exits 1 if the composition table is
missing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_integrator as U

QUALIFYING_CLASS = "non_bilaterian_metazoan"


def main():
    parser = argparse.ArgumentParser( description = "Build Table 2 — qualifying (non-bilaterian-metazoan) orthogroups" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    input_composition_path = U.resolve_composition_table_path( Path( args.output_dir ) )
    if not input_composition_path.is_file():
        print( f"CRITICAL ERROR: composition table not found: {input_composition_path}", file = sys.stderr )
        print( "  Script 001 (classify_orthogroups) must run before this script.", file = sys.stderr )
        sys.exit( 1 )

    output_dir = Path( args.output_dir ) / "2-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_table_path = U.timestamped_output_path( output_dir, "2_ai-nonbilaterian_metazoan_orthogroups", Path( args.output_dir ) )

    header_columns = [
        "Orthogroup_ID (orthogroup identifier from the orthogroups subproject)",
        "Member_Protein_Count (number of member protein sequence identifiers in the orthogroup)",
        "Species_Count (number of unique species among the member proteins)",
        "NonBilaterian_Metazoan_Species_Count (count of member species in Metazoa but not in Bilateria; at least one for a qualifying orthogroup)",
        "NonMetazoan_Species_Count (count of member species not in Metazoa; unicellular outgroups that may ride along)",
        "Species_List (comma delimited list of member species as Genus_species; no bilaterians)",
    ]

    kept_count = 0
    total_count = 0
    with open( input_composition_path, 'r' ) as input_composition, \
         open( output_table_path, 'w' ) as output_table:
        output_table.write( '\t'.join( header_columns ) + '\n' )

        # Orthogroup_ID (...)\tMember_Protein_Count (...)\tSpecies_Count (...)\tBilaterian_Species_Count (...)\tNonBilaterian_Metazoan_Species_Count (...)\tNonMetazoan_Species_Count (...)\tComposition_Class (...)\tQualifies_NonBilaterian_Metazoan (...)\tSpecies_List (...)
        # OG000123\t44\t6\t0\t6\t0\tnon_bilaterian_metazoan\tyes\tBeroe_ovata,Bolinopsis_microptera,...
        header_line = input_composition.readline()
        header_ids___indices = U.build_header_index( header_line )
        index_og = header_ids___indices[ "Orthogroup_ID" ]
        index_member_count = header_ids___indices[ "Member_Protein_Count" ]
        index_species_count = header_ids___indices[ "Species_Count" ]
        index_non_bilaterian_metazoan = header_ids___indices[ "NonBilaterian_Metazoan_Species_Count" ]
        index_non_metazoan = header_ids___indices[ "NonMetazoan_Species_Count" ]
        index_class = header_ids___indices[ "Composition_Class" ]
        index_species_list = header_ids___indices[ "Species_List" ]

        for line in input_composition:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            total_count += 1
            if parts[ index_class ] != QUALIFYING_CLASS:
                continue

            output = '\t'.join( [
                parts[ index_og ],
                parts[ index_member_count ],
                parts[ index_species_count ],
                parts[ index_non_bilaterian_metazoan ],
                parts[ index_non_metazoan ],
                parts[ index_species_list ],
            ] ) + '\n'
            output_table.write( output )
            kept_count += 1

    print( f"[002] qualifying (non-bilaterian-metazoan) orthogroups: {kept_count} of {total_count} -> {output_table_path}" )


if __name__ == '__main__':
    main()
