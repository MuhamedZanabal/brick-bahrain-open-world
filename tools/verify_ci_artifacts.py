#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess,zipfile
from pathlib import Path
PNG=b'\x89PNG\r\n\x1a\n'
SHOTS=['01_main_menu.png','02_character_select.png','03_hero_district.png','04_player_walking.png','05_vehicle_driving.png','06_souq_npcs.png','07_boulevard_traffic.png','08_waterfront.png','09_night_scene.png','10_sandstorm.png','11_phone_ui.png','12_mission_hud.png','13_minimap.png']
def run(args):
 p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False);return p.returncode,p.stdout
def shot_check(root):
 rows=[];errors=[]
 for name in SHOTS:
  p=root/name;r={'filename':name,'exists':p.is_file()}
  if not p.is_file():errors.append(f'missing screenshot: {name}')
  else:
   d=p.read_bytes()
   if len(d)<24 or d[:8]!=PNG:errors.append(f'invalid PNG: {name}')
   else:
    w=int.from_bytes(d[16:20],'big');h=int.from_bytes(d[20:24],'big');r.update(width=w,height=h,size_bytes=len(d))
    if w<320 or h<180 or len(d)<=128:errors.append(f'invalid screenshot dimensions/size: {name}')
  rows.append(r)
 return {'ok':not errors,'errors':errors,'screenshots':rows}
def apk_check(apk,aapt,apksigner):
 errors=[];r={'path':str(apk),'exists':apk.is_file()}
 if not apk.is_file():r.update(ok=False,errors=['APK does not exist']);return r
 data=apk.read_bytes();r['size_bytes']=len(data);r['sha256']=hashlib.sha256(data).hexdigest()
 try:
  with zipfile.ZipFile(apk) as z:
   bad=z.testzip();names=z.namelist();r['zip_entries']=len(names);r['zip_test']='ok' if bad is None else f'corrupt:{bad}'
   if bad:errors.append(f'ZIP CRC failed: {bad}')
   if 'AndroidManifest.xml' not in names:errors.append('AndroidManifest.xml missing')
   project=[n for n in names if n.startswith('assets/') and ('project' in n.lower() or n.endswith('.pck') or n=='assets/_cl_')];r['project_data_entries']=project
   if not project:errors.append('Godot project data entry missing')
 except Exception as e:errors.append(f'APK ZIP error: {e}')
 code,badging=run([aapt,'dump','badging',str(apk)]);r['aapt_exit_code']=code;r['aapt_badging']=badging
 m=re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'",badging)
 if not m:errors.append('aapt package/version metadata missing')
 else:
  package,vc,vn=m.groups();r.update(package_id=package,version_code=vc,version_name=vn)
  if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+',package):errors.append(f'invalid package ID: {package}')
  if vc!='14':errors.append(f'versionCode expected 14, got {vc}')
  if vn!='1.4.0':errors.append(f'versionName expected 1.4.0, got {vn}')
 lm=re.search(r"launchable-activity: name='([^']+)'",badging);r['launch_activity']=lm.group(1) if lm else ''
 if not lm:errors.append('launchable activity missing')
 code,out=run([apksigner,'verify','--verbose','--print-certs',str(apk)]);r['apksigner_exit_code']=code;r['apksigner_output']=out
 if code:errors.append('APK signature verification failed')
 r['errors']=errors;r['ok']=not errors;return r
def main():
 p=argparse.ArgumentParser();p.add_argument('--apk',type=Path);p.add_argument('--screenshots',type=Path);p.add_argument('--aapt',default='aapt');p.add_argument('--apksigner',default='apksigner');p.add_argument('--report',type=Path,required=True);p.add_argument('--sha256-file',type=Path);a=p.parse_args();report={};status=0
 if a.apk:
  report['apk']=apk_check(a.apk,a.aapt,a.apksigner);status|=not report['apk']['ok']
  if a.sha256_file and a.apk.is_file():a.sha256_file.parent.mkdir(parents=True,exist_ok=True);a.sha256_file.write_text(f"{report['apk']['sha256']}  {a.apk.name}\n",encoding='utf-8')
 if a.screenshots:report['visual']=shot_check(a.screenshots);status|=not report['visual']['ok']
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));return int(bool(status))
if __name__=='__main__':raise SystemExit(main())
