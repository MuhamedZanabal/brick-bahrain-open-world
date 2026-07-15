import unittest
from pathlib import Path

from tools.asset_lab.render_golden_master_contact_sheets import ASSET_FAMILIES, VIEWS, render_plan


class GoldenMasterRenderPlanTests(unittest.TestCase):
    def test_render_plan_contains_three_views_for_five_assets(self):
        plan = render_plan(Path("build/golden-masters"), Path("build/renders"))
        self.assertEqual(plan["asset_count"], 5)
        self.assertEqual(plan["view_count"], 15)
        self.assertEqual(len(plan["renders"]), 15)
        self.assertEqual(set(ASSET_FAMILIES), {record["asset_id"] for record in plan["renders"]})
        self.assertEqual(set(VIEWS), {record["view"] for record in plan["renders"]})

    def test_plan_reads_only_balanced_lod0_authorities(self):
        plan = render_plan(Path("assets"), Path("renders"))
        for record in plan["renders"]:
            self.assertEqual(record["profile"], "balanced")
            self.assertEqual(record["lod"], 0)
            self.assertEqual(
                record["input"],
                f"assets/balanced/{record['family']}/{record['asset_id']}_lod0.glb",
            )
            self.assertEqual(
                record["output"],
                f"renders/views/{record['asset_id']}__{record['view']}.png",
            )

    def test_contact_sheet_paths_are_unique_and_exact(self):
        plan = render_plan(Path("assets"), Path("renders"))
        sheets = plan["contact_sheets"]
        self.assertEqual(len(sheets), 5)
        self.assertEqual(len({record["path"] for record in sheets}), 5)
        for record in sheets:
            self.assertEqual(record["path"], f"renders/contact-sheets/{record['asset_id']}.png")
            self.assertEqual(record["profile"], "balanced")
            self.assertEqual(record["lod"], 0)


if __name__ == "__main__":
    unittest.main()
