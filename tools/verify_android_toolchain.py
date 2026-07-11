#!/usr/bin/env python3
from __future__ import annotations
import json,os,shutil,subprocess,sys
TOOLS=['java','keytool','sdkmanager','adb','apksigner','zipalign','aapt']
rows=[];ok=True
for tool in TOOLS:
 path=shutil.which(tool)
 rows.append({'tool':tool,'path':path or ''})
 ok &= path is not None
print(json.dumps({'ok':bool(ok),'java_home':os.getenv('JAVA_HOME',''),'android_sdk_root':os.getenv('ANDROID_SDK_ROOT',''),'tools':rows},indent=2))
raise SystemExit(0 if ok else 1)
