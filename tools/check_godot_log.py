#!/usr/bin/env python3
from __future__ import annotations
import argparse,re
from pathlib import Path
FATAL=[r'SCRIPT ERROR:',r'Parse Error:',r'Failed to load script',r'Failed loading resource',r'Cannot open file',r'Shader compilation failed',r'ERROR:.*(Invalid|Cannot|Failed|Parse|Could not)']
IGNORE=[r'ERROR:.*pulse',r'ALSA lib',r'Fontconfig warning',r'XDG_RUNTIME_DIR',r'getaddrinfo']
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--report',type=Path);a=p.parse_args();text=a.log.read_text(encoding='utf-8',errors='replace') if a.log.exists() else '';hits=[]
 for line in text.splitlines():
  if any(re.search(x,line,re.I) for x in IGNORE):continue
  if any(re.search(x,line,re.I) for x in FATAL):hits.append(line)
 out='\n'.join([f'log={a.log}',f'fatal_matches={len(hits)}',*hits])+'\n'
 if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(out,encoding='utf-8')
 print(out,end='');return 1 if hits else 0
if __name__=='__main__':raise SystemExit(main())
