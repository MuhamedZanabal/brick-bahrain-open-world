#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
root=Path('.')
important=['project.godot','export_presets.cfg','scripts/hero_district_builder.gd','scripts/player_controller.gd','scripts/vehicle.gd','scripts/npc_manager.gd','scripts/traffic_manager.gd','scripts/quality_manager.gd','scripts/minimap.gd','scripts/hud.gd','scripts/mission_manager.gd','tests/runtime_smoke_test_v14.gd']
rows=[];missing=[]
for name in important:
 p=root/name
 if not p.is_file(): missing.append(name); continue
 rows.append({'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
out=Path('build/ci_logs/v14-source-manifest.json');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'files':rows,'missing':missing},indent=2),encoding='utf-8')
print(out.read_text());raise SystemExit(1 if missing else 0)
