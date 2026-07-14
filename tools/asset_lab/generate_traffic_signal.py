"""Generate a simplified Bahrain Brick traffic signal assembly."""
from __future__ import annotations
import argparse,sys
from pathlib import Path
from _common import reset_scene,create_material,add_box,add_collision_box,export_glb

def build(output: Path)->None:
    reset_scene(); metal=create_material('bh_mat_painted_metal_charcoal',(0.07,0.08,0.09,1),roughness=0.5)
    red=create_material('bh_mat_signal_red',(0.65,0.03,0.02,1),roughness=0.3); amber=create_material('bh_mat_signal_amber',(0.95,0.45,0.02,1),roughness=0.3); green=create_material('bh_mat_signal_green',(0.02,0.55,0.16,1),roughness=0.3)
    pole=add_box('bh_prop_traffic_signal_a_01_pole',(0.07,2.2,0.07),(0,2.2,0),metal)
    add_box('bh_prop_traffic_signal_a_01_head',(0.22,0.62,0.18),(0,4.6,0),metal)
    for y,matl,name in (
        (4.96,red,'bh_prop_traffic_signal_a_01_red'),
        (4.60,amber,'bh_prop_traffic_signal_a_01_amber'),
        (4.24,green,'bh_prop_traffic_signal_a_01_green'),
    ):
        add_box(name,(0.09,0.09,0.035),(0,y,-0.19),matl)
    add_collision_box(pole,'bh_col_prop_traffic_signal_a_01',(0.10,2.2,0.10),(0,2.2,0))
    export_glb(output/'bh_prop_traffic_signal_a_01.glb')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/generated/street')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);build(Path(a.output))
