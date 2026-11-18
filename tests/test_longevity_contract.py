#!/usr/bin/env python3
"""Cross-platform longevity assessment contract.

The backend test suite compares the canonical assessment to this fixture, and the iOS test suite
decodes the same bytes into its presentation model. Keeping the two copies byte-identical is what
proves the clients receive the same facts rather than two independently drifting examples.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "strength-training-app/tests/fixtures/intelligence/longevity_assessment.ok.json"
IOS = ROOT / "StrengthApp/StrengthAppTests/Fixtures/longevity_assessment.ok.json"


class LongevityContractTests(unittest.TestCase):
    def test_both_clients_use_the_same_fixture_bytes(self) -> None:
        self.assertTrue(BACKEND.is_file(), BACKEND)
        self.assertTrue(IOS.is_file(), IOS)
        self.assertEqual(BACKEND.read_bytes(), IOS.read_bytes())

    def test_fixture_carries_the_canonical_assessment_states(self) -> None:
        payload = json.loads(BACKEND.read_text(encoding="utf-8"))
        self.assertEqual(payload["as_of"], "2026-11-18")
        self.assertEqual(payload["reference"]["role"], "context, not a target")
        self.assertEqual(payload["last_week"]["relation"], "below")
        self.assertEqual(payload["last_week"]["remaining_minutes"], 10.0)
        self.assertEqual(payload["last_week"]["classified_share"], 1.0)
        self.assertEqual(payload["current_week"]["equivalent_minutes"], 30.0)
        self.assertNotIn("relation", payload["current_week"])
        self.assertEqual(payload["vo2max"]["status"], "current")
        self.assertEqual(payload["vo2max"]["unit"], "ml/kg/min")
        self.assertEqual(payload["vo2max"]["method"], "Apple Watch")
        self.assertIsNone(payload["time_in_zone"])
        self.assertIsNone(payload["patterns"])


if __name__ == "__main__":
    unittest.main()
