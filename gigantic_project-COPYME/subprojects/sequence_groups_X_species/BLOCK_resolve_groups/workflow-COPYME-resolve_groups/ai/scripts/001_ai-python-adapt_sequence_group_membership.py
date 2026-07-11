# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Adapt a producer's native group output into the STANDARD sequence-group membership (SequenceGroup_ID, Sequence_Identifier, Genus_Species)
# Human: Eric Edsinger

"""
Script 001 — Adapt a producer's sequence-group set into the standard membership.

This subproject resolves ANY "sequence group" onto the species-tree clades. The one
producer-specific step is reading the group set's native output into a single
STANDARD membership table; every downstream script (deconvolution, per-species map,
composite clades) reads only that standard table, so they are producer-agnostic.

Standard membership (1-output/1_ai-<group_set_label>-sequence_group_membership.tsv):
    SequenceGroup_ID  Sequence_Identifier  Genus_Species
one row per (member sequence, group).

Producers (config 'producer'):
  - orthogroups : reads orthogroups_gigantic_ids.tsv, a row per orthogroup
        OG_id <TAB> member_seq_id <TAB> member_seq_id <TAB> ...
    where each member id embeds its phyloname after '-n_' (Genus_species parsed
    from there). Adding a producer = add a small reader branch here; nothing
    downstream changes.

Fail-fast (§36): exits 1 if the input is missing, the producer is unknown, the
output is empty, or any member id has no parseable Genus_species (silent loss).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U


def read_orthogroups( producer_membership_path: Path ):
    """
    Yield ( sequence_group_id, sequence_identifier, genus_species ) from an
    orthogroups_gigantic_ids.tsv (one orthogroup per line; members tab-delimited
    after the orthogroup id; Genus_species parsed from each member's '-n_<phyloname>').
    """
    # OG000000	g_..-n_<phyloname>	g_..-n_<phyloname>	...
    # OG000001	g_..-n_<phyloname>	...
    with open( producer_membership_path, 'r' ) as input_membership:
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_group_id = parts[ 0 ]
            for sequence_identifier in parts[ 1: ]:
                sequence_identifier = sequence_identifier.strip()
                if not sequence_identifier:
                    continue
                genus_species = U.genus_species_from_full_id( sequence_identifier )
                yield ( sequence_group_id, sequence_identifier, genus_species )


def read_annogroups( producer_membership_path: Path ):
    """
    Yield ( sequence_group_id, sequence_identifier, genus_species ) from an annogroups
    membership table (2_ai-<source>-annogroup_membership.tsv): one row per (sequence,
    annogroup), with Genus_Species already a column. The annogroup id is the
    SequenceGroup_ID. All annogroup types pass through (including the single 'absent'
    annogroup); filter downstream if a particular analysis wants only origin-bearing types.
    """
    # Sequence_Identifier (...)	Genus_Species (...)	Annogroup_ID (...)	Annogroup_Type (...)	...
    with open( producer_membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_genus_species = header_ids___indices[ "Genus_Species" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            yield ( parts[ index_annogroup ], parts[ index_sequence ], parts[ index_genus_species ] )


def read_gene_families( producer_membership_path: Path ):
    """
    Yield ( sequence_group_id, sequence_identifier, genus_species ) from a directory of
    per-family AGS (All Gene Set) FASTAs. producer_membership_path is the root holding
    one AGS FASTA per gene family; the family name is the SequenceGroup_ID and each
    FASTA header (a full GIGANTIC id) is a member (Genus_species parsed from its
    '-n_<phyloname>'). AGS files are matched as '<family>/**/16_ai-ags-*.aa'.
    """
    root = Path( producer_membership_path )
    ags_files = sorted( root.glob( "**/16_ai-ags-*.aa" ) )
    for ags_file in ags_files:
        # Family name: the FASTA's own descriptor (16_ai-ags-<family>.aa) or its top dir.
        family_token = ags_file.stem.replace( "16_ai-ags-", "" )
        sequence_group_id = family_token if family_token else ags_file.parent.name
        with open( ags_file, 'r' ) as input_fasta:
            for line in input_fasta:
                if not line.startswith( '>' ):
                    continue
                sequence_identifier = line[ 1: ].strip().split()[ 0 ]
                genus_species = U.genus_species_from_full_id( sequence_identifier )
                if not genus_species:
                    continue   # RGS reference seed (no -n_<phyloname>) -- not a species-tree member
                yield ( sequence_group_id, sequence_identifier, genus_species )


def read_gene_groups( producer_membership_path: Path ):
    """
    Yield ( sequence_group_id, sequence_identifier, genus_species ) from ONE gene-groups
    instance's homolog-discovery tree (e.g. gene_groups-hugo_hgnc, gene_groups-snap_family).

    producer_membership_path is the instance root; under it each gene group lives in its
    own 'gene_group-<name>/' directory holding an AGS (All Gene Set) FASTA. The gene-group
    name (from the enclosing 'gene_group-<name>' directory) is the SequenceGroup_ID; each
    FASTA header (a full GIGANTIC id) is a member (Genus_species parsed from its
    '-n_<phyloname>'). AGS files are matched as
    '<instance>/**/gene_group-<name>/**/16_ai-ags-*.aa'.

    This is deliberately its own reader (not shared with read_gene_families): gene groups
    carry the extra 'gene_group-<name>/' wrapper directory that names the group, and the
    two producers are separate subprojects whose input layouts are allowed to diverge.
    """
    root = Path( producer_membership_path )
    ags_files = sorted( root.glob( "**/gene_group-*/**/16_ai-ags-*.aa" ) )
    for ags_file in ags_files:
        # The gene-group name is the enclosing 'gene_group-<name>' directory (stable even
        # if the AGS filename convention changes); fall back to the AGS's own descriptor.
        sequence_group_id = ""
        for parent in ags_file.parents:
            if parent.name.startswith( "gene_group-" ):
                sequence_group_id = parent.name[ len( "gene_group-" ): ]
                break
        if not sequence_group_id:
            sequence_group_id = ags_file.stem.replace( "16_ai-ags-", "" )
        with open( ags_file, 'r' ) as input_fasta:
            for line in input_fasta:
                if not line.startswith( '>' ):
                    continue
                sequence_identifier = line[ 1: ].strip().split()[ 0 ]
                genus_species = U.genus_species_from_full_id( sequence_identifier )
                if not genus_species:
                    continue   # RGS reference seed (no -n_<phyloname>) -- not a species-tree member
                yield ( sequence_group_id, sequence_identifier, genus_species )


PRODUCER_READERS = {
    "orthogroups": read_orthogroups,
    "annogroups": read_annogroups,
    "gene_families": read_gene_families,
    "gene_groups": read_gene_groups,
}


def main():
    parser = argparse.ArgumentParser( description = "Adapt a producer's sequence-group set into the standard membership" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    # Optional per-producer overrides (multi-producer runner passes these on the command
    # line so ONE run resolves many producers; each falls back to config when omitted).
    parser.add_argument( '--producer', default = None )
    parser.add_argument( '--group_set_label', default = None )
    parser.add_argument( '--producer_membership', default = None )
    parser.add_argument( '--workflow_root', default = None )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = Path( args.workflow_root ).resolve() if args.workflow_root else U.workflow_root_from_output_dir( args.output_dir )

    group_set_label = args.group_set_label if args.group_set_label else config[ "group_set_label" ]
    producer = args.producer if args.producer else config[ "producer" ]
    if producer not in PRODUCER_READERS:
        print( f"CRITICAL ERROR: unknown producer '{producer}'; known producers: {sorted( PRODUCER_READERS )}", file = sys.stderr )
        sys.exit( 1 )

    # producer_membership is a FILE for most producers (orthogroups, annogroups) and a
    # DIRECTORY for gene_families (a tree of per-family AGS FASTAs).
    producer_membership_config = args.producer_membership if args.producer_membership else config[ "inputs" ][ "producer_membership" ]
    producer_membership_path = U.resolve_input_path( workflow_root, producer_membership_config )
    if not producer_membership_path.exists():
        print( f"CRITICAL ERROR: producer membership not found: {producer_membership_path}", file = sys.stderr )
        sys.exit( 1 )

    output_dir = Path( args.output_dir ) / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_path = output_dir / f"1_ai-{group_set_label}-sequence_group_membership.tsv"

    header = (
        "SequenceGroup_ID (identifier of the sequence group from the producer)\t"
        "Sequence_Identifier (full GIGANTIC member sequence identifier)\t"
        "Genus_Species (Genus_species of the member, parsed from the sequence identifier)\n"
    )

    rows_written = 0
    groups = set()
    members_without_species = []
    with open( output_path, 'w' ) as output_file:
        output_file.write( header )
        for ( sequence_group_id, sequence_identifier, genus_species ) in PRODUCER_READERS[ producer ]( producer_membership_path ):
            if not genus_species:
                if len( members_without_species ) < 5:
                    members_without_species.append( sequence_identifier )
                continue
            output = sequence_group_id + '\t' + sequence_identifier + '\t' + genus_species + '\n'
            output_file.write( output )
            rows_written += 1
            groups.add( sequence_group_id )

    if members_without_species:
        print( f"CRITICAL ERROR: {len( members_without_species )}+ member ids had no parseable Genus_species "
               f"(silent member loss); examples: {members_without_species}", file = sys.stderr )
        sys.exit( 1 )
    if rows_written == 0:
        print( f"CRITICAL ERROR: zero member rows written from {producer_membership_path.name}", file = sys.stderr )
        sys.exit( 1 )

    print( f"[001 {group_set_label}] adapted {producer}: {rows_written} member rows across {len( groups )} sequence groups "
           f"-> {output_path.name}" )


if __name__ == '__main__':
    main()
