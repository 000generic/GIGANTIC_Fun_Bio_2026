#!/usr/bin/env python3
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 09 | Purpose: Write workflow run log to ai/logs/ (per gigantic_conventions §45)
# Human: Eric Edsinger

"""
Write Workflow Run Log (per gigantic_conventions §45)

Creates a timestamped log file documenting each workflow run for transparency
and reproducibility. Written to ai/logs/ within this workflow directory.

Usage:
    python3 006_ai-python-write_run_log.py \
        --workflow-name WORKFLOW_NAME \
        --subproject-name SUBPROJECT_NAME \
        --project-name PROJECT_NAME \
        --status success|failure \
        [--input-summary "..."] [--output-summary "..."] [--error-message "..."]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path


def write_run_log(
    workflow_name: str,
    subproject_name: str,
    project_name: str,
    status: str,
    input_summary: str = None,
    output_summary: str = None,
    error_message: str = None
) -> Path:
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime( "%Y%m%d_%H%M%S" )
    timestamp_human = timestamp.strftime( "%Y-%m-%d %H:%M:%S" )

    # This script is in ai/scripts/; logs go to ai/logs/
    script_dir = Path( __file__ ).parent
    log_dir = script_dir.parent / "logs"
    log_dir.mkdir( parents = True, exist_ok = True )

    log_filename = f"run_{timestamp_str}-{subproject_name}_{status}.log"
    log_path = log_dir / log_filename

    log_lines = [
        "=" * 80,
        f"GIGANTIC Workflow Run Log - {workflow_name}",
        "=" * 80,
        "",
        "## Run Information",
        "",
        f"Timestamp:      {timestamp_human}",
        f"Project Name:   {project_name}",
        f"Subproject:     {subproject_name}",
        f"Workflow:       {workflow_name}",
        f"Status:         {status.upper()}",
        "",
    ]

    if input_summary:
        log_lines.extend( [ "## Input Summary", "", f"{input_summary}", "" ] )
    if output_summary:
        log_lines.extend( [ "## Output Summary", "", f"{output_summary}", "" ] )
    if error_message:
        log_lines.extend( [ "## Error", "", f"Error Message: {error_message}", "" ] )

    log_lines.extend( [ "=" * 80, f"Log written to: {log_path}", "=" * 80 ] )

    with open( log_path, 'w' ) as output_log:
        output = '\n'.join( log_lines ) + '\n'
        output_log.write( output )

    return log_path


def main():
    parser = argparse.ArgumentParser( description = "Write workflow run log to ai/logs/" )
    parser.add_argument( '--workflow-name', required = True )
    parser.add_argument( '--subproject-name', required = True )
    parser.add_argument( '--project-name', required = True )
    parser.add_argument( '--status', choices = [ 'success', 'failure' ], required = True )
    parser.add_argument( '--input-summary', default = None )
    parser.add_argument( '--output-summary', default = None )
    parser.add_argument( '--error-message', default = None )
    args = parser.parse_args()

    log_path = write_run_log(
        workflow_name = args.workflow_name,
        subproject_name = args.subproject_name,
        project_name = args.project_name,
        status = args.status,
        input_summary = args.input_summary,
        output_summary = args.output_summary,
        error_message = args.error_message
    )
    print( f"Run log written to: {log_path}" )


if __name__ == '__main__':
    main()
