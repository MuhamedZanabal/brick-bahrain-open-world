import unittest

from tools.asset_lab.evaluate_golden_master_gate import evaluate_evidence


ASSET_IDS = [
    "bh_traditional_projecting_window_01",
    "bh_souq_shop_gold_01",
    "bh_waterfront_tower_a_01",
    "bh_supermarket_storefront_a_01",
    "bh_cr_skyscraper_tower_01",
]


def passing_evidence():
    return {
        "technical_validation": {"passed": True, "validated_assets": 45, "texture_count": 24},
        "protected_authority": {"passed": True},
        "godot_import": {"passed": True, "imported_assets": ASSET_IDS},
        "android_runtime": {"passed": True, "visible_assets": ASSET_IDS, "landscape": True},
        "contact_sheets": [
            {"asset_id": asset_id, "profile": "balanced", "lod": 0, "path": f"renders/{asset_id}.png", "sha256": "a" * 64}
            for asset_id in ASSET_IDS
        ],
        "android_screenshots": [
            {"asset_id": asset_id, "path": f"android/{asset_id}.png", "sha256": "b" * 64}
            for asset_id in ASSET_IDS
        ],
        "art_approvals": [
            {"asset_id": asset_id, "approved": True, "reviewer": "human", "criteria": {"visual": True}}
            for asset_id in ASSET_IDS
        ],
    }


class GoldenMasterEvidenceGateTests(unittest.TestCase):
    def test_complete_evidence_opens_mass_regeneration_gate(self):
        result = evaluate_evidence(passing_evidence())
        self.assertTrue(result["mass_regeneration_allowed"], result["failures"])
        self.assertEqual(result["approved_assets"], sorted(ASSET_IDS))
        self.assertEqual(result["failures"], [])

    def test_missing_contact_sheet_keeps_gate_closed(self):
        evidence = passing_evidence()
        evidence["contact_sheets"].pop()
        result = evaluate_evidence(evidence)
        self.assertFalse(result["mass_regeneration_allowed"])
        self.assertTrue(any("contact_sheets" in failure for failure in result["failures"]))

    def test_technical_success_cannot_substitute_for_art_approval(self):
        evidence = passing_evidence()
        evidence["art_approvals"] = []
        result = evaluate_evidence(evidence)
        self.assertFalse(result["mass_regeneration_allowed"])
        self.assertTrue(any("art_approvals" in failure for failure in result["failures"]))

    def test_godot_or_android_failure_keeps_gate_closed(self):
        for section in ("godot_import", "android_runtime"):
            with self.subTest(section=section):
                evidence = passing_evidence()
                evidence[section]["passed"] = False
                result = evaluate_evidence(evidence)
                self.assertFalse(result["mass_regeneration_allowed"])
                self.assertTrue(any(section in failure for failure in result["failures"]))

    def test_duplicate_or_wrong_profile_contact_sheets_fail(self):
        evidence = passing_evidence()
        evidence["contact_sheets"][0]["profile"] = "high"
        evidence["contact_sheets"][1]["asset_id"] = evidence["contact_sheets"][0]["asset_id"]
        result = evaluate_evidence(evidence)
        self.assertFalse(result["mass_regeneration_allowed"])
        self.assertTrue(any("contact_sheets" in failure for failure in result["failures"]))


if __name__ == "__main__":
    unittest.main()
