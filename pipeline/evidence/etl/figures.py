from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean, median
from ...core.paths import ROOT


CORPUS_BIAS = ROOT / "artifacts" / "stats" / "corpus_bias.json"
CORPUS_FUNNEL = ROOT / "artifacts" / "stats" / "corpus_funnel.json"
