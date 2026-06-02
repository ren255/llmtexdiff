"""
sample/latex.py

Simple script to test LaTeX compilation with Japanese text.
Usage:
    python -m app.sample.latex "Your LaTeX content here"
    python -m app.sample.latex --file path/to/latex.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add parent directory to path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from the module to avoid circular imports from __init__.py
import importlib.util

spec = importlib.util.spec_from_file_location(
    "latex_service", Path(__file__).parent.parent / "services" / "latex.py"
)
latex_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(latex_module)
compile_tex = latex_module.compile_tex
LatexCompileError = latex_module.LatexCompileError


def main():
    parser = argparse.ArgumentParser(description="Test LaTeX compilation")
    parser.add_argument("content", nargs="?", help="LaTeX content to compile")
    parser.add_argument("--file", "-f", help="Read LaTeX content from file")
    args = parser.parse_args()

    if args.file:
        tex = Path(args.file).read_text(encoding="utf-8")
    elif args.content:
        tex = args.content
    else:
        # Default test content
        tex = r"""
問題 2 $x^2 + y^2 = 1$ のとき、$x^2 - 2y$ の最大値、最小値を求めよ。

$x^2 + y^2 = 1$ より、$x^2 = 1 - y^2$

$x^2 - 2y = (1 - y^2) - 2y = -y^2 - 2y + 1$

$= -(y + 1)^2 + 2$

よって、最大値 2 ($y = -1$ のとき)
"""

    print("=" * 60)
    print("Testing LaTeX compilation...")
    print("=" * 60)
    print(f"\nInput ({len(tex)} chars):")
    print(tex)
    print("\n" + "-" * 60)

    try:
        pdf_bytes = compile_tex(tex)
        output = Path("output.pdf")
        output.write_bytes(pdf_bytes)
        print(f"\nSUCCESS! PDF saved to {output} ({len(pdf_bytes)} bytes)")
    except LatexCompileError as e:
        print(f"\nFAILED: {e}")
        if e.stdout:
            print("\n--- STDOUT ---")
            print(e.stdout)
        if e.stderr:
            print("\n--- STDERR ---")
            print(e.stderr)


if __name__ == "__main__":
    main()
