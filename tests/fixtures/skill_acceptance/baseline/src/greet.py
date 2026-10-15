#!/usr/bin/env python3
"""Small offline fixture, not a WasmEdge implementation."""
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version="1.0")
parser.add_argument("name")
args = parser.parse_args()
print(f"Hello, {args.name}!")
