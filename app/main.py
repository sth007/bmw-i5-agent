from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import BmwI5Agent


def main() -> None:
    agent = BmwI5Agent()
    best_offer, score = agent.pick_best_offer()
    print(f"Best offer: {best_offer.model} ({score} points)")


if __name__ == "__main__":
    main()
