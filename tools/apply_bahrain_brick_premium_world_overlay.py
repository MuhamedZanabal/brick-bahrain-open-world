#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, io, json, zipfile
from pathlib import Path
EXPECTED_SOURCE_SHA256 = "5c4d8ac4497eda7752058424062a74a97c1f6f5e0c9a1ff393abac2a2c7c828a"
FROZEN = [
 "scripts/virtual_joystick.gd", "scripts/touch_input.gd", "scripts/player_controller.gd", "scripts/hud.gd",
 "tests/mobile_input_pipeline_test.gd", "scenes/mobile_input_pipeline_test.tscn",
 "tests/mobile_input_visual_evidence.gd", "scenes/mobile_input_visual_evidence.tscn",
]
EVIDENCE_ONLY = {"tests/premium_world_visual_evidence.gd", "scenes/premium_world_visual_evidence.tscn"}
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def main() -> int:
 parser=argparse.ArgumentParser(); parser.add_argument("project_root",type=Path); parser.add_argument("--report",type=Path); parser.add_argument("--evidence-only",action="store_true")
 args=parser.parse_args(); project=args.project_root.resolve()
 if not (project/"project.godot").is_file(): raise SystemExit("project.godot missing")
 before={rel:sha(project/rel) for rel in FROZEN}; changed=[]
 payload_dir=Path(__file__).resolve().parent/"premium_payload"
 payload="".join(p.read_text().strip() for p in sorted(payload_dir.glob("part*.b64")))
 with zipfile.ZipFile(io.BytesIO(base64.b64decode(payload))) as archive:
  for rel in sorted(archive.namelist()):
   if args.evidence_only and rel not in EVIDENCE_ONLY: continue
   target=project/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(archive.read(rel)); changed.append(rel)
 after={rel:sha(project/rel) for rel in FROZEN}; mismatches=[rel for rel in FROZEN if before[rel]!=after[rel]]
 if mismatches: raise SystemExit(f"frozen controls modified: {mismatches}")
 report={"evidence_class":"VERIFIED","classification":"premium world overlay on historical v1.4 fallback; not v15 authority","base_integrated_source_sha256":EXPECTED_SOURCE_SHA256,"evidence_only":args.evidence_only,"overlay_files":changed,"frozen_controls_unchanged":True,"frozen_control_hashes":after}
 if args.report: args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
