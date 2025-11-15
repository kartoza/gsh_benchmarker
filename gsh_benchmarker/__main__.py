#!/usr/bin/env python3
"""
GSH Benchmarker Suite - Main module entry point

Allows running the benchmarker as a module:
    python3 -m gsh_benchmarker [args...]

This is equivalent to:
    python3 -m gsh_benchmarker.cli [args...]
"""

from .cli import main

if __name__ == "__main__":
    main()