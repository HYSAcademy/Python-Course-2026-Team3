import argparse
import os

def parse_args() -> tuple[str, str]:
    """
    Parse CLI arguments.
    Returns (input_path, output_path).
    """
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Analyze a .txt document and export structured JSON report.",
        epilog="Example: python main.py input.txt output.json",
    )

    parser.add_argument(
        "input",
        metavar="input.txt",
        help="Path to the .txt file to analyze",
    )
    parser.add_argument(
        "output",
        metavar="output.json",
        nargs="?",
        default=None,
        help="Path for the JSON output file (optional)",
    )

    args = parser.parse_args()

    input_path: str = args.input
    output_path: str = args.output if args.output else _default_output_path(input_path)

    return input_path, output_path


def _default_output_path(input_path: str) -> str:
    """Generate default output filename: input.analysis.json"""
    base = os.path.splitext(os.path.basename(input_path))[0]
    directory = os.path.dirname(input_path)
    filename = f"{base}.analysis.json"
    return os.path.join(directory, filename) if directory else filename