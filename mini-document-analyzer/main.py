import asyncio
import json
import sys
import os
from cli import parse_args, validate_input
from analyzer import analyze_document

async def export_json(data: dict, output_path: str) -> None:
    await asyncio.to_thread(_write_json, data, output_path)

def _write_json(data: dict, output_path: str) -> None:
    with open(output_path, mode="w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def main() -> None:
    """
    Main entry point. Handles CLI, validation, analysis, and output.
    Need developer A analysis logic to replace the _stub_result once available.
    """
    input_path, output_path = parse_args()

    validate_input(input_path)

    try:
        result = await analyze_document(input_path)
    except Exception as e:
        print(f"Error during document analysis: {e}")
        sys.exit(1)

    try:
        await export_json(result, output_path)
    except OSError as e:
        print(f"Error: Could not write output file '{output_path}': {e}")
        sys.exit(1)

    print(f"Analysis complete. Results saved to '{output_path}'.")



if __name__ == "__main__":
    asyncio.run(main())