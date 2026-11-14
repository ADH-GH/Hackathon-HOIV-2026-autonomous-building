import json, re, unittest
from pathlib import Path

from building_ops.decisions import ACTIONS, LEVELS
from building_ops.openapi import build


class OpenApiTest(unittest.TestCase):
    def test_spec_follows_the_decision_contract(self):
        spec = build()
        decision = spec["components"]["schemas"]["Decision"]
        self.assertEqual(decision["properties"]["action"]["enum"], list(ACTIONS))
        self.assertEqual(decision["properties"]["autonomy"]["enum"], list(LEVELS))
        for field in ("event_id", "timestamp_utc", "affected_assets", "issue_type", "action", "priority", "reason", "requires_human_approval"):
            self.assertIn(field, decision["required"])

    def test_references_and_path_parameters_resolve(self):
        spec = build()
        refs = set(re.findall(r"#/components/schemas/(\w+)", json.dumps(spec)))
        self.assertEqual(refs - set(spec["components"]["schemas"]), set())
        for path, item in spec["paths"].items():
            for op in item.values():
                declared = {p["name"] for p in op.get("parameters", []) if p["in"] == "path"}
                self.assertEqual(set(re.findall(r"\{(\w+)\}", path)), declared, path)

    def test_published_file_is_current(self):
        published = Path(__file__).resolve().parent.parent / "docs" / "api" / "openapi.json"
        self.assertEqual(json.loads(published.read_text()), json.loads(json.dumps(build())))


if __name__ == "__main__":
    unittest.main()
