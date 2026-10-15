#!/usr/bin/env python3
"""Small offline fixture, not a WasmEdge implementation."""
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version="1.1")
parser.add_argument("--name", required=True)
args = parser.parse_args()
print(f"Hello, {args.name}!")
