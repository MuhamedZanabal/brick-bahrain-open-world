#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID required}"
ROOT="${GITHUB_WORKSPACE}"
HARNESS=/tmp/pr59_engine_qualification.py
CORPUS_DIR="$ROOT/build/corpus"
CANDIDATES="$ROOT/build/candidates"
AGG="$ROOT/build/aggregate"
DOWNLOADS="$ROOT/build/downloads"
SOURCES="$ROOT/build/sources"
WORK="$ROOT/build/work"
mkdir -p "$CORPUS_DIR" "$CANDIDATES" "$AGG" "$DOWNLOADS" "$SOURCES" "$WORK"
SOURCE_ZIP=$(find "$ROOT/build/input" -name MANAMA_SOUQ_COMPOSITE_SOURCE.zip -type f -print -quit)
SELECTION=$(find "$ROOT/build/forensic" -name REPRESENTATIVE_SELECTION.json -type f -print -quit)
test -n "$SOURCE_ZIP" -a -n "$SELECTION"
python3 "$HARNESS" prepare-corpus --source-zip "$SOURCE_ZIP" --selection "$SELECTION" --output "$CORPUS_DIR"
CORPUS_ZIP=$(find "$CORPUS_DIR" -name BAHRAIN_BRICK_ENGINE_QUALIFICATION_CORPUS.zip -type f -print -quit)
SEMANTIC="$ROOT/qualification/.github/forensics/pr59_model_semantic_dump.gd"
test -f "$CORPUS_ZIP" -a -f "$SEMANTIC"

release_assets() {
  local tag="$1" json="$2" out="$3"
  python3 - "$tag" "$json" "$out" <<'PY'
import json,shlex,sys
TAG,p,out=sys.argv[1:]
r=json.load(open(p))
bname=f'Godot_v{TAG}_linux.x86_64.zip'
sname=f'godot-{TAG}.tar.xz'
def one(name):
    m=[a for a in r.get('assets',[]) if a.get('name')==name]
    if len(m)!=1: raise SystemExit(f'expected one official asset {name}, got {len(m)}')
    a=m[0]
    if not (a.get('digest') or '').startswith('sha256:'): raise SystemExit(f'missing official sha256 digest for {name}')
    return a
b=one(bname); s=one(sname)
vals={
 'RELEASE_ID':str(r['id']),'RELEASE_URL':r['html_url'],'PUBLISHED_AT':r['published_at'],
 'BINARY_NAME':bname,'BINARY_URL':b['browser_download_url'],'BINARY_SHA':b['digest'][7:],'BINARY_ID':str(b['id']),'BINARY_BYTES':str(b['size']),
 'SOURCE_NAME':sname,'SOURCE_URL':s['browser_download_url'],'SOURCE_SHA':s['digest'][7:],'SOURCE_ID':str(s['id']),'SOURCE_BYTES':str(s['size'])}
open(out,'w').write('\n'.join(f'{k}={shlex.quote(v)}' for k,v in vals.items())+'\n')
PY
}

