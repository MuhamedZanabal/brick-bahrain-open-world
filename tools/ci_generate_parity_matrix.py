#!/usr/bin/env python3
from pathlib import Path
import json
shots=Path('build/runtime_screenshots')
items=[('Player model','03_hero_district.png'),('Player animation','04_player_walking.png'),('Camera','04_player_walking.png'),('Buildings','03_hero_district.png'),('Landmark quality','03_hero_district.png'),('Road quality','07_boulevard_traffic.png'),('Sidewalk quality','06_souq_npcs.png'),('Traffic','07_boulevard_traffic.png'),('Pedestrian density','06_souq_npcs.png'),('Vegetation','08_waterfront.png'),('Water','08_waterfront.png'),('Lighting','09_night_scene.png'),('Shadows','03_hero_district.png'),('Sky','03_hero_district.png'),('Materials','03_hero_district.png'),('HUD','12_mission_hud.png'),('Minimap','13_minimap.png'),('Mobile controls','05_vehicle_driving.png'),('Mission presentation','12_mission_hud.png'),('Vehicle presentation','05_vehicle_driving.png'),('Atmospheric depth','10_sandstorm.png'),('Overall city density','03_hero_district.png')]
lines=['# Evidence-Based Visual Parity Matrix','','Generated only from workflow-rendered PNG existence. Quality classification remains `Below target` pending human review; missing evidence is `Unverified`.','','| Category | Status | Evidence filename | Remaining difference | Highest-impact correction |','|---|---|---|---|---|']
for category,name in items:
 exists=(shots/name).is_file() and (shots/name).stat().st_size>128
 status='Below target' if exists else 'Unverified'
 evidence=name if exists else 'Unavailable'
 gap='Requires screenshot review against benchmark' if exists else 'No valid rendered screenshot'
 fix='Review actual frame and prioritize largest observed visual gap' if exists else 'Fix renderer/state capture and rerun'
 lines.append(f'| {category} | {status} | {evidence} | {gap} | {fix} |')
out=Path('build/ci_logs/evidence-parity-matrix.md');out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(out)
