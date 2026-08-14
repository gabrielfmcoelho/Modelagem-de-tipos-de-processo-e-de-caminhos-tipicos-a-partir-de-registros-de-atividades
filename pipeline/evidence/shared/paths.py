from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT


TYPICAL = ROOT / "artifacts" / "typical"


RUN_MANIFEST = TYPICAL / "run_manifest.json"


CLUSTERING = ROOT / "artifacts" / "clustering"


SHUFFLED = "-shuffled"


MAIN_CELLS = ("exp-raw/hdbscan", "exp-raw/kmeans", "exp-raw/leiden",
              "exp-anon/hdbscan", "exp-anon/kmeans", "exp-anon/leiden")