qualify() {
  local TAG="$1" OUT="$CANDIDATES/$TAG" DL="$DOWNLOADS/$TAG" SRC="$SOURCES/$TAG" W="$WORK/$TAG"
  mkdir -p "$OUT" "$DL" "$SRC" "$W"
  curl -fsSL --retry 4 --retry-all-errors \
    -H 'Accept: application/vnd.github+json' -H "Authorization: Bearer $GH_TOKEN" \
    "https://api.github.com/repos/godotengine/godot-builds/releases/tags/$TAG" > "$DL/release.json"
  release_assets "$TAG" "$DL/release.json" "$DL/assets.env"
  # shellcheck disable=SC1090
  source "$DL/assets.env"
  curl -fL --retry 4 --retry-all-errors "$BINARY_URL" -o "$DL/$BINARY_NAME"
  curl -fL --retry 4 --retry-all-errors "$SOURCE_URL" -o "$DL/$SOURCE_NAME"
  test "$(sha256sum "$DL/$BINARY_NAME" | cut -d' ' -f1)" = "$BINARY_SHA"
  test "$(sha256sum "$DL/$SOURCE_NAME" | cut -d' ' -f1)" = "$SOURCE_SHA"
  unzip -q "$DL/$BINARY_NAME" -d "$DL/engine"
  local ENGINE
  ENGINE=$(find "$DL/engine" -maxdepth 2 -type f -name 'Godot*' ! -name '*.txt' -print -quit)
  chmod +x "$ENGINE"
  tar -xf "$DL/$SOURCE_NAME" -C "$SRC"
  local SOURCE_ROOT TAG_COMMIT VERSION_OUTPUT
  SOURCE_ROOT=$(find "$SRC" -mindepth 1 -maxdepth 1 -type d -print -quit)
  TAG_COMMIT=$(git ls-remote https://github.com/godotengine/godot.git "refs/tags/$TAG^{}" | awk 'NR==1{print $1}')
  if [ -z "$TAG_COMMIT" ]; then TAG_COMMIT=$(git ls-remote https://github.com/godotengine/godot.git "refs/tags/$TAG" | awk 'NR==1{print $1}'); fi
  VERSION_OUTPUT=$("$ENGINE" --version | head -1)
  python3 - "$OUT/ENGINE_IDENTITY.json" "$TAG" "$RELEASE_ID" "$RELEASE_URL" "$PUBLISHED_AT" "$BINARY_NAME" "$BINARY_SHA" "$BINARY_ID" "$BINARY_BYTES" "$SOURCE_NAME" "$SOURCE_SHA" "$SOURCE_ID" "$SOURCE_BYTES" "$TAG_COMMIT" "$VERSION_OUTPUT" <<'PY'
import json,os,platform,sys
(p,tag,rid,rurl,published,bn,bsha,bid,bbytes,sn,ssha,sid,sbytes,commit,version)=sys.argv[1:]
d={'tag':tag,'release_id':int(rid),'release_url':rurl,'published_at':published,'prerelease':False,'draft':False,
'binary_archive_filename':bn,'binary_archive_sha256':bsha,'binary_asset_id':int(bid),'binary_asset_bytes':int(bbytes),
'source_archive_filename':sn,'source_archive_sha256':ssha,'source_asset_id':int(sid),'source_asset_bytes':int(sbytes),
'source_tag_commit':commit,'runtime_version_output':version,'operating_system':platform.platform(),'architecture':platform.machine(),
'locale':'C.UTF-8','timezone':'UTC','umask':'0022','cpu_count':os.cpu_count(),
'command_line_arguments':['--headless','--path','<disposable-project>','--editor','--import','--quit','--verbose'],
'import_environment':{'TZ':'UTC','LC_ALL':'C.UTF-8','LANG':'C.UTF-8','umask':'0022'},
'download_provenance':'official godotengine/godot-builds release API assets with GitHub-published SHA-256 digests'}
open(p,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n')
PY
  set +e
  python3 "$HARNESS" stage2 --engine "$ENGINE" --identity "$OUT/ENGINE_IDENTITY.json" --source-root "$SOURCE_ROOT" --corpus-zip "$CORPUS_ZIP" --semantic-script "$SEMANTIC" --output "$OUT" --work-root "$W"
  local code=$?
  set -e
  if [ "$code" -ne 0 ]; then
    python3 - "$OUT" "$TAG" "$code" <<'PY'
import json,sys
out,tag,code=sys.argv[1:]
obj={'classification':'Q6','stage2_pass':False,'reason':f'qualification harness exited {code}','engine_identity':{'tag':tag}}
open(out+'/ENGINE_CLASSIFICATION.json','w').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
PY
  fi
  rm -rf "$DL" "$SRC" "$W"
}

for tag in 4.4.1-stable 4.5.2-stable 4.6.3-stable; do qualify "$tag"; done

unavailable() {
  local TAG="$1" OUT="$CANDIDATES/$TAG" STATUS
  mkdir -p "$OUT"
  STATUS=$(curl -sS -o "$OUT/release-api-response.json" -w '%{http_code}' -H 'Accept: application/vnd.github+json' -H "Authorization: Bearer $GH_TOKEN" "https://api.github.com/repos/godotengine/godot-builds/releases/tags/$TAG")
  test "$STATUS" = 404
  python3 "$HARNESS" unavailable --version "$TAG" --checked-at "$(date -u +%FT%TZ)" --evidence "official godotengine/godot-builds release API HTTP $STATUS" --reason 'No official release exists for the requested tag as of the qualification run.' --output "$OUT"
}
unavailable 4.7.1-stable
unavailable 4.8-dev1
python3 "$HARNESS" aggregate --candidate-root "$CANDIDATES" --output "$AGG"
cp "$CORPUS_DIR/CORPUS_AUTHORITY_RESOLUTION.json" "$AGG/"
cp "$CORPUS_DIR/QUALIFICATION_CORPUS_ARCHIVE.json" "$AGG/"
python3 - <<'PY'
import hashlib,json,os
from pathlib import Path
r=Path('build/aggregate'); rows=[]
for p in sorted(x for x in r.rglob('*') if x.is_file() and x.name!='FINAL_AGGREGATE_INVENTORY.json'):
    rows.append({'path':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(r/'FINAL_AGGREGATE_INVENTORY.json').write_text(json.dumps({'workflow_run_id':int(os.environ['GITHUB_RUN_ID']),'frozen_pr_head':'5b4e2466ef84f3984f3bf336b31925d4d2e97a7f','files':rows,'no_android_export':True,'no_project_migration':True},indent=2,sort_keys=True)+'\n')
PY
