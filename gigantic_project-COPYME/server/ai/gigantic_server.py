#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 April 20 | Purpose: GIGANTIC data server with drill-down hierarchy
# Human: Eric Edsinger

"""
GIGANTIC Data Server — Drill-down Hierarchy Edition

Renders each subproject's upload_to_server/ tree as a true hierarchical web
interface. Every directory is a page; walking into the tree drills down one
level. Files appear at the leaves, grouped by optional category metadata.

Stdlib only. No external Python dependencies. Keeps the brutalist aesthetic of
the original server.

Configuration:   ../START_HERE-server_config.yaml
Usage:
    python3 gigantic_server.py [--config PATH] [--port N] [--subprojects-dir PATH]

Data flow:
    subprojects/<sp>/upload_to_server/.../<file>  (symlinks)
        -> tree cache (rebuilt every refresh_interval_seconds)
        -> recursive hub/leaf renderer
        -> HTML
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import http.server
import socketserver
import socket
import argparse
import sys
import urllib.parse
import threading
import time
import re
import html as htmllib

# Local stdlib-only TSV/CSV -> .xlsx converter (sits next to this file).
# Ensure this script's directory is importable whether the server is launched
# as `python3 ai/gigantic_server.py` or imported as a module.
_THIS_DIRECTORY = Path( __file__ ).resolve().parent
if str( _THIS_DIRECTORY ) not in sys.path:
    sys.path.insert( 0, str( _THIS_DIRECTORY ) )
import tsv_to_xlsx


# ============================================================================
# Configuration Parser (hand-rolled; stdlib-only, preserved from v1)
# ============================================================================

class ServerConfig:
    """Parse and hold server config from YAML. Supports scalars, simple lists,
    one-level maps, and list-of-scalars. No external deps."""

    def __init__( self, config_path: Path ):
        self.config_path = config_path
        self.raw = {}

        if not config_path.exists():
            print( f"ERROR: Config file not found: {config_path}" )
            sys.exit( 1 )

        self._parse( config_path )

        # Scalars
        self.project_name = self._get_string( 'project_name', 'GIGANTIC DATA' )
        self.port = self._get_integer( 'port', 9456 )
        self.refresh_interval_seconds = self._get_integer( 'refresh_interval_seconds', 300 )
        self.show_empty_subprojects = self._get_bool( 'show_empty_subprojects', True )

        # Subproject ordering (explicit allowlist)
        self.subproject_order = self._get_list( 'subproject_order' )

        # Display customization
        self.display_names = self._get_map( 'display_names' )

        # File filtering
        self.exclude_file_patterns = self._get_list( 'exclude_file_patterns' )

        # SLURM settings (kept for .sbatch compatibility; not used by server itself)
        slurm_map = self._get_map( 'slurm' )
        self.slurm_account = slurm_map.get( 'account', 'your_account' )
        self.slurm_qos = slurm_map.get( 'qos', 'your_qos' )
        self.slurm_partition = slurm_map.get( 'partition', 'hpg-default' )

        # Credits
        credits_map = self._get_map( 'credits' )
        self.credits_ai = credits_map.get( 'ai', 'Claude Code' )
        self.credits_human = credits_map.get( 'human', '' )

    def _parse( self, config_path: Path ):
        """Simple YAML parser: scalars, lists (- item), one-level maps, inline {} [] empty."""
        with open( config_path, 'r' ) as f:
            lines = f.readlines()

        current_key = None
        current_map = None
        current_list = None
        current_indent = 0

        for raw_line in lines:
            # strip trailing whitespace, preserve leading
            line = raw_line.rstrip()
            stripped = line.lstrip()

            if not stripped or stripped.startswith( '#' ):
                continue

            indent = len( line ) - len( stripped )

            if stripped.startswith( '- ' ):
                # List item
                item = stripped[ 2: ].strip()
                item = self._unquote( item )
                if current_list is not None and indent > current_indent:
                    current_list.append( item )
                continue

            # key: value or key:
            if ':' in stripped:
                key, _, value = stripped.partition( ':' )
                key = key.strip()
                value = value.strip()

                if indent == 0:
                    # Top-level key
                    current_key = key
                    current_indent = indent

                    if value == '' or value == '{}' or value == '[]':
                        if value == '{}':
                            self.raw[ key ] = {}
                            current_map = None
                            current_list = None
                        elif value == '[]':
                            self.raw[ key ] = []
                            current_map = None
                            current_list = None
                        else:
                            # Defer: could be list or map, peek at next line
                            self.raw[ key ] = None
                            current_list = []
                            current_map = {}
                            # We'll commit either list or map once we see the first child
                    else:
                        self.raw[ key ] = self._unquote( value )
                        current_map = None
                        current_list = None
                elif indent > current_indent and current_key is not None:
                    # Child of current top-level key → treat as map entry
                    if self.raw.get( current_key ) is None:
                        # First child; commit as map
                        self.raw[ current_key ] = {}
                        current_map = self.raw[ current_key ]
                        current_list = None
                    if current_map is not None:
                        if value == '' or value == '{}' or value == '[]':
                            current_map[ key ] = {} if value != '[]' else []
                        else:
                            current_map[ key ] = self._unquote( value )
                continue

            # Fall through — unparseable line, ignore

        # Post-process: any key whose raw value is still None (meaning we saw
        # indented list items but no map keys) → commit as its list.
        # We detect lists by: parent key with child lines starting with '- '.
        # Re-scan specifically for lists because the above loop tracked into
        # current_list but never committed.
        self._second_pass_lists( lines )

    def _second_pass_lists( self, lines ):
        """Find top-level keys whose children are '- item' lines, materialize as lists."""
        current_key = None
        current_indent = -1
        accumulator = []

        for raw_line in lines + [ '' ]:  # sentinel
            line = raw_line.rstrip()
            stripped = line.lstrip()

            if not stripped or stripped.startswith( '#' ):
                continue

            indent = len( line ) - len( stripped )

            if stripped.startswith( '- ' ):
                if current_key is not None:
                    item = stripped[ 2: ].strip()
                    accumulator.append( self._unquote( item ) )
                continue

            # Non-list line → if we were accumulating, flush
            if current_key is not None and accumulator:
                # Only override if raw value was None (undecided) or we explicitly want list
                if self.raw.get( current_key ) is None:
                    self.raw[ current_key ] = accumulator
                elif isinstance( self.raw.get( current_key ), dict ) and not self.raw[ current_key ]:
                    # Empty map that's actually a list
                    self.raw[ current_key ] = accumulator
                accumulator = []

            if ':' in stripped and indent == 0:
                key, _, value = stripped.partition( ':' )
                current_key = key.strip()
                current_indent = indent

    @staticmethod
    def _unquote( s: str ) -> str:
        s = s.strip()
        if ( s.startswith( '"' ) and s.endswith( '"' ) ) or \
           ( s.startswith( "'" ) and s.endswith( "'" ) ):
            return s[ 1:-1 ]
        return s

    def _get_string( self, key: str, default: str = '' ) -> str:
        v = self.raw.get( key, default )
        return str( v ) if v is not None else default

    def _get_integer( self, key: str, default: int = 0 ) -> int:
        v = self.raw.get( key, default )
        try:
            return int( v )
        except ( TypeError, ValueError ):
            return default

    def _get_bool( self, key: str, default: bool = False ) -> bool:
        v = self.raw.get( key, default )
        if isinstance( v, bool ):
            return v
        if isinstance( v, str ):
            return v.strip().lower() in ( 'true', 'yes', '1', 'on' )
        return default

    def _get_list( self, key: str ) -> list:
        v = self.raw.get( key )
        if isinstance( v, list ):
            return v
        return []

    def _get_map( self, key: str ) -> dict:
        v = self.raw.get( key )
        if isinstance( v, dict ):
            return v
        return {}


# ============================================================================
# Directory Tree Cache
# ============================================================================

class TreeNode:
    """
    One node in the cached directory tree.

    Attributes:
        name: directory/file name (URL-safe path segment)
        display_name: human-readable label for this node
        is_file: True for file, False for directory
        real_path: absolute resolved path on disk (follows symlinks)
        children: dict[name -> TreeNode] if is_file=False
        size_bytes: file size (if is_file)
        category: file_category string (from sidecar metadata) for grouping in leaf pages
        description: tooltip/subtitle
        order: sort key for display (lower = earlier)
    """

    __slots__ = (
        'name', 'display_name', 'is_file', 'real_path', 'children',
        'size_bytes', 'category', 'description', 'order',
    )

    def __init__( self, name: str, is_file: bool, real_path: Path ):
        self.name = name
        self.display_name = ''
        self.is_file = is_file
        self.real_path = real_path
        self.children: Dict[ str, 'TreeNode' ] = {}
        self.size_bytes = 0
        self.category = ''
        self.description = ''
        self.order = 100


def build_tree( upload_dir: Path, config: ServerConfig ) -> TreeNode:
    """
    Walk upload_to_server/ and produce a TreeNode rooted at `upload_dir`.
    Reads .section_metadata.tsv sidecars where present to decorate file nodes.
    Skips files matching exclude_file_patterns.
    """
    root = TreeNode( name = upload_dir.name, is_file = False, real_path = upload_dir )

    def should_exclude_file( file_path: Path ) -> bool:
        name = file_path.name
        for pattern in config.exclude_file_patterns:
            if pattern in name:
                return True
        return False

    def load_sidecar( directory: Path ) -> Dict[ str, Dict[ str, str ] ]:
        """Load filename -> metadata dict from .section_metadata.tsv in this dir."""
        sidecar = directory / '.section_metadata.tsv'
        if not sidecar.exists():
            return {}
        result = {}
        try:
            with open( sidecar, 'r' ) as f:
                header_fields = None
                for line in f:
                    line = line.rstrip( '\n' )
                    if not line or line.startswith( '#' ):
                        continue
                    parts = line.split( '\t' )
                    if header_fields is None:
                        header_fields = parts
                        continue
                    if len( parts ) < len( header_fields ):
                        # pad
                        parts = parts + [ '' ] * ( len( header_fields ) - len( parts ) )
                    row = dict( zip( header_fields, parts ) )
                    fname = row.get( 'filename', '' )
                    if fname:
                        result[ fname ] = row
        except Exception as e:
            print( f"  WARN: failed to parse {sidecar}: {e}" )
        return result

    def walk( dir_path: Path, parent: TreeNode ):
        try:
            sidecar = load_sidecar( dir_path )
            entries = sorted( dir_path.iterdir(), key = lambda p: p.name.lower() )
        except ( PermissionError, FileNotFoundError ):
            return

        # Reserved __DIR__ row carries a short label for THIS directory itself
        # (rendered as a folder subtitle). Not a real file on disk.
        dir_meta = sidecar.get( '__DIR__', {} )
        if dir_meta.get( 'description', '' ):
            parent.description = dir_meta[ 'description' ]

        for entry in entries:
            if entry.name.startswith( '.' ):
                # hide dotfiles (sidecars, .gitkeep, etc.)
                continue
            try:
                is_dir = entry.is_dir()
            except OSError:
                continue
            if is_dir:
                child = TreeNode( name = entry.name, is_file = False, real_path = entry.resolve() )
                parent.children[ entry.name ] = child
                walk( entry, child )
            else:
                if should_exclude_file( entry ):
                    continue
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                meta = sidecar.get( entry.name, {} )
                child = TreeNode( name = entry.name, is_file = True, real_path = entry.resolve() )
                child.size_bytes = size
                child.display_name = meta.get( 'display_label', '' )
                child.category = meta.get( 'file_category', '' )
                child.description = meta.get( 'description', '' )
                order_raw = meta.get( 'order', '' )
                try:
                    child.order = int( order_raw ) if order_raw else 100
                except ValueError:
                    child.order = 100
                parent.children[ entry.name ] = child

    walk( upload_dir, root )
    return root


# ============================================================================
# Server
# ============================================================================

class GIGANTICServer:

    def __init__( self, config: ServerConfig, subprojects_dir: Path, port_override: Optional[ int ] = None ):
        self.config = config
        self.subprojects_dir = subprojects_dir
        self.port = port_override if port_override is not None else config.port

        # Cache: subproject_name -> TreeNode (the root of that subproject's upload_to_server/)
        self._cache: Dict[ str, TreeNode ] = {}
        self._cache_built_at: Optional[ datetime ] = None
        self._cache_lock = threading.Lock()

    # ---- Display name helpers ----

    def _clean_display_name( self, raw: str ) -> str:
        """Convert directory_name_with_underscores to uppercase display form."""
        if raw in self.config.display_names:
            return self.config.display_names[ raw ]
        # Replace underscores with spaces, uppercase
        return raw.replace( '_', ' ' ).upper()

    def _format_size( self, size_bytes: int ) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        if size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / ( 1024 * 1024 ):.1f} MB"
        return f"{size_bytes / ( 1024 * 1024 * 1024 ):.2f} GB"

    # ---- Cache management ----

    def rebuild_cache( self ):
        """Rebuild the tree cache by walking each configured subproject's upload_to_server/."""
        new_cache: Dict[ str, TreeNode ] = {}

        for subproject_name in self.config.subproject_order:
            subproject_dir = self.subprojects_dir / subproject_name
            if not subproject_dir.exists() or not subproject_dir.is_dir():
                continue
            upload_dir = subproject_dir / 'upload_to_server'
            if not upload_dir.exists() or not upload_dir.is_dir():
                # Still cache an empty root so "NO DATA YET" can render
                if self.config.show_empty_subprojects:
                    new_cache[ subproject_name ] = TreeNode(
                        name = subproject_name, is_file = False, real_path = upload_dir
                    )
                continue
            new_cache[ subproject_name ] = build_tree( upload_dir, self.config )

        with self._cache_lock:
            self._cache = new_cache
            self._cache_built_at = datetime.now()

        total_nodes = sum( self._count_nodes( root ) for root in new_cache.values() )
        print( f"[{self._cache_built_at.strftime( '%Y-%m-%d %H:%M:%S' )}] "
               f"Cache rebuilt: {len( new_cache )} subprojects, {total_nodes} nodes" )

    def _count_nodes( self, node: TreeNode ) -> int:
        count = 1
        for child in node.children.values():
            count += self._count_nodes( child )
        return count

    def auto_refresh_data( self, interval_seconds: int ):
        while True:
            time.sleep( interval_seconds )
            print( f"\n[{datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}] Auto-refresh triggered..." )
            self.rebuild_cache()

    # ---- Tree lookup ----

    def _resolve_path_segments( self, segments: List[ str ] ) -> Optional[ TreeNode ]:
        """
        Walk the cache given a list of URL path segments.

        segments[0] = subproject_name
        segments[1:] = subdirs / filename

        Returns TreeNode or None if not found.
        """
        if not segments:
            return None

        subproject_name = segments[ 0 ]
        with self._cache_lock:
            node = self._cache.get( subproject_name )
            if node is None:
                return None

        for segment in segments[ 1: ]:
            if node.is_file:
                return None
            child = node.children.get( segment )
            if child is None:
                return None
            node = child

        return node

    # ---- Rendering: common CSS + helpers ----

    def _css_common( self ) -> str:
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'Arial', sans-serif;
            background-color: #000000;
            color: #FFFFFF;
            line-height: 1.6;
            padding: 0;
            margin: 0;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        a { color: inherit; text-decoration: none; }

        h1 {
            font-size: 80px;
            font-weight: 900;
            letter-spacing: -2px;
            text-transform: uppercase;
            color: #FFFFFF;
            border: 8px solid #FFFFFF;
            padding: 30px;
            margin: 20px 0 40px 0;
            background-color: #000000;
            line-height: 1.1;
            word-wrap: break-word;
        }
        h1 .pink { color: #FF007F; }

        .last-updated {
            color: #B0B0B0;
            font-size: 14px;
            margin-top: 0.25em;
            margin-bottom: 1.5em;
        }

        h2 {
            font-size: 28px;
            font-weight: 900;
            text-transform: uppercase;
            color: #000000;
            background-color: #FFFFFF;
            padding: 18px 22px;
            margin: 40px 0 15px 0;
            border-left: 12px solid #000000;
            letter-spacing: 2px;
        }

        h3 {
            font-size: 16px;
            font-weight: 900;
            text-transform: uppercase;
            color: #000000;
            background-color: #E8E8E8;
            padding: 10px 14px;
            margin: 20px 0 8px 0;
            border-left: 6px solid #000000;
            letter-spacing: 2px;
        }

        .crumb-bar {
            margin-bottom: 18px;
            padding: 12px 16px;
            background-color: #1A1A1A;
            border: 2px solid #FFFFFF;
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #B0B0B0;
        }
        .crumb-bar a { color: #FFFFFF; }
        .crumb-bar a:hover { color: #FF007F; }
        .crumb-bar .sep { margin: 0 8px; color: #606060; }
        .crumb-bar .current { color: #FF007F; }

        .home-link {
            display: inline-block;
            margin: 8px 0;
            padding: 10px 18px;
            background-color: #000000;
            color: #FFFFFF;
            border: 3px solid #FFFFFF;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 14px;
        }
        .home-link:hover { background-color: #FF007F; }

        .card-grid {
            display: grid;
            grid-template-columns: repeat( auto-fill, minmax( 300px, 1fr ) );
            gap: 16px;
            margin: 15px 0 30px 0;
        }

        .card {
            background-color: #FFFFFF;
            border: 4px solid #000000;
            padding: 22px;
            text-align: left;
            display: block;
            transition: background-color 0.15s, transform 0.15s;
        }
        .card:hover {
            background-color: #FF007F;
            transform: translateY( -3px );
            box-shadow: 6px 6px 0 #FFFFFF;
        }
        .card .title {
            color: #000000;
            font-size: 18px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
            word-wrap: break-word;
        }
        .card:hover .title { color: #FFFFFF; }
        .card .subtitle {
            color: #333333;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 6px;
            word-wrap: break-word;
        }
        .card:hover .subtitle { color: #FFFFFF; }
        .dir-subtitle {
            color: #B0B0B0;
            font-size: 15px;
            font-weight: 600;
            margin: -10px 0 25px 0;
        }
        .card .hint {
            color: #606060;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .card:hover .hint { color: #FFFFFF; }

        .card.empty {
            background-color: #2A2A2A;
            border-color: #4A4A4A;
            cursor: not-allowed;
            pointer-events: none;
        }
        .card.empty .title { color: #808080; }
        .card.empty .hint { color: #606060; }

        .file-group {
            background-color: #FFFFFF;
            color: #000000;
            border: 4px solid #000000;
            margin: 0 0 25px 0;
        }
        .file-group .file-row {
            border-top: 1px solid #CCCCCC;
            padding: 12px 18px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .file-group .file-row:first-child { border-top: none; }
        .file-group .file-row:hover { background-color: #F0F0F0; }
        .file-name {
            font-weight: 700;
            flex: 1;
            word-break: break-all;
        }
        .file-size {
            color: #606060;
            font-size: 13px;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            min-width: 80px;
            text-align: right;
        }
        .file-actions a {
            padding: 6px 12px;
            border: 2px solid #000000;
            background-color: #000000;
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .file-actions a:hover { background-color: #FF007F; border-color: #FF007F; }
        .file-description {
            color: #555555;
            font-size: 13px;
            margin-top: 4px;
            width: 100%;
        }

        .nav-row {
            display: flex;
            justify-content: flex-start;
            margin: 15px 0;
        }
        .nav-row.bottom {
            justify-content: center;
            margin-top: 50px;
        }

        .no-data-banner {
            background-color: #2A2A2A;
            border: 4px dashed #FFFFFF;
            padding: 40px;
            margin: 20px 0;
            text-align: center;
            color: #B0B0B0;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        footer {
            margin-top: 60px;
            padding: 40px;
            text-align: center;
            background-color: #FFFFFF;
            border-top: 8px solid #000000;
            color: #000000;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 1px;
        }

        .methods-panel {
            background-color: #FFFFFF;
            border: 4px solid #000000;
            margin: 0 0 30px 0;
        }
        .methods-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: #000000;
            padding: 12px 18px;
        }
        .methods-title {
            color: #FFFFFF;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 16px;
        }
        .methods-download {
            padding: 6px 12px;
            border: 2px solid #FFFFFF;
            background-color: #000000;
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .methods-download:hover { background-color: #FF007F; border-color: #FF007F; }
        .methods-panel summary {
            cursor: pointer;
            padding: 12px 18px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 13px;
            color: #000000;
            background-color: #E8E8E8;
            border-bottom: 2px solid #000000;
        }
        .methods-panel summary:hover { color: #FF007F; }
        .methods-panel pre {
            margin: 0;
            padding: 18px;
            max-height: 500px;
            overflow: auto;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 12.5px;
            line-height: 1.45;
            color: #000000;
            background-color: #FFFFFF;
            white-space: pre;
        }
"""

    def _page_shell( self, title: str, body_inner: str ) -> str:
        """Wrap body content with <html>, <head>, footer."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{htmllib.escape( title )}</title>
    <style>{self._css_common()}</style>
</head>
<body>
    <div class="container">
{body_inner}
    </div>
{self._footer_html()}
</body>
</html>
"""

    def _footer_html( self ) -> str:
        credits = [ f"AI: {self.config.credits_ai.upper()}" ]
        if self.config.credits_human:
            credits.append( f"HUMAN: {self.config.credits_human.upper()}" )
        return f"""
    <footer>
        GIGANTIC DATA SERVER<br>
        {'<br>'.join( credits )}
    </footer>
"""

    def _breadcrumb_html( self, segments: List[ str ] ) -> str:
        """
        Render a breadcrumb bar.

        segments = [ subproject, dir1, dir2, ... ]
        Each segment except the last is a link.
        """
        if not segments:
            return ''
        parts = [ '<a href="/">GIGANTIC DATA</a>' ]
        accumulated = ''
        for i, seg in enumerate( segments ):
            accumulated = accumulated + '/' + urllib.parse.quote( seg )
            label = htmllib.escape( self._clean_display_name( seg ) )
            is_last = ( i == len( segments ) - 1 )
            if is_last:
                parts.append( f'<span class="current">{label}</span>' )
            else:
                parts.append( f'<a href="{accumulated}/">{label}</a>' )
        return '<div class="crumb-bar">' + '<span class="sep">&gt;</span>'.join( parts ) + '</div>'

    def _home_link_html( self, position: str = 'top' ) -> str:
        # HOME links retired — the breadcrumb bar already links back to "GIGANTIC DATA".
        return ''

    # ---- Subproject methods document ----

    def _methods_file_for( self, subproject_name: str ) -> Optional[ Path ]:
        """
        Return the path to a subproject's served methods document, if present.

        Convention: subprojects/<sp>/methods-<sp>.txt committed at the subproject
        root (NOT inside upload_to_server/). Only subprojects in the configured
        allowlist are eligible (guards the /methods/ route against traversal).
        """
        if subproject_name not in self.config.subproject_order:
            return None
        candidate = self.subprojects_dir / subproject_name / f"methods-{subproject_name}.txt"
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            return None
        return None

    def _methods_panel_html( self, subproject_name: str ) -> str:
        """
        Render the subproject methods document as a panel at the TOP of the
        subproject page (expanded, scrollable) with a download link. Returns ''
        when the subproject has no methods-<sp>.txt.
        """
        methods_path = self._methods_file_for( subproject_name )
        if methods_path is None:
            return ''
        try:
            text = methods_path.read_text( encoding = 'utf-8', errors = 'replace' )
        except OSError:
            return ''
        download_url = '/methods/' + urllib.parse.quote( subproject_name )
        return f"""
        <div class="methods-panel">
            <div class="methods-head">
                <span class="methods-title">Methods</span>
                <a class="methods-download" href="{download_url}">Download .txt</a>
            </div>
            <details open>
                <summary>{htmllib.escape( methods_path.name )} &mdash; click to collapse</summary>
                <pre>{htmllib.escape( text )}</pre>
            </details>
        </div>
"""

    # ---- Landing page ----

    def generate_landing_page( self ) -> str:
        name_parts = self.config.project_name.split( ' ', 1 )
        if len( name_parts ) == 2:
            title_html = f'{htmllib.escape( name_parts[ 0 ] )} <span class="pink">{htmllib.escape( name_parts[ 1 ] )}</span>'
        else:
            title_html = htmllib.escape( self.config.project_name )

        cards_html = []
        with self._cache_lock:
            built_at = self._cache_built_at
            for subproject_name in self.config.subproject_order:
                node = self._cache.get( subproject_name )
                display = htmllib.escape( self._clean_display_name( subproject_name ) )
                has_data = node is not None and len( node.children ) > 0

                if not has_data:
                    if not self.config.show_empty_subprojects:
                        continue
                    # Dimmed card, not clickable
                    cards_html.append( f"""
            <div class="card empty">
                <div class="title">{display}</div>
                <div class="hint">NO DATA YET</div>
            </div>
""" )
                else:
                    url = '/' + urllib.parse.quote( subproject_name ) + '/'
                    cards_html.append( f"""
            <a class="card" href="{url}">
                <div class="title">{display}</div>
                <div class="hint">{len( node.children )} ITEMS &rsaquo;</div>
            </a>
""" )

        if built_at is not None:
            last_updated_html = (
                f'<p class="last-updated">Last updated: '
                f'{htmllib.escape( built_at.strftime( "%Y-%m-%d %H:%M:%S" ) )} (server local time)</p>'
            )
        else:
            last_updated_html = ''

        body = f"""
        <h1>{title_html}</h1>
        {last_updated_html}

        <h2>SUBPROJECTS</h2>
        <div class="card-grid">
{''.join( cards_html )}
        </div>
"""
        return self._page_shell( self.config.project_name, body )

    # ---- Drill-down page (hub OR leaf OR mixed) ----

    def generate_directory_page( self, segments: List[ str ] ) -> str:
        """
        Render the page for a directory at the given URL path segments.

        - If the directory contains only subdirectories: hub mode (cards).
        - If only files: leaf mode (file list, grouped by file_category or extension).
        - If mixed: hub first, then a trailing file section.
        """
        node = self._resolve_path_segments( segments )

        if node is None:
            return self.generate_404_page()

        if node.is_file:
            # User navigated straight to a file path — redirect-like: show download card
            return self.generate_file_stub_page( segments, node )

        title = ' · '.join( self._clean_display_name( s ) for s in segments )
        body_parts = []

        body_parts.append( self._home_link_html( 'top' ) )
        body_parts.append( self._breadcrumb_html( segments ) )

        # Title
        last_display = htmllib.escape( self._clean_display_name( segments[ -1 ] ) )
        body_parts.append( f'<h1>{last_display}</h1>' )
        # Optional folder descriptor (subtitle) from the __DIR__ sidecar row
        if node.description:
            body_parts.append( f'<div class="dir-subtitle">{htmllib.escape( node.description )}</div>' )

        # Subproject methods document, served at the TOP of the subproject page
        # (methods-<subproject>.txt at the subproject root, if present).
        if len( segments ) == 1:
            methods_html = self._methods_panel_html( segments[ 0 ] )
            if methods_html:
                body_parts.append( methods_html )

        # Partition children into subdirs and files
        subdirs = [ child for child in node.children.values() if not child.is_file ]
        files = [ child for child in node.children.values() if child.is_file ]

        if not subdirs and not files:
            body_parts.append( '<div class="no-data-banner">NO DATA PUBLISHED IN THIS DIRECTORY YET</div>' )
        else:
            # Subdirs as cards
            if subdirs:
                subdirs_sorted = sorted( subdirs, key = lambda c: c.name.lower() )
                cards = []
                for child in subdirs_sorted:
                    child_url_segments = segments + [ child.name ]
                    url = '/' + '/'.join( urllib.parse.quote( s ) for s in child_url_segments ) + '/'
                    child_display = htmllib.escape( self._clean_display_name( child.name ) )
                    # Optional folder descriptor (subtitle) from the __DIR__ sidecar row
                    subtitle_html = ''
                    if child.description:
                        subtitle_html = f'<div class="subtitle">{htmllib.escape( child.description )}</div>'
                    # Count items as a hint
                    total_items = self._count_direct_items( child )
                    hint = f'{total_items} ITEMS &rsaquo;'
                    cards.append( f"""
            <a class="card" href="{url}">
                <div class="title">{child_display}</div>
                {subtitle_html}
                <div class="hint">{hint}</div>
            </a>
""" )
                heading = self._children_section_heading( segments, subdirs_sorted )
                body_parts.append( f'<h2>{heading}</h2>' )
                body_parts.append( f'<div class="card-grid">{"".join( cards )}</div>' )

            # Files grouped by category
            if files:
                body_parts.append( self._render_file_groups( segments, files ) )

        body_parts.append( self._home_link_html( 'bottom' ) )

        return self._page_shell( title or self.config.project_name, '\n'.join( body_parts ) )

    def _count_direct_items( self, node: TreeNode ) -> int:
        """Count files + subdirs that are direct children of `node`."""
        return len( node.children )

    def _children_section_heading( self, segments: List[ str ], children: List[ TreeNode ] ) -> str:
        """
        Pick an h2 heading for the children-cards section that describes what
        the children ARE (not the parent).

        Heuristics (first match wins):
          - All children named STEP_*       → 'STEPS'
          - All children named BLOCK_*      → 'BLOCKS'
          - All children named workflow-*   → 'WORKFLOWS'
          - All children named structure_NNN → 'STRUCTURES'
          - All children look like N-output or *-output → 'OUTPUTS'
          - depth 1, parent starts with 'trees_' → strip 'trees_' and uppercase
            (e.g. 'trees_gene_families' → 'GENE FAMILIES')
          - Otherwise → 'SECTIONS'
        """
        if not children:
            return 'SECTIONS'
        names = [ child.name for child in children ]
        if all( n.startswith( 'STEP_' ) for n in names ):
            return 'STEPS'
        if all( n.startswith( 'BLOCK_' ) for n in names ):
            return 'BLOCKS'
        if all( n.startswith( 'workflow-' ) for n in names ):
            return 'WORKFLOWS'
        structure_regex = re.compile( r'^structure_\d+$' )
        if all( structure_regex.search( n ) for n in names ):
            return 'STRUCTURES'
        output_regex = re.compile( r'^\d+[-_]output$|-output$' )
        if all( output_regex.search( n ) for n in names ):
            return 'OUTPUTS'
        if len( segments ) == 1:
            subproject_name = segments[ 0 ]
            if subproject_name.startswith( 'trees_' ):
                stripped = subproject_name[ len( 'trees_' ): ]
                return stripped.replace( '_', ' ' ).upper()
        return 'SECTIONS'

    def _render_file_groups( self, segments: List[ str ], files: List[ TreeNode ] ) -> str:
        """Render files grouped by category (or by extension fallback) into <h3> subsections."""
        # Group
        groups: Dict[ str, List[ TreeNode ] ] = {}
        for f in files:
            key = f.category if f.category else f.real_path.suffix.lstrip( '.' ).upper() or 'FILE'
            groups.setdefault( key, [] ).append( f )

        # Sort groups: by preferred category order (substantive outputs first,
        # summary/qc/log sections last), then alphabetical within each tier.
        # Unknown categories slot into the middle tier (50).
        category_priority = {
            'visualization': 0,
            'tree': 10,
            'alignment': 20,
            'data': 30,
            'summary': 90,
            'qc': 95,
            'log': 100,
        }
        sorted_group_keys = sorted(
            groups.keys(),
            key = lambda k: ( category_priority.get( k.lower(), 50 ), k.lower() )
        )

        out = [ '<h2>FILES</h2>' ]
        for key in sorted_group_keys:
            group_files = sorted( groups[ key ], key = lambda f: ( f.order, f.name.lower() ) )
            out.append( f'<h3>{htmllib.escape( key.upper() )}</h3>' )
            out.append( '<div class="file-group">' )
            for f in group_files:
                download_url = '/download/' + '/'.join( urllib.parse.quote( s ) for s in segments + [ f.name ] )
                display = htmllib.escape( f.display_name or f.name )
                size = self._format_size( f.size_bytes )
                desc_html = ''
                if f.description:
                    desc_html = f'<div class="file-description">{htmllib.escape( f.description )}</div>'
                # Offer an on-the-fly Excel (.xlsx) conversion for tabular files.
                excel_action = ''
                if f.real_path.suffix.lower() in ( '.tsv', '.csv' ):
                    excel_url = '/excel/' + '/'.join( urllib.parse.quote( s ) for s in segments + [ f.name ] )
                    excel_action = f'<a href="{excel_url}">EXCEL</a>'
                out.append( f"""
                <div class="file-row">
                    <div class="file-name">
                        {display}
                        {desc_html}
                    </div>
                    <div class="file-size">{size}</div>
                    <div class="file-actions">
                        {excel_action}
                        <a href="{download_url}">DOWNLOAD</a>
                    </div>
                </div>
""" )
            out.append( '</div>' )
        return '\n'.join( out )

    def generate_file_stub_page( self, segments: List[ str ], node: TreeNode ) -> str:
        """If user hits a file URL (not /download/), show a mini page with a download button."""
        parent_segments = segments[ :-1 ]
        download_href = '/download/' + '/'.join( urllib.parse.quote( s ) for s in segments )
        excel_action = ''
        if node.real_path.suffix.lower() in ( '.tsv', '.csv' ):
            excel_href = '/excel/' + '/'.join( urllib.parse.quote( s ) for s in segments )
            excel_action = f'<a href="{excel_href}">EXCEL</a> '
        body = [
            self._home_link_html( 'top' ),
            self._breadcrumb_html( segments ),
            f'<h1>{htmllib.escape( node.display_name or node.name )}</h1>',
            '<div class="file-group">',
            f'<div class="file-row"><div class="file-name">{htmllib.escape( node.name )}</div>',
            f'<div class="file-size">{self._format_size( node.size_bytes )}</div>',
            f'<div class="file-actions">{excel_action}<a href="{download_href}">DOWNLOAD</a></div></div>',
            '</div>',
            self._home_link_html( 'bottom' ),
        ]
        return self._page_shell( node.name, '\n'.join( body ) )

    def generate_excel_error_page( self, segments: List[ str ], filename: str, problems: List[ str ] ) -> str:
        """Shown when an .xlsx conversion is REFUSED so no data is lost or
        corrupted. Lists exactly what blocked it and links the original TSV."""
        download_url = '/download/' + '/'.join( urllib.parse.quote( s ) for s in segments )
        problem_items = '\n'.join( f'<li>{htmllib.escape( p )}</li>' for p in problems )
        body = [
            self._home_link_html( 'top' ),
            self._breadcrumb_html( segments ),
            '<h1>EXCEL &mdash; <span class="pink">REFUSED</span></h1>',
            '<div class="no-data-banner">THIS TABLE WAS NOT CONVERTED TO EXCEL BECAUSE DOING SO WOULD LOSE OR CORRUPT DATA. DOWNLOAD THE ORIGINAL TSV INSTEAD.</div>',
            f'<div class="file-group"><div class="file-row"><div class="file-name">{htmllib.escape( filename )}'
            f'<div class="file-description"><ul>{problem_items}</ul></div></div>'
            f'<div class="file-actions"><a href="{download_url}">DOWNLOAD ORIGINAL TSV</a></div></div></div>',
            self._home_link_html( 'bottom' ),
        ]
        return self._page_shell( 'Excel Refused', '\n'.join( body ) )

    def generate_404_page( self ) -> str:
        body = [
            self._home_link_html( 'top' ),
            '<h1>404 &mdash; <span class="pink">NOT FOUND</span></h1>',
            '<div class="no-data-banner">THE PATH YOU REQUESTED DOES NOT EXIST IN THE SERVER TREE.</div>',
            self._home_link_html( 'bottom' ),
        ]
        return self._page_shell( 'Not Found', '\n'.join( body ) )

    # ---- Download handler ----

    def resolve_download_target( self, segments: List[ str ] ) -> Optional[ TreeNode ]:
        """Return the TreeNode for a file at given segments, or None."""
        node = self._resolve_path_segments( segments )
        if node is None or not node.is_file:
            return None
        return node

    # ---- Utilities ----

    def get_hostname( self ) -> str:
        try:
            hostname = socket.gethostname()
            if hostname and hostname != 'localhost':
                return hostname
            return socket.gethostname()
        except Exception:
            return 'localhost'


# ============================================================================
# HTTP handling
# ============================================================================

CONTENT_TYPES = {
    '.txt': 'text/plain', '.tsv': 'text/tab-separated-values', '.csv': 'text/csv',
    '.pdf': 'application/pdf', '.svg': 'image/svg+xml', '.png': 'image/png',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.html': 'text/html',
    '.json': 'application/json', '.xml': 'application/xml',
    '.aa': 'text/plain', '.fasta': 'text/plain', '.fa': 'text/plain',
    '.faa': 'text/plain', '.fna': 'text/plain',
    '.mafft': 'text/plain', '.clipkit-smartgap': 'text/plain',
    '.fasttree': 'text/plain', '.treefile': 'text/plain', '.veryfasttree': 'text/plain',
    '.nwk': 'text/plain', '.iqtree': 'text/plain',
    '.log': 'text/plain', '.md': 'text/markdown',
    '.gz': 'application/gzip', '.zip': 'application/zip', '.tar': 'application/x-tar',
}


def make_request_handler( server_instance: GIGANTICServer ):
    static_dir = Path( __file__ ).parent / 'static'

    class RequestHandler( http.server.SimpleHTTPRequestHandler ):

        def log_message( self, format, *args ):
            # Suppress default request logging
            pass

        def _write_html( self, html: str, status: int = 200 ):
            self.send_response( status )
            self.send_header( 'Content-type', 'text/html; charset=utf-8' )
            self.end_headers()
            self.wfile.write( html.encode( 'utf-8' ) )

        def do_GET( self ):
            parsed = urllib.parse.urlparse( self.path )
            path = parsed.path

            # Landing
            if path in ( '/', '/index.html' ):
                self._write_html( server_instance.generate_landing_page() )
                return

            # Static assets
            if path.startswith( '/static/' ):
                rel = path[ len( '/static/' ): ]
                file_path = static_dir / rel
                if file_path.exists() and file_path.is_file():
                    self.send_response( 200 )
                    self.send_header( 'Content-type', CONTENT_TYPES.get( file_path.suffix.lower(), 'application/octet-stream' ) )
                    self.end_headers()
                    with open( file_path, 'rb' ) as f:
                        self.wfile.write( f.read() )
                    return
                self._write_html( server_instance.generate_404_page(), 404 )
                return

            # Excel conversion (on-the-fly TSV/CSV -> .xlsx, strict refuse-and-report)
            if path.startswith( '/excel/' ):
                raw_segments = [ p for p in path[ len( '/excel/' ): ].split( '/' ) if p ]
                segments = [ urllib.parse.unquote( s ) for s in raw_segments ]
                node = server_instance.resolve_download_target( segments )
                if node is None:
                    self._write_html( server_instance.generate_404_page(), 404 )
                    return

                file_path = node.real_path
                if file_path.suffix.lower() not in ( '.tsv', '.csv' ):
                    self._write_html(
                        server_instance.generate_excel_error_page(
                            segments, file_path.name,
                            [ 'Only .tsv and .csv files can be converted to Excel.' ] ),
                        400 )
                    return

                try:
                    ok, report, xlsx_bytes = tsv_to_xlsx.convert_path_to_bytes( file_path )
                except Exception as conversion_error:
                    self._write_html(
                        server_instance.generate_excel_error_page(
                            segments, file_path.name,
                            [ f'Unexpected error during conversion: {conversion_error}' ] ),
                        500 )
                    return

                if not ok:
                    self._write_html(
                        server_instance.generate_excel_error_page( segments, file_path.name, report ),
                        422 )
                    return

                xlsx_name = file_path.stem + '.xlsx'
                self.send_response( 200 )
                self.send_header( 'Content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' )
                self.send_header( 'Content-Length', str( len( xlsx_bytes ) ) )
                self.send_header( 'Content-Disposition', f'attachment; filename="{xlsx_name}"' )
                self.end_headers()
                try:
                    self.wfile.write( xlsx_bytes )
                except ( BrokenPipeError, ConnectionResetError ):
                    return
                return

            # Download
            if path.startswith( '/download/' ):
                raw_segments = [ p for p in path[ len( '/download/' ): ].split( '/' ) if p ]
                segments = [ urllib.parse.unquote( s ) for s in raw_segments ]
                node = server_instance.resolve_download_target( segments )
                if node is None:
                    self._write_html( server_instance.generate_404_page(), 404 )
                    return

                file_path = node.real_path
                try:
                    size = file_path.stat().st_size
                except OSError:
                    self._write_html( server_instance.generate_404_page(), 404 )
                    return

                content_type = CONTENT_TYPES.get( file_path.suffix.lower(), 'application/octet-stream' )
                self.send_response( 200 )
                self.send_header( 'Content-type', content_type )
                self.send_header( 'Content-Length', str( size ) )
                self.send_header( 'Content-Disposition', f'attachment; filename="{file_path.name}"' )
                self.end_headers()
                CHUNK_SIZE = 1024 * 1024
                with open( file_path, 'rb' ) as f:
                    while True:
                        chunk = f.read( CHUNK_SIZE )
                        if not chunk:
                            break
                        try:
                            self.wfile.write( chunk )
                        except ( BrokenPipeError, ConnectionResetError ):
                            return
                return

            # Subproject methods document (subprojects/<sp>/methods-<sp>.txt)
            if path.startswith( '/methods/' ):
                raw_segments = [ p for p in path[ len( '/methods/' ): ].split( '/' ) if p ]
                if len( raw_segments ) != 1:
                    self._write_html( server_instance.generate_404_page(), 404 )
                    return
                subproject_name = urllib.parse.unquote( raw_segments[ 0 ] )
                methods_path = server_instance._methods_file_for( subproject_name )
                if methods_path is None:
                    self._write_html( server_instance.generate_404_page(), 404 )
                    return
                try:
                    data = methods_path.read_bytes()
                except OSError:
                    self._write_html( server_instance.generate_404_page(), 404 )
                    return
                self.send_response( 200 )
                self.send_header( 'Content-type', 'text/plain; charset=utf-8' )
                self.send_header( 'Content-Length', str( len( data ) ) )
                self.send_header( 'Content-Disposition', f'attachment; filename="{methods_path.name}"' )
                self.end_headers()
                try:
                    self.wfile.write( data )
                except ( BrokenPipeError, ConnectionResetError ):
                    return
                return

            # Drill-down directory page
            raw_segments = [ p for p in path.split( '/' ) if p ]
            segments = [ urllib.parse.unquote( s ) for s in raw_segments ]
            if not segments:
                self._write_html( server_instance.generate_landing_page() )
                return

            self._write_html( server_instance.generate_directory_page( segments ) )

    return RequestHandler


def main():
    parser = argparse.ArgumentParser( description = 'GIGANTIC Data Server (drill-down hierarchy)' )
    parser.add_argument( '--config', type = str, default = None )
    parser.add_argument( '--port', type = int, default = None )
    parser.add_argument( '--subprojects-dir', type = str, default = None )
    args = parser.parse_args()

    script_dir = Path( __file__ ).parent
    config_path = Path( args.config ) if args.config else script_dir.parent / 'START_HERE-server_config.yaml'

    config = ServerConfig( config_path )

    if args.subprojects_dir:
        subprojects_dir = Path( args.subprojects_dir )
    else:
        subprojects_dir = script_dir.parent.parent / 'subprojects'

    if not subprojects_dir.exists():
        print( f"ERROR: Subprojects directory does not exist: {subprojects_dir}" )
        sys.exit( 1 )

    server = GIGANTICServer( config = config, subprojects_dir = subprojects_dir, port_override = args.port )

    # Initial cache build
    print( "Building initial directory tree cache..." )
    server.rebuild_cache()

    handler_cls = make_request_handler( server )

    # Threaded server: each request runs in its own thread so one slow
    # request (or a stuck client mid-read) can't freeze the whole server.
    # Daemon threads die when the main process exits.
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True
    with socketserver.ThreadingTCPServer( ( '', server.port ), handler_cls ) as httpd:
        hostname = server.get_hostname()
        refresh = config.refresh_interval_seconds

        print( "=" * 80 )
        print( f"{config.project_name} SERVER STARTED" )
        print( "=" * 80 )
        print( f"Hostname: {hostname}" )
        print( f"Port:     {server.port}" )
        print()
        print( f"  SSH tunnel:    ssh -L {server.port}:{hostname}:{server.port} YOUR_USER@YOUR_HOST" )
        print( f"  Open browser:  http://localhost:{server.port}/" )
        print()
        print( f"Auto-refresh every {refresh} seconds" )
        print( "=" * 80 )

        refresh_thread = threading.Thread(
            target = server.auto_refresh_data, args = ( refresh, ), daemon = True
        )
        refresh_thread.start()

        httpd.serve_forever()


if __name__ == '__main__':
    main()
