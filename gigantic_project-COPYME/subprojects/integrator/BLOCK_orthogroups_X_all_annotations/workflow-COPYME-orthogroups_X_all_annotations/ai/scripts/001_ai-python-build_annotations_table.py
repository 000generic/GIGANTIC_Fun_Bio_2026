#!/usr/bin/env python3
# AI: Claude (Cursor) | Opus 4.8 | 2026 July 10 | Purpose: Build the per-orthogroup all-annotations table (Pfam/GO/PANTHER/gene families/gene groups/dark proteome/hotspots + species-tree deconvolution)
# Human: Eric Edsinger

"""
Script 001 — Build the orthogroups_X_all_annotations table (one row per OrthoHMM orthogroup).

Each row is ONE OrthoHMM orthogroup. Columns, in order:

  Orthogroup_ID
  Sequence_IDs                     comma-delimited full GIGANTIC member IDs
  Member_Sequence_Count            integer
  Is_Singleton                     yes | no

  For EACH of ten annotation types, four columns:
    <Type>_Species_Count           non-redundant # Genus_species among member
                                   sequences carrying >=1 annotation of this type
    <Type>_Sequence_Count          # member sequences carrying >=1 annotation
    <Type>_Identifiers             comma-delimited non-redundant identifiers
    <Type>_Names                   ' // '-delimited names aligned to identifiers

  Types (in order): Pfam, GO, PANTHER, Annogroups_Pfam, Annogroups_GO, Annogroups_PANTHER,
                    Gene_Families, Gene_Groups, Dark_Proteome, Hotspots

  <clade / species columns...>     species-tree deconvolution (see below)

Species-tree deconvolution
--------------------------
One column per NON-REDUNDANT clade (internal node or species tip), taken as the
UNION of clades across the selected structures (default 001, 003, 031, 032). Each
cell = the count of the orthogroup's member sequences within that clade. A clade
covering every species (a tree root) equals Member_Sequence_Count. GIGANTIC Rule 6
guarantees a clade_id_name is a fixed species set, so counts are identical across
the structures it appears in; the union is non-redundant and each header records
which selected structures the clade is in. Column order: largest clade -> tips.

Per-type annotation sources and join keys
-----------------------------------------
Pfam    : annotations_hmms BLOCK_interproscan_parsed/pfam/pfam-<phyloname>.tsv
          (Protein_Identifier -> Accession + Description). Join = full GIGANTIC id.
GO      : annotations_hmms BLOCK_interproscan/<phyloname>_interproscan_results.tsv
          (no header; col0 = protein, col13 = pipe-delimited GO:NNNNNNN(Origin)).
          Names from GO_reference/go_id_to_name.tsv. Join = full GIGANTIC id.
PANTHER : BLOCK_interproscan_parsed/panther/panther-<phyloname>.tsv
          (Protein_Identifier -> Accession PTHR##### + Description). Join = full id.
Annogroups_Pfam / Annogroups_GO / Annogroups_PANTHER :
          annogroups BLOCK_build_annogroups/<species_set>/<source>/
          2_ai-<source>-annogroup_map.tsv + 2_ai-<source>-annogroup_membership.tsv
          (ALL annogroup types: feature, combination, architecture, absent).
          Identifier = Annogroup_ID; name from Annotation_Definitions (or fixed
          label for absent). Join = full GIGANTIC id. STRICT fail-fast.
Gene_Families : invert AGS FASTAs trees_gene_families/output_to_input/<slug>/**/16_ai-ags-*.aa
          id = family slug; name = family slug (no central name table). Join = full id.
Gene_Groups   : invert AGS trees_gene_groups/output_to_input/gene_groups-*/**/gene_group-<san>/**/16_ai-ags-*.aa
          id = gg<N> (from HGNC metadata; fallback = sanitized name); name = Gene_Group_Name. Join = full id.
Dark_Proteome : dark_proteomes .../3_ai-dark_proteome-<Genus_species>.tsv
          (Full_GIGANTIC_Gene_ID -> Status). id = Status (DARK/ANNOTATED);
          name = Annotation_Sources_CSV (or 'none'). Join = full GIGANTIC id.
Hotspots      : hotspots .../3_ai-hotspots-<Genus_species>.tsv (region rows;
          Member_Source_Gene_IDs comma-delimited bare gene ids). id = Hotspot_ID;
          NO human name (Names column blank). Join = (Genus_species, bare gene id),
          where bare gene id = member.split('-t_')[0] with the leading 'g_' removed.

Fail-fast policy (§36)
----------------------
STRICT (exit 1) for Pfam/GO/PANTHER: an annotated sequence absent from the
orthogroups means a silently dropped annotation (the annotation proteome set and
the orthogroup member set must be identical for species70). Also exit 1 on missing
inputs, Rule-6 violations, non-tip member species, full-coverage count mismatch,
or any name containing the NAME delimiter ' // '.

DOCUMENTED EXCEPTION (explicit user decision, Eric Edsinger 2026-07-10): InterProScan
truncates protein identifiers at a hard 255-char cap. A few GIGANTIC *fused* gene
models (e.g. Sphaeroforma arctica; pfam 7 / panther 7 / go 9 sequences) exceed this,
so their annotation-file ids are truncated to exactly 255 chars and cannot match the
orthogroup member ids. These specific 255-char truncated sequences are DROPPED (their
annotations are not attributed) and written to a report file — never silent. An absent
id of any OTHER length still triggers fail-fast.

LOG-AND-SKIP (never silent) for AGS-based types (gene families/groups), dark
proteome, and hotspots: these sources may legitimately contain sequences outside
species70 (e.g. reference/other-set sequences in AGS) or cover fewer species
(hotspots: 64/70). Non-orthogroup members are counted and reported prominently in
the run log, never dropped silently.
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_orthogroups_X_all_annotations as U


# ===========================================================================
# Feature-result container (uniform across all seven annotation types)
# ===========================================================================
def new_feature( prefix: str, label: str, names_blank: bool = False ) -> dict:
    """A per-type accumulator. Keyed by orthogroup id throughout."""
    return {
        "prefix": prefix,
        "label": label,
        "names_blank": names_blank,
        "orthogroups___identifiers": defaultdict( set ),   # og -> { identifier }
        "orthogroups___sequences": defaultdict( set ),     # og -> { annotated member seq id }
        "orthogroups___species": defaultdict( set ),       # og -> { Genus_species of annotated members }
        "identifiers___names": {},                         # identifier -> name
        "skipped_non_orthogroup": 0,                       # log-and-skip counter
    }


def add_annotation( feature: dict, og_id: str, sequence_id: str, genus_species: str,
                    identifier: str, name: str ):
    """Record one (sequence, identifier) annotation for its orthogroup."""
    feature[ "orthogroups___identifiers" ][ og_id ].add( identifier )
    feature[ "orthogroups___sequences" ][ og_id ].add( sequence_id )
    feature[ "orthogroups___species" ][ og_id ].add( genus_species )
    if not feature[ "names_blank" ]:
        feature[ "identifiers___names" ][ identifier ] = name


def guard_name( label: str, identifier: str, name: str ):
    """Fail fast if a name contains the NAME-column delimiter (would corrupt the list)."""
    if U.NAME_DELIM in name:
        print( f"CRITICAL ERROR: {label} name for identifier {identifier} contains the NAME-column "
               f"delimiter {U.NAME_DELIM!r} and would corrupt the *_Names list: {name!r}", file = sys.stderr )
        sys.exit( 1 )


# ===========================================================================
# Clade data (species-tree deconvolution) — reused from the leonid block
# ===========================================================================
def load_clade_data( clade_map_path: Path, selected_structures: list ):
    selected = set( selected_structures )
    clades___species = {}
    clades___descendant_count = {}
    clades___structures_set = defaultdict( set )
    tip_species = set()
    seen_structures = set()

    # Structure_ID	Clade_ID_Name	Phylogenetic_Block	Descendant_Species_Count	Descendant_Species_List	...
    # structure_001	C082_Metazoa	...::...	70	Acropora_muricata,Adineta_vaga,...	...
    with open( clade_map_path, 'r' ) as input_clade_map:
        header_ids___indices = U.build_header_index( input_clade_map.readline() )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_descendant_count = header_ids___indices[ "Descendant_Species_Count" ]
        index_descendant_list = header_ids___indices[ "Descendant_Species_List" ]

        for line in input_clade_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            structure_id = parts[ index_structure ]
            if structure_id not in selected:
                continue
            seen_structures.add( structure_id )

            clade_id_name = parts[ index_clade ]
            descendant_count = int( parts[ index_descendant_count ] ) if parts[ index_descendant_count ] else 0
            descendant_list = parts[ index_descendant_list ] if index_descendant_list < len( parts ) else ''

            if descendant_count > 0:
                species = frozenset( name.strip() for name in descendant_list.split( ',' ) if name.strip() )
            else:
                species_name = clade_id_name.split( '_', 1 )[ 1 ] if '_' in clade_id_name else clade_id_name
                species = frozenset( [ species_name ] )
                tip_species.add( species_name )

            clades___structures_set[ clade_id_name ].add( structure_id )

            if clade_id_name in clades___species:
                if clades___species[ clade_id_name ] != species:
                    print( f"CRITICAL ERROR: clade {clade_id_name} has DIFFERENT species sets across the "
                           f"selected structures (Rule 6 violation) -- counts would be ill-defined", file = sys.stderr )
                    sys.exit( 1 )
            else:
                clades___species[ clade_id_name ] = species
                clades___descendant_count[ clade_id_name ] = descendant_count

    missing_structures = selected - seen_structures
    if missing_structures:
        print( f"CRITICAL ERROR: selected structure(s) not found in {clade_map_path}: "
               f"{sorted( missing_structures )}", file = sys.stderr )
        sys.exit( 1 )
    if not clades___species:
        print( f"CRITICAL ERROR: no clades found for selected structures in {clade_map_path}", file = sys.stderr )
        sys.exit( 1 )

    clades___structures = { clade: sorted( structures ) for clade, structures in clades___structures_set.items() }

    union_ordered_clades = sorted(
        clades___species.keys(),
        key = lambda clade: ( -clades___descendant_count[ clade ], clade )
    )
    full_coverage_clades = [ clade for clade in union_ordered_clades
                             if clades___species[ clade ] == frozenset( tip_species ) ]

    species___ancestor_clades = defaultdict( list )
    for clade_id_name, species in clades___species.items():
        for species_name in species:
            species___ancestor_clades[ species_name ].append( clade_id_name )

    return ( clades___species, clades___descendant_count, clades___structures, tip_species,
             species___ancestor_clades, union_ordered_clades, full_coverage_clades )


# ===========================================================================
# Orthogroups spine — reused from the leonid block
# ===========================================================================
def load_orthogroups( orthogroups_path: Path ):
    orthogroups = []
    sequences___orthogroups = {}
    # (headerless) OG_ID <tab> member_1 <tab> member_2 <tab> ...
    # OG000001	g_g19067-t_g19067.t1-p_g19067.t1-n_HolozoaUNOFFICIAL_..._Abeoforma_whisleri	...
    with open( orthogroups_path, 'r' ) as input_orthogroups:
        for line in input_orthogroups:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            og_id = parts[ 0 ]
            members = parts[ 1: ]
            orthogroups.append( ( og_id, members ) )
            for member in members:
                sequences___orthogroups[ member ] = og_id
    if not orthogroups:
        print( f"CRITICAL ERROR: no orthogroups parsed from {orthogroups_path}", file = sys.stderr )
        sys.exit( 1 )
    return orthogroups, sequences___orthogroups


# InterProScan truncates protein identifiers at a hard 255-character cap. A few
# GIGANTIC *fused* gene models (e.g. Sphaeroforma arctica) have full IDs longer
# than this, so their annotation-file IDs are truncated to exactly 255 chars and
# cannot match the (longer) orthogroup member IDs. Per an explicit user decision
# (Eric Edsinger, 2026-07-10), these specific truncated sequences are DROPPED
# (their annotations are not attributed) — but the drop is documented: each is
# counted and written to a report file, and it is NOT silent. An absent sequence
# of any OTHER length still triggers fail-fast (a genuine ID/species-set mismatch).
INTERPROSCAN_ID_TRUNCATION_LENGTH = 255


def report_dropped_truncated( source: str, dropped_truncated: set, output_dir: Path ):
    """Write + loudly log the truncated (255-char) sequences we dropped for this source."""
    if not dropped_truncated:
        return
    report_path = output_dir / f"1_ai-{source}-dropped_truncated_255char_sequences.tsv"
    with open( report_path, 'w' ) as output_dropped:
        output_dropped.write( "Truncated_Sequence_Identifier (255-char InterProScan-truncated id; annotations DROPPED per explicit user decision 2026-07-10)\n" )
        for sequence_id in sorted( dropped_truncated ):
            output_dropped.write( sequence_id + '\n' )
    print( f"[001] WARNING: {source}: DROPPED {len( dropped_truncated )} sequence(s) whose id is exactly "
           f"{INTERPROSCAN_ID_TRUNCATION_LENGTH} chars (InterProScan truncation of over-long fused gene models); "
           f"their {source} annotations are not attributed. Explicit user decision (2026-07-10). "
           f"Report: {report_path}" )


def source_gene_id_from_full_id( full_id: str ) -> str:
    """Bare species-local gene id: 'g_A1BG-t_...' -> 'A1BG'; 'g_g5785-t_...' -> 'g5785'."""
    gene_field = full_id.split( '-t_' )[ 0 ]
    if gene_field.startswith( 'g_' ):
        gene_field = gene_field[ 2: ]
    return gene_field


# ===========================================================================
# Loaders — Pfam / PANTHER (InterProScan parsed, per-species, HAS header)
# ===========================================================================
def load_parsed_interproscan( feature: dict, source_dir: Path, source: str,
                              sequences___orthogroups: dict, output_dir: Path ):
    """
    STRICT fail-fast: an annotated sequence absent from the orthogroups is a
    silently dropped annotation -> write offenders and exit 1. EXCEPTION (explicit
    user decision, documented): an absent id of exactly the InterProScan 255-char
    truncation length is DROPPED (counted + reported), not fatal.
    """
    files = sorted( source_dir.glob( f"{source}-*.tsv" ) )
    if not files:
        print( f"CRITICAL ERROR: no {source} files found in {source_dir}", file = sys.stderr )
        sys.exit( 1 )
    missing_sequences = []
    dropped_truncated = set()
    for source_file in files:
        # Protein_Identifier	MD5	Sequence_Length	Analysis_Database	Accession	Description	Match_Start ...
        # g_3460263-t_3460263-p_3460263-n_Metazoa_Ctenophora_..._Pleurobrachia_bachei	<md5>	11223	Pfam	PF10505	NMDA receptor-regulated gene protein 2 C-terminus	...
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            index_accession = header_ids___indices[ "Accession" ]
            index_description = header_ids___indices[ "Description" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                sequence_id = parts[ index_protein ]
                og_id = sequences___orthogroups.get( sequence_id )
                if og_id is None:
                    if len( sequence_id ) == INTERPROSCAN_ID_TRUNCATION_LENGTH:
                        dropped_truncated.add( sequence_id )
                        continue
                    if len( missing_sequences ) < 100:
                        missing_sequences.append( sequence_id )
                    else:
                        missing_sequences.append( None )
                    continue
                accession = parts[ index_accession ]
                name = parts[ index_description ] if index_description < len( parts ) else ''
                guard_name( feature[ "label" ], accession, name )
                genus_species = U.genus_species_from_full_gigantic_id( sequence_id )
                add_annotation( feature, og_id, sequence_id, genus_species, accession, name )

    report_dropped_truncated( source, dropped_truncated, output_dir )

    if missing_sequences:
        real_missing = [ s for s in missing_sequences if s is not None ]
        overflow = missing_sequences.count( None )
        missing_report_path = output_dir / f"1_ai-{source}-sequences_absent_from_orthogroups.tsv"
        with open( missing_report_path, 'w' ) as output_missing:
            output_missing.write( "Sequence_Identifier (annotated sequence absent from the orthogroups table)\n" )
            for sequence_id in real_missing:
                output_missing.write( sequence_id + '\n' )
        print( f"CRITICAL ERROR: {source} has {len( real_missing ) + overflow} annotated sequence(s) absent from the "
               f"orthogroups table (length != {INTERPROSCAN_ID_TRUNCATION_LENGTH}, so NOT the known truncation case) "
               f"-- their annotations would be silently dropped. First offenders written to "
               f"{missing_report_path}", file = sys.stderr )
        sys.exit( 1 )


# ===========================================================================
# Loader — GO (raw InterProScan, per-species, NO header) + go_id_to_name
# ===========================================================================
def load_go_names( go_name_path: Path ) -> dict:
    identifiers___names = {}
    # GO_ID	GO_Name	GO_Namespace	Is_Obsolete	Is_Primary_ID
    # GO:0000001	mitochondrion inheritance	biological_process	False	True
    with open( go_name_path, 'r' ) as input_go:
        header_ids___indices = U.build_header_index( input_go.readline() )
        index_id = header_ids___indices[ "GO_ID" ]
        index_name = header_ids___indices[ "GO_Name" ]
        for line in input_go:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            identifiers___names[ parts[ index_id ] ] = parts[ index_name ]
    if not identifiers___names:
        print( f"CRITICAL ERROR: no GO id->name pairs parsed from {go_name_path}", file = sys.stderr )
        sys.exit( 1 )
    return identifiers___names


GO_TERMS_COLUMN_INDEX = 13   # fixed InterProScan column (no header)
GO_PROTEIN_COLUMN_INDEX = 0


def load_go_raw( feature: dict, raw_dir: Path, go_id_to_name: dict,
                 sequences___orthogroups: dict, output_dir: Path ):
    """
    STRICT fail-fast on annotated sequences absent from orthogroups, EXCEPT absent
    ids of exactly the 255-char InterProScan truncation length, which are DROPPED
    (counted + reported) per the explicit user decision. GO names missing from
    go_id_to_name use a placeholder (logged), never dropped.
    """
    files = sorted( raw_dir.glob( "*_interproscan_results.tsv" ) )
    if not files:
        print( f"CRITICAL ERROR: no *_interproscan_results.tsv files found in {raw_dir}", file = sys.stderr )
        sys.exit( 1 )
    missing_sequences = []
    missing_name_ids = set()
    dropped_truncated = set()
    for source_file in files:
        # (no header) col0 = Protein_Identifier ; col13 = pipe-delimited GO:NNNNNNN(Origin) ; '-' if none
        # g_3460263-...-n_..._Pleurobrachia_bachei	<md5>	11223	Pfam	PF10505	...	GO:0008023(InterPro)	-
        with open( source_file, 'r' ) as input_source:
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                if len( parts ) <= GO_TERMS_COLUMN_INDEX:
                    continue
                go_terms = parts[ GO_TERMS_COLUMN_INDEX ]
                if not go_terms or go_terms == '-':
                    continue
                sequence_id = parts[ GO_PROTEIN_COLUMN_INDEX ]
                og_id = sequences___orthogroups.get( sequence_id )
                if og_id is None:
                    if len( sequence_id ) == INTERPROSCAN_ID_TRUNCATION_LENGTH:
                        dropped_truncated.add( sequence_id )
                        continue
                    if len( missing_sequences ) < 100:
                        missing_sequences.append( sequence_id )
                    else:
                        missing_sequences.append( None )
                    continue
                genus_species = U.genus_species_from_full_gigantic_id( sequence_id )
                for token in go_terms.split( '|' ):
                    token = token.strip()
                    if not token:
                        continue
                    go_id = token.split( '(' )[ 0 ].strip()
                    if not go_id.startswith( "GO:" ):
                        continue
                    name = go_id_to_name.get( go_id )
                    if name is None:
                        name = "unknown GO term"
                        missing_name_ids.add( go_id )
                    guard_name( feature[ "label" ], go_id, name )
                    add_annotation( feature, og_id, sequence_id, genus_species, go_id, name )

    report_dropped_truncated( "go", dropped_truncated, output_dir )

    if missing_sequences:
        real_missing = [ s for s in missing_sequences if s is not None ]
        overflow = missing_sequences.count( None )
        missing_report_path = output_dir / "1_ai-go-sequences_absent_from_orthogroups.tsv"
        with open( missing_report_path, 'w' ) as output_missing:
            output_missing.write( "Sequence_Identifier (annotated sequence absent from the orthogroups table)\n" )
            for sequence_id in real_missing:
                output_missing.write( sequence_id + '\n' )
        print( f"CRITICAL ERROR: GO has {len( real_missing ) + overflow} annotated sequence(s) absent from the "
               f"orthogroups table (length != {INTERPROSCAN_ID_TRUNCATION_LENGTH}, so NOT the known truncation case) "
               f"-- their annotations would be silently dropped. First offenders written to "
               f"{missing_report_path}", file = sys.stderr )
        sys.exit( 1 )

    if missing_name_ids:
        print( f"[001] GO: {len( missing_name_ids )} GO id(s) had no name in go_id_to_name and used the "
               f"placeholder 'unknown GO term' (ids retained, not dropped)" )


# ===========================================================================
# Loaders — Annogroups (pfam/go/panther; ALL types; STRICT fail-fast)
# ===========================================================================
def load_annogroup_map( map_path: Path, source_label: str ) -> dict:
    """Build { Annogroup_ID: name } for every row in the annogroup MAP."""
    annogroup_ids___names = {}
    # Annogroup_ID	Source	Annogroup_Type	Defining_Features	Annotation_Definitions	...
    # annogroup_pfam_PF00001	pfam	feature	PF00001	7 transmembrane receptor (rhodopsin family) ==PF00001	...
    with open( map_path, 'r' ) as input_map:
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        index_type = header_ids___indices[ "Annogroup_Type" ]
        index_definitions = header_ids___indices[ "Annotation_Definitions" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            annogroup_id = parts[ index_annogroup ]
            annogroup_type = parts[ index_type ]
            definitions = parts[ index_definitions ] if index_definitions < len( parts ) else ''
            name = U.annogroup_name_from_map_fields( annogroup_type, definitions )
            guard_name( source_label, annogroup_id, name )
            annogroup_ids___names[ annogroup_id ] = name
    if not annogroup_ids___names:
        print( f"CRITICAL ERROR: no annogroups parsed from {map_path}", file = sys.stderr )
        sys.exit( 1 )
    return annogroup_ids___names


def load_annogroups_membership( feature: dict, membership_path: Path, source_label: str,
                                annogroup_ids___names: dict, sequences___orthogroups: dict,
                                output_dir: Path ):
    """
    STRICT fail-fast: any membership sequence absent from orthogroups means a
    silently dropped annotation -> write offenders and exit 1.
    """
    missing_sequences = []
    # Sequence_Identifier	Genus_Species	Annogroup_ID	Annogroup_Type	Member_Architecture_Coordinates ...
    with open( membership_path, 'r' ) as input_membership:
        header_ids___indices = U.build_header_index( input_membership.readline() )
        index_sequence = header_ids___indices[ "Sequence_Identifier" ]
        index_annogroup = header_ids___indices[ "Annogroup_ID" ]
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_id = parts[ index_sequence ]
            annogroup_id = parts[ index_annogroup ]
            og_id = sequences___orthogroups.get( sequence_id )
            if og_id is None:
                if len( missing_sequences ) < 100:
                    missing_sequences.append( sequence_id )
                else:
                    missing_sequences.append( None )
                continue
            if annogroup_id not in annogroup_ids___names:
                print( f"CRITICAL ERROR: {source_label} membership annogroup {annogroup_id} has no "
                       f"name in the annogroup map -- map/membership mismatch", file = sys.stderr )
                sys.exit( 1 )
            name = annogroup_ids___names[ annogroup_id ]
            genus_species = U.genus_species_from_full_gigantic_id( sequence_id )
            add_annotation( feature, og_id, sequence_id, genus_species, annogroup_id, name )

    if missing_sequences:
        real_missing = [ sequence_id for sequence_id in missing_sequences if sequence_id is not None ]
        overflow = missing_sequences.count( None )
        source_slug = source_label.lower().replace( ' ', '_' )
        missing_report_path = output_dir / f"1_ai-{source_slug}-annogroup_sequences_absent_from_orthogroups.tsv"
        with open( missing_report_path, 'w' ) as output_missing:
            output_missing.write( "Sequence_Identifier (annogroup membership sequence absent from the orthogroups table)\n" )
            for sequence_id in real_missing:
                output_missing.write( sequence_id + '\n' )
        print( f"CRITICAL ERROR: {source_label} has {len( real_missing ) + overflow} annogroup membership "
               f"sequence(s) absent from the orthogroups table -- their annotations would be silently dropped. "
               f"First offenders written to {missing_report_path}", file = sys.stderr )
        sys.exit( 1 )


# ===========================================================================
# Loaders — Gene families / gene groups (invert AGS FASTAs; LOG-AND-SKIP)
# ===========================================================================
def iter_fasta_member_headers( fasta_path: Path ):
    """Yield full GIGANTIC member ids (headers starting with 'g_'); skip 'rgs_' refs."""
    with open( fasta_path, 'r' ) as input_fasta:
        for line in input_fasta:
            if not line.startswith( '>' ):
                continue
            header = line[ 1: ].strip()
            if header.startswith( 'g_' ):
                yield header


def load_gene_families( feature: dict, gene_families_dir: Path, sequences___orthogroups: dict ):
    if not gene_families_dir.is_dir():
        print( f"CRITICAL ERROR: gene_families directory not found: {gene_families_dir}", file = sys.stderr )
        sys.exit( 1 )
    family_count = 0
    for family_dir in sorted( gene_families_dir.iterdir() ):
        if not family_dir.is_dir():
            continue
        ags_files = sorted( family_dir.rglob( "16_ai-ags-*.aa" ) )
        if not ags_files:
            continue
        family_slug = family_dir.name
        family_count += 1
        for ags_file in ags_files:
            for sequence_id in iter_fasta_member_headers( ags_file ):
                og_id = sequences___orthogroups.get( sequence_id )
                if og_id is None:
                    feature[ "skipped_non_orthogroup" ] += 1
                    continue
                genus_species = U.genus_species_from_full_gigantic_id( sequence_id )
                add_annotation( feature, og_id, sequence_id, genus_species, family_slug, family_slug )
    print( f"[001] gene_families: {family_count} families scanned" )


def load_gene_group_metadata( metadata_path: Path ) -> dict:
    """{ sanitized_name : ( gene_group_id, gene_group_name ) } from HGNC metadata."""
    sanitized___id_name = {}
    if not metadata_path.is_file():
        print( f"[001] WARNING: gene_groups HGNC metadata not found ({metadata_path}); "
               f"gene group ids will fall back to sanitized names" )
        return sanitized___id_name
    # Gene_Group_ID	Gene_Group_Name	Sanitized_Name	Abbreviation	Typical_Gene	...
    # gg288	Pannexins	pannexins	PANX	PANX1	3	3	no
    with open( metadata_path, 'r' ) as input_metadata:
        header_ids___indices = U.build_header_index( input_metadata.readline() )
        index_id = header_ids___indices[ "Gene_Group_ID" ]
        index_name = header_ids___indices[ "Gene_Group_Name" ]
        index_sanitized = header_ids___indices[ "Sanitized_Name" ]
        for line in input_metadata:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sanitized___id_name[ parts[ index_sanitized ] ] = ( parts[ index_id ], parts[ index_name ] )
    return sanitized___id_name


# Known display names for non-HGNC gene-group instances (id fallback = sanitized).
GENE_GROUP_NAME_FALLBACKS = { "snap_family": "Synaptosomal-Associated Proteins" }


def load_gene_groups( feature: dict, gene_groups_dir: Path, sanitized___id_name: dict,
                      sequences___orthogroups: dict ):
    if not gene_groups_dir.is_dir():
        print( f"CRITICAL ERROR: gene_groups directory not found: {gene_groups_dir}", file = sys.stderr )
        sys.exit( 1 )
    group_dirs_seen = set()
    for instance_dir in sorted( gene_groups_dir.glob( "gene_groups-*" ) ):
        for ags_file in sorted( instance_dir.rglob( "16_ai-ags-*.aa" ) ):
            sanitized = None
            for part in ags_file.parts:
                if part.startswith( "gene_group-" ):
                    sanitized = part[ len( "gene_group-" ): ]
                    break
            if sanitized is None:
                continue
            group_dirs_seen.add( sanitized )
            if sanitized in sanitized___id_name:
                gene_group_id, gene_group_name = sanitized___id_name[ sanitized ]
            else:
                gene_group_id = sanitized
                gene_group_name = GENE_GROUP_NAME_FALLBACKS.get( sanitized, sanitized )
            guard_name( feature[ "label" ], gene_group_id, gene_group_name )
            for sequence_id in iter_fasta_member_headers( ags_file ):
                og_id = sequences___orthogroups.get( sequence_id )
                if og_id is None:
                    feature[ "skipped_non_orthogroup" ] += 1
                    continue
                genus_species = U.genus_species_from_full_gigantic_id( sequence_id )
                add_annotation( feature, og_id, sequence_id, genus_species, gene_group_id, gene_group_name )
    print( f"[001] gene_groups: {len( group_dirs_seen )} groups scanned" )


# ===========================================================================
# Loader — Dark proteome (native per-sequence, HAS header; LOG-AND-SKIP)
# ===========================================================================
def load_dark_proteome( feature: dict, dark_dir: Path, sequences___orthogroups: dict ):
    if not dark_dir.is_dir():
        print( f"CRITICAL ERROR: dark_proteome directory not found: {dark_dir}", file = sys.stderr )
        sys.exit( 1 )
    # per-species per-sequence files, EXCLUDING the *_summary-*.tsv species-level files
    files = sorted( p for p in dark_dir.glob( "3_ai-dark_proteome-*.tsv" )
                    if "dark_proteome_summary" not in p.name )
    if not files:
        print( f"CRITICAL ERROR: no 3_ai-dark_proteome-<species>.tsv files found in {dark_dir}", file = sys.stderr )
        sys.exit( 1 )
    for source_file in files:
        # Full_GIGANTIC_Gene_ID	Source_Gene_ID	Has_Reference_Blast	In_Reference_Orthogroup	Has_HMM_Annotation	Status	Annotation_Sources_CSV
        # g_A1BG-...-n_..._Homo_sapiens	A1BG	True	True	True	ANNOTATED	reference_blast,reference_orthogroup,hmm_annotation
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_full_id = header_ids___indices[ "Full_GIGANTIC_Gene_ID" ]
            index_status = header_ids___indices[ "Status" ]
            index_sources = header_ids___indices[ "Annotation_Sources_CSV" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                sequence_id = parts[ index_full_id ]
                og_id = sequences___orthogroups.get( sequence_id )
                if og_id is None:
                    feature[ "skipped_non_orthogroup" ] += 1
                    continue
                status = parts[ index_status ]
                sources = parts[ index_sources ] if index_sources < len( parts ) else ''
                name = sources.replace( ',', ' ' ).strip() if sources.strip() else "none"
                guard_name( feature[ "label" ], status, name )
                genus_species = U.genus_species_from_full_gigantic_id( sequence_id )
                add_annotation( feature, og_id, sequence_id, genus_species, status, name )


# ===========================================================================
# Loader — Hotspots (per-region -> invert to (species, gene); LOG-AND-SKIP)
# ===========================================================================
def load_hotspots( feature: dict, hotspots_dir: Path, orthogroups: list,
                   sequences___orthogroups: dict ):
    """
    Hotspot rows are per genomic region. Invert to { (Genus_species, bare_gene_id):
    set(Hotspot_ID) }, then attribute hotspots to orthogroup members by matching on
    (species, bare gene id). Names are blank (hotspots have no human name).
    Species without a hotspot file (6/70) simply contribute nothing.
    """
    if not hotspots_dir.is_dir():
        print( f"CRITICAL ERROR: hotspots directory not found: {hotspots_dir}", file = sys.stderr )
        sys.exit( 1 )
    files = sorted( p for p in hotspots_dir.glob( "3_ai-hotspots-*.tsv" )
                    if "hotspot_summary" not in p.name )
    if not files:
        print( f"CRITICAL ERROR: no 3_ai-hotspots-<species>.tsv files found in {hotspots_dir}", file = sys.stderr )
        sys.exit( 1 )

    species_gene___hotspots = defaultdict( set )
    species_with_hotspots = set()
    for source_file in files:
        # Hotspot_ID	Chromosome	Hotspot_Start	Hotspot_End	Paralog_Count	Member_Source_Gene_IDs
        # hotspot_w20_Homo_sapiens_00001	NC_000001.11	65419	720101	3	OR4F5,OR4F29,OR4F16
        # species from filename: 3_ai-hotspots-<Genus_species>.tsv
        genus_species = source_file.name[ len( "3_ai-hotspots-" ): -len( ".tsv" ) ]
        species_with_hotspots.add( genus_species )
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_hotspot = header_ids___indices[ "Hotspot_ID" ]
            index_members = header_ids___indices[ "Member_Source_Gene_IDs" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                hotspot_id = parts[ index_hotspot ]
                members_field = parts[ index_members ] if index_members < len( parts ) else ''
                for source_gene_id in members_field.split( ',' ):
                    source_gene_id = source_gene_id.strip()
                    if not source_gene_id:
                        continue
                    species_gene___hotspots[ ( genus_species, source_gene_id ) ].add( hotspot_id )

    # attribute to orthogroup members
    for og_id, members in orthogroups:
        for member in members:
            genus_species = U.genus_species_from_full_gigantic_id( member )
            source_gene_id = source_gene_id_from_full_id( member )
            hotspot_ids = species_gene___hotspots.get( ( genus_species, source_gene_id ) )
            if not hotspot_ids:
                continue
            for hotspot_id in hotspot_ids:
                add_annotation( feature, og_id, member, genus_species, hotspot_id, "" )

    print( f"[001] hotspots: {len( species_with_hotspots )} species with hotspot files; "
           f"{len( species_gene___hotspots )} (species,gene) hotspot memberships" )


# ===========================================================================
# Self-documenting headers
# ===========================================================================
def clade_header( clade, clades___descendant_count, clades___species, clades___structures, total_selected ):
    present_numbers = ','.join( U.structure_number( s ) for s in clades___structures[ clade ] )
    present = f"present in structures {present_numbers} of {total_selected} selected"
    if clades___descendant_count[ clade ] == 0:
        species_name = next( iter( clades___species[ clade ] ) )
        return ( f"{clade} (member sequence count of this orthogroup within tip {clade} = species "
                 f"{species_name}; {present})" )
    return ( f"{clade} (member sequence count of this orthogroup within clade {clade}; "
             f"{clades___descendant_count[ clade ]} descendant species; {present})" )


def feature_headers( feature: dict ) -> list:
    prefix = feature[ "prefix" ]
    label = feature[ "label" ]
    if feature[ "names_blank" ]:
        names_desc = ( f"{prefix}_Names (intentionally blank; {label} has no separate human-readable name -- "
                       f"see {prefix}_Identifiers)" )
    else:
        names_desc = ( f"{prefix}_Names (' // ' delimited {label} names aligned to {prefix}_Identifiers; "
                       f"' // ' used because names may contain commas, semicolons, or pipes)" )
    return [
        f"{prefix}_Species_Count (non-redundant count of Genus_species among member sequences carrying at least one {label} annotation)",
        f"{prefix}_Sequence_Count (count of member sequences carrying at least one {label} annotation)",
        f"{prefix}_Identifiers (comma delimited non-redundant {label} identifiers across all member sequences)",
        names_desc,
    ]


def feature_cells( feature: dict, og_id: str ) -> list:
    identifiers = sorted( feature[ "orthogroups___identifiers" ].get( og_id, () ) )
    sequence_count = len( feature[ "orthogroups___sequences" ].get( og_id, () ) )
    species_count = len( feature[ "orthogroups___species" ].get( og_id, () ) )
    if feature[ "names_blank" ]:
        names = ''
    else:
        names = U.NAME_DELIM.join( feature[ "identifiers___names" ][ identifier ] for identifier in identifiers )
    return [ str( species_count ), str( sequence_count ), U.DELIM.join( identifiers ), names ]


# ===========================================================================
# Main
# ===========================================================================
def main():
    parser = argparse.ArgumentParser( description = "Build the orthogroups_X_all_annotations table" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    hmm_sources = config[ "hmm_annotation_sources" ]
    annogroup_sources = config.get( "annogroup_sources", [ "pfam", "go", "panther" ] )
    species_set_name = config[ "species_set_name" ]
    selected_structures = config[ "inputs" ][ "deconvolution_structures" ]
    inputs = config[ "inputs" ]

    def resolve( key ):
        return U.resolve_input_path( workflow_root, inputs[ key ] )

    orthogroups_path = resolve( "orthogroups_file" )
    clade_map_path = resolve( "clade_species_mappings" )
    interproscan_parsed_dir = resolve( "interproscan_parsed_dir" )
    interproscan_raw_dir = resolve( "interproscan_raw_dir" )
    go_id_to_name_path = resolve( "go_id_to_name" )
    annogroups_dir = resolve( "annogroups_dir" )
    gene_families_dir = resolve( "gene_families_dir" )
    gene_groups_dir = resolve( "gene_groups_dir" )
    gene_groups_hgnc_metadata = resolve( "gene_groups_hgnc_metadata" )
    dark_proteome_dir = resolve( "dark_proteome_dir" )
    hotspots_dir = resolve( "hotspots_dir" )

    output_base = Path( args.output_dir )
    output_dir = output_base / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    _integrator_ai = Path( __file__ ).resolve().parents[ 4 ] / "ai"
    if str( _integrator_ai ) not in sys.path:
        sys.path.insert( 0, str( _integrator_ai ) )
    import utils_integrator_shared as S
    timestamp_suffix = S.resolve_workflow_run_timestamp_suffix( output_base )
    table_filename = S.build_timestamped_filename( U.OUTPUT_TABLE_STEM, timestamp_suffix )
    output_path = output_dir / table_filename
    print( f"[001] run timestamp suffix: {timestamp_suffix}" )

    for required in ( orthogroups_path, clade_map_path, go_id_to_name_path ):
        if not required.is_file():
            print( f"CRITICAL ERROR: required input not found: {required}", file = sys.stderr )
            sys.exit( 1 )
    if not annogroups_dir.is_dir():
        print( f"CRITICAL ERROR: annogroups directory not found: {annogroups_dir}", file = sys.stderr )
        sys.exit( 1 )

    # ---- clades ------------------------------------------------------------
    ( clades___species, clades___descendant_count, clades___structures, tip_species,
      species___ancestor_clades, union_ordered_clades, full_coverage_clades ) = load_clade_data(
        clade_map_path, selected_structures )
    total_selected = len( selected_structures )
    print( f"[001] deconvolution: {len( union_ordered_clades )} non-redundant clades across "
           f"{total_selected} structures; {len( tip_species )} tips; "
           f"{len( full_coverage_clades )} full-coverage root clade(s)" )

    # ---- orthogroups -------------------------------------------------------
    orthogroups, sequences___orthogroups = load_orthogroups( orthogroups_path )
    print( f"[001] loaded {len( orthogroups )} orthogroups; {len( sequences___orthogroups )} member sequences" )

    # ---- build every annotation feature (in output column order) -----------
    features = []

    hmm_display = { "pfam": "Pfam", "go": "GO", "panther": "PANTHER" }
    go_id_to_name = None
    for source in hmm_sources:
        display = hmm_display.get( source, source.capitalize() )
        feature = new_feature( display, display )
        if source == "go":
            go_id_to_name = load_go_names( go_id_to_name_path )
            load_go_raw( feature, interproscan_raw_dir, go_id_to_name, sequences___orthogroups, output_dir )
        else:
            source_dir = interproscan_parsed_dir / source
            if not source_dir.is_dir():
                print( f"CRITICAL ERROR: {source} parsed directory not found: {source_dir}", file = sys.stderr )
                sys.exit( 1 )
            load_parsed_interproscan( feature, source_dir, source, sequences___orthogroups, output_dir )
        features.append( feature )
        print( f"[001] {display}: {len( feature[ 'orthogroups___identifiers' ] )} orthogroups carry >=1 annotation; "
               f"{len( feature[ 'identifiers___names' ] )} distinct identifiers" )

    annogroup_display = { "pfam": "pfam annogroup", "go": "go annogroup", "panther": "panther annogroup" }
    for source in annogroup_sources:
        prefix = U.annogroup_prefix_for_source( source )
        label = annogroup_display.get( source, f"{source} annogroup" )
        source_dir = annogroups_dir / species_set_name / source
        map_path = source_dir / f"2_ai-{source}-annogroup_map.tsv"
        membership_path = source_dir / f"2_ai-{source}-annogroup_membership.tsv"
        for required in ( map_path, membership_path ):
            if not required.is_file():
                print( f"CRITICAL ERROR: required {source} annogroup input not found: {required}", file = sys.stderr )
                sys.exit( 1 )
        feature = new_feature( prefix, label )
        annogroup_ids___names = load_annogroup_map( map_path, prefix )
        load_annogroups_membership(
            feature, membership_path, prefix, annogroup_ids___names, sequences___orthogroups, output_dir )
        features.append( feature )
        print( f"[001] {prefix}: {len( feature[ 'orthogroups___identifiers' ] )} orthogroups carry >=1 annogroup; "
               f"{len( feature[ 'identifiers___names' ] )} distinct annogroup identifiers" )

    feature_gene_families = new_feature( "Gene_Families", "gene family" )
    load_gene_families( feature_gene_families, gene_families_dir, sequences___orthogroups )
    print( f"[001] Gene_Families: {len( feature_gene_families[ 'orthogroups___identifiers' ] )} orthogroups; "
           f"{feature_gene_families[ 'skipped_non_orthogroup' ]} non-orthogroup member(s) skipped (logged)" )
    features.append( feature_gene_families )

    sanitized___id_name = load_gene_group_metadata( gene_groups_hgnc_metadata )
    feature_gene_groups = new_feature( "Gene_Groups", "gene group" )
    load_gene_groups( feature_gene_groups, gene_groups_dir, sanitized___id_name, sequences___orthogroups )
    print( f"[001] Gene_Groups: {len( feature_gene_groups[ 'orthogroups___identifiers' ] )} orthogroups; "
           f"{feature_gene_groups[ 'skipped_non_orthogroup' ]} non-orthogroup member(s) skipped (logged)" )
    features.append( feature_gene_groups )

    feature_dark = new_feature( "Dark_Proteome", "dark proteome status" )
    load_dark_proteome( feature_dark, dark_proteome_dir, sequences___orthogroups )
    print( f"[001] Dark_Proteome: {len( feature_dark[ 'orthogroups___identifiers' ] )} orthogroups; "
           f"{feature_dark[ 'skipped_non_orthogroup' ]} non-orthogroup member(s) skipped (logged)" )
    features.append( feature_dark )

    feature_hotspots = new_feature( "Hotspots", "hotspot", names_blank = True )
    load_hotspots( feature_hotspots, hotspots_dir, orthogroups, sequences___orthogroups )
    print( f"[001] Hotspots: {len( feature_hotspots[ 'orthogroups___identifiers' ] )} orthogroups carry >=1 hotspot" )
    features.append( feature_hotspots )

    # ---- header ------------------------------------------------------------
    header_columns = [
        "Orthogroup_ID (OrthoHMM orthogroup identifier)",
        "Sequence_IDs (comma delimited full GIGANTIC member protein identifiers in this orthogroup)",
        "Member_Sequence_Count (number of member protein sequences in this orthogroup)",
        "Is_Singleton (yes if the orthogroup has exactly one member sequence else no)",
    ]
    for feature in features:
        header_columns.extend( feature_headers( feature ) )
    header_columns.extend(
        clade_header( clade, clades___descendant_count, clades___species, clades___structures, total_selected )
        for clade in union_ordered_clades )
    header_line = '\t'.join( header_columns )

    # ---- write rows --------------------------------------------------------
    rows_written = 0
    with open( output_path, 'w' ) as output_table:
        output_table.write( header_line + '\n' )
        for og_id, members in orthogroups:
            member_count = len( members )
            is_singleton = "yes" if member_count == 1 else "no"

            species___counts = defaultdict( int )
            for member in members:
                genus_species = U.genus_species_from_full_gigantic_id( member )
                if genus_species is None or genus_species not in tip_species:
                    print( f"CRITICAL ERROR: orthogroup {og_id} member {member} maps to species "
                           f"{genus_species!r}, which is not a tree tip -- it would be silently uncounted",
                           file = sys.stderr )
                    sys.exit( 1 )
                species___counts[ genus_species ] += 1

            clades___counts = defaultdict( int )
            for genus_species, count in species___counts.items():
                for clade_id_name in species___ancestor_clades[ genus_species ]:
                    clades___counts[ clade_id_name ] += count

            for clade in full_coverage_clades:
                if clades___counts.get( clade, 0 ) != member_count:
                    print( f"CRITICAL ERROR: orthogroup {og_id} count at full-coverage clade {clade} "
                           f"({clades___counts.get( clade, 0 )}) != Member_Sequence_Count {member_count}",
                           file = sys.stderr )
                    sys.exit( 1 )

            row = [ og_id, U.DELIM.join( members ), str( member_count ), is_singleton ]
            for feature in features:
                row.extend( feature_cells( feature, og_id ) )
            row.extend( str( clades___counts.get( clade, 0 ) ) for clade in union_ordered_clades )
            output_table.write( '\t'.join( row ) + '\n' )
            rows_written += 1

    print( f"[001] wrote {rows_written} orthogroup rows ({len( header_columns )} columns) -> {output_path}" )
    U.write_output_table_pointer( output_base, table_filename )


if __name__ == '__main__':
    main()
