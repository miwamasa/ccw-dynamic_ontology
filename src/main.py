#!/usr/bin/env python3
"""
Main entry point for the Dynamic Ontology DSL compiler.

This script reads a DSL file and generates Cypher queries.
"""

import sys
import argparse
from pathlib import Path

from parser import parse_dsl
from codegen import generate_cypher


def compile_dsl_file(input_path: str, output_path: str = None):
    """
    Compile a DSL file to Cypher queries.

    Args:
        input_path: Path to the input DSL file
        output_path: Optional path to write the output Cypher file
    """
    # Read input file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            dsl_text = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse DSL
    try:
        print(f"Parsing {input_path}...", file=sys.stderr)
        ast = parse_dsl(dsl_text)
        print(f"✓ Parsed {len(ast.statements)} statements", file=sys.stderr)
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate Cypher
    try:
        print("Generating Cypher code...", file=sys.stderr)
        cypher_code = generate_cypher(ast)
        print("✓ Cypher code generated successfully", file=sys.stderr)
    except Exception as e:
        print(f"Code generation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cypher_code)
            print(f"✓ Written to {output_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("\n" + "="*60, file=sys.stderr)
        print("Generated Cypher Code:", file=sys.stderr)
        print("="*60 + "\n", file=sys.stderr)
        print(cypher_code)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Dynamic Ontology DSL Compiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compile DSL to Cypher and print to stdout
  python main.py sample.dsl

  # Compile and save to file
  python main.py sample.dsl -o output.cypher

  # Show version
  python main.py --version
        """
    )

    parser.add_argument(
        'input',
        help='Input DSL file path'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output Cypher file path (default: stdout)',
        default=None
    )

    parser.add_argument(
        '--version',
        action='version',
        version='Dynamic Ontology DSL Compiler v1.0.0'
    )

    args = parser.parse_args()

    compile_dsl_file(args.input, args.output)


if __name__ == '__main__':
    main()
