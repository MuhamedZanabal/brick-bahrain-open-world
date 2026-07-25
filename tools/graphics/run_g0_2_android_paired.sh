#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="${1:?repository root required}"
SOURCE_ROOT="${2:?source artifact extraction root required}"
OUTPUT_ROOT="${3:?raw output root required}"
AUTHORITY="$REPO_ROOT/authority/bahrain_brick_g0_2_android_renderer_qualification.json"
SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
ADB="$SDK_ROOT/platform-tools/adb"
EMULATOR="$SDK_ROOT/emulator/emulator"
AVDMANAGER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/avdmanager' | sort | tail -1)"
AAPT2="$SDK_ROOT/build-tools/34.0.0/aapt2"
APKSIGNER="$SDK_ROOT/build-tools/34.0.0/apksigner"
APKANALYZER="$(find "$SDK_ROOT/cmdline-tools" -type f -path '*/bin/apkanalyzer' | sort | tail -1)"

PERFORMANCE_LABEL="DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE"
STATE_ORDER=(
  PACKAGE_VERIFIED
  LAUNCHER_RESOLVED
  LOG_CAPTURE_STARTED
  ACTIVITY_START_REQUESTED
  PROCESS_CREATED
  WINDOW_VISIBLE
  GODOT_STARTED
  RENDERER_IDENTIFIED
  MISSION_STARTED
  SCENE_READY
  CAPTURE_FRAME_REACHED
  SCREENSHOT_CAPTURED
  PAUSE_RESUME_PASSED
  CRITICAL_LOG_SCAN_PASSED
  EVIDENCE_FINALIZED
)

mkdir -p "$OUTPUT_ROOT"
cp "$AUTHORITY" "$OUTPUT_ROOT/authority.json"
for tool in "$ADB" "$EMULATOR" "$AVDMANAGER" "$AAPT2" "$APKSIGNER" "$APKANALYZER"; do
  test -x "$tool" || { echo "missing tool: $tool" >&2; exit 2; }
done

utc_now() { date -u +%Y-%m-%dT%H:%M:%S.%3NZ; }
epoch_ms() { date +%s%3N; }

record_state() {
  local file="$1" state="$2" started="$3" terminal="$4" command="$5" code="$6" evidence="$7" result="$8" reason="$9"
  python3 - "$file" "$state" "$started" "$terminal" "$command" "$code" "$evidence" "$result" "$reason" <<'PY'
from pathlib import Path
import json,sys
path=Path(sys.argv[1])
value=json.loads(path.read_text()) if path.is_file() else {"schema_version":1,"performance_label":"DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE","states":[]}
value["states"].append({
  "state":sys.argv[2],"start_timestamp":sys.argv[3],"terminal_timestamp":sys.argv[4],
  "command_or_signal":sys.argv[5],"exit_code":int(sys.argv[6]),"evidence_path":sys.argv[7],
  "result":sys.argv[8],"failure_reason":sys.argv[9] or None,
})
path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
PY
}

write_json() {
  local path="$1"; shift
  python3 - "$path" "$@" <<'PY'
from pathlib import Path
import json,sys
path=Path(sys.argv[1]); payload=json.loads(sys.argv[2]); path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
PY
}

copy_shared_authority() {
  python3 - "$SOURCE_ROOT" "$OUTPUT_ROOT/shared_import_equivalence.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
source=Path(sys.argv[1]); out=Path(sys.argv[2])
clone=json.loads((source/'CLONE_IDENTITY.json').read_text())
manifest=json.loads((source/'IMPORTED_STATE_MANIFEST.json').read_text())
roots=clone.get('roots',[])
hashes=[item.get('aggregate_sha256') for item in roots]
counts=[item.get('file_count') for item in roots]
bytes_=[item.get('aggregate_bytes') for item in roots]
passed=bool(clone.get('passed')) and len(set(hashes))==1 and len(set(counts))==1 and len(set(bytes_))==1
payload={
 'schema_version':1,'source_artifact_id':8586122615,'renderer_evidence_source_commit':'6ade72ed02084791128dcf4a91223e695d802c15',
 'one_imported_state':True,'byte_identical_clones':passed,'file_count':manifest.get('file_count'),
 'aggregate_byte_count':manifest.get('aggregate_bytes'),'aggregate_sha256':manifest.get('aggregate_sha256'),
 'imported_resource_hash_inventory':manifest.get('files',[]),'clone_identity':clone,
}
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
if not passed: raise SystemExit('shared import clone equivalence failed')
PY
  cp "$SOURCE_ROOT/GL_VARIANT_OVERRIDE.json" "$OUTPUT_ROOT/GL_VARIANT_OVERRIDE.json"
  cp "$SOURCE_ROOT/MOBILE_VARIANT_OVERRIDE.json" "$OUTPUT_ROOT/MOBILE_VARIANT_OVERRIDE.json"
}

capture_environment() {
  local key="$1" out="$2" avd_name="$3"
  python3 - "$ADB" "$EMULATOR" "$out" "$key" "$avd_name" <<'PY'
import json,os,platform,subprocess,sys
adb,emulator,out,key,avd=sys.argv[1:]
def host(*args): return subprocess.run(list(args),text=True,capture_output=True,check=False).stdout.strip()
def shell(*args): return subprocess.run([adb,'shell',*args],text=True,capture_output=True,check=False).stdout.strip()
payload={
 'schema_version':1,'candidate':key,'api_level':int(shell('getprop','ro.build.version.sdk') or 0),
 'android_version':shell('getprop','ro.build.version.release'),'system_image':'system-images;android-34;default;x86_64',
 'abi':shell('getprop','ro.product.cpu.abi'),'abi_list':shell('getprop','ro.product.cpu.abilist'),
 'uname_m':shell('uname','-m'),'manufacturer':shell('getprop','ro.product.manufacturer'),
 'model':shell('getprop','ro.product.model'),'device':shell('getprop','ro.product.device'),
 'build_fingerprint':shell('getprop','ro.build.fingerprint'),'boot_completed':shell('getprop','sys.boot_completed'),
 'resolution':shell('wm','size'),'density':shell('wm','density'),'gles_version':shell('getprop','ro.opengles.version'),
 'vulkan_features':shell('pm','list','features'),'disk_space':shell('df','-h','/data'),
 'ram_mb':4096,'storage':'default AVD data partition','cores':4,'gpu_mode':'swiftshader','acceleration_mode':'auto/KVM when available',
 'avd_name':avd,'emulator_version':host(emulator,'-version'),'adb_version':host(adb,'version'),
 'host_platform':platform.platform(),'runner_image_version':os.environ.get('ImageVersion'),'host_runner_class':'ubuntu-24.04',
 'package_install_user':0,'performance_label':'DIAGNOSTIC_ONLY_NOT_PHYSICAL_DEVICE_ACCEPTANCE',
}
open(out,'w').write(json.dumps(payload,indent=2,sort_keys=True)+'\n')
PY
}

start_emulator() {
  local key="$1" candidate_dir="$2"
  local avd_home="$OUTPUT_ROOT/avd-$key" emulator_home="$OUTPUT_ROOT/emulator-home-$key" avd_name="bahrain_brick_g0_2_${key}"
  rm -rf "$avd_home" "$emulator_home"
  mkdir -p "$avd_home" "$emulator_home"
  export ANDROID_AVD_HOME="$avd_home"
  export ANDROID_EMULATOR_HOME="$emulator_home"
  echo no | "$AVDMANAGER" create avd --force --name "$avd_name" --package 'system-images;android-34;default;x86_64' --device 'pixel_6' > "$candidate_dir/avd-create.txt" 2>&1 || return 1
  nohup "$EMULATOR" "@$avd_name" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data \
    -gpu swiftshader -accel auto -memory 4096 -cores 4 -camera-back none -camera-front none \
    > "$candidate_dir/emulator.log" 2>&1 &
  EMULATOR_PID=$!
  export EMULATOR_PID
  "$ADB" wait-for-device > "$candidate_dir/adb-wait-for-device.txt" 2>&1 || return 1
  local booted=false
  for _attempt in $(seq 1 240); do
    if [[ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == "1" ]]; then booted=true; break; fi
    sleep 2
  done
  if [[ "$booted" != true ]]; then return 1; fi
  "$ADB" shell settings put system accelerometer_rotation 0 >/dev/null 2>&1 || true
  "$ADB" shell settings put system user_rotation 1 >/dev/null 2>&1 || true
  "$ADB" shell wm size 1920x1080 > "$candidate_dir/wm-size.txt" 2>&1 || return 1
  "$ADB" shell wm density 420 > "$candidate_dir/wm-density.txt" 2>&1 || return 1
  "$ADB" shell input keyevent 82 >/dev/null 2>&1 || true
  capture_environment "$key" "$candidate_dir/emulator_environment.json" "$avd_name"
  return 0
}

stop_emulator() {
  "$ADB" emu kill >/dev/null 2>&1 || true
  if [[ -n "${EMULATOR_PID:-}" ]]; then kill "$EMULATOR_PID" >/dev/null 2>&1 || true; fi
  unset EMULATOR_PID
  sleep 3
}

fail_remaining_states() {
  local state_file="$1" reason="$2" evidence="$3" start_index="$4"
  local now; now="$(utc_now)"
  for ((i=start_index;i<${#STATE_ORDER[@]};i++)); do
    record_state "$state_file" "${STATE_ORDER[$i]}" "$now" "$now" "not executed" 1 "$evidence" "FAIL" "$reason"
  done
}

critical_scan() {
  local log="$1" output="$2" summary="$3"
  python3 - "$log" "$output" "$summary" <<'PY'
from pathlib import Path
import json,re,sys
log=Path(sys.argv[1]); text=log.read_text(errors='replace') if log.is_file() else ''
patterns={
 'java_fatal':re.compile(r'FATAL EXCEPTION|AndroidRuntime.*FATAL',re.I),
 'native_fatal':re.compile(r'Fatal signal|SIGSEGV|SIGABRT|SIGILL|SIGBUS|crash_dump|tombstoned.*received crash',re.I),
 'linker_failure':re.compile(r'linker.*(?:cannot locate|not found|dlopen failed)|CANNOT LINK EXECUTABLE',re.I),
 'anr':re.compile(r'ANR in |am_anr',re.I),
 'missing_resource':re.compile(r'Failed loading resource|Failed to load resource|Could not load resource|missing resource',re.I),
 'renderer_blocking_shader':re.compile(r'(?:shader.*(?:error|failed)|failed.*shader|SPIR-V|GLSL.*error|rendering device.*failed|failed to initialize.*render)',re.I),
}
counts={name:len(p.findall(text)) for name,p in patterns.items()}
lines=[line for line in text.splitlines() if any(p.search(line) for p in patterns.values())]
Path(sys.argv[2]).write_text('\n'.join(lines)+('\n' if lines else ''))
payload={'schema_version':1,'counts':counts,'total':sum(counts.values()),'passed':sum(counts.values())==0}
Path(sys.argv[3]).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
raise SystemExit(0 if payload['passed'] else 1)
PY
}

run_candidate() {
  local key="$1" expected_renderer="$2" package="$3" apk="$4" override="$5"
  local out="$OUTPUT_ROOT/$key"
  local state_file="$out/state_machine.json"
  mkdir -p "$out/gfxinfo_samples" "$out/meminfo_samples"
  printf '{"schema_version":1,"candidate":"%s","expected_renderer":"%s","performance_label":"%s","states":[]}\n' "$key" "$expected_renderer" "$PERFORMANCE_LABEL" > "$state_file"
  cp "$override" "$out/renderer_override.json"
  local started terminal code reason result resolved launch_start_ms visible_ms pid pid_after logcat_pid

  started="$(utc_now)"
  "$APKSIGNER" verify --verbose --print-certs "$apk" > "$out/apksigner.txt" 2>&1; code=$?
  "$AAPT2" dump packagename "$apk" > "$out/aapt2-packagename.txt" 2>&1; local aapt_code=$?
  "$APKANALYZER" manifest print "$apk" > "$out/manifest.xml" 2>&1; local manifest_code=$?
  unzip -l "$apk" > "$out/unzip-list.txt" 2>&1; local unzip_code=$?
  python3 - "$apk" "$out/native_elf_inventory.json" <<'PY_NATIVE'
from pathlib import Path
import hashlib,json,re,subprocess,sys,tempfile,zipfile
apk=Path(sys.argv[1]); output=Path(sys.argv[2]); records=[]
system_allow={'libandroid.so','libc.so','libdl.so','libEGL.so','libGLESv2.so','libGLESv3.so','libjnigraphics.so','liblog.so','libm.so','libOpenSLES.so','libvulkan.so','libz.so'}
with zipfile.ZipFile(apk) as zf, tempfile.TemporaryDirectory() as tmp:
    names=[name for name in zf.namelist() if re.fullmatch(r'lib/[^/]+/[^/]+\.so',name)]
    bundled={Path(name).name for name in names}
    for name in names:
        info=zf.getinfo(name); data=zf.read(name); target=Path(tmp)/Path(name).name; target.write_bytes(data)
        header=subprocess.run(['readelf','-h',str(target)],text=True,capture_output=True).stdout
        dynamic=subprocess.run(['readelf','-d',str(target)],text=True,capture_output=True).stdout
        notes=subprocess.run(['readelf','-n',str(target)],text=True,capture_output=True).stdout
        machine=re.search(r'^\s*Machine:\s*(.+)$',header,re.M)
        elf_class=re.search(r'^\s*Class:\s*(.+)$',header,re.M)
        needed=re.findall(r'\(NEEDED\).*?\[(.+?)\]',dynamic)
        records.append({
          'path':name,'abi':name.split('/')[1],'filename':Path(name).name,'bytes':len(data),
          'sha256':hashlib.sha256(data).hexdigest(),'compressed':info.compress_type!=zipfile.ZIP_STORED,
          'compression_method':info.compress_type,'local_header_offset':info.header_offset,
          'alignment_mod_4096':info.header_offset%4096,'elf_class':elf_class.group(1).strip() if elf_class else None,
          'machine':machine.group(1).strip() if machine else None,'needed':needed,
          'missing_bundled_or_system_dependencies':[item for item in needed if item not in bundled and item not in system_allow],
          'android_notes':notes,
        })
payload={'schema_version':1,'libraries':records,'supported_abis':sorted({r['abi'] for r in records}),
 'x86_64_godot_runtime_present':any(r['path']=='lib/x86_64/libgodot_android.so' for r in records),
 'duplicate_library_filenames':sorted({r['filename'] for r in records if sum(x['filename']==r['filename'] for x in records)>1}),
 'all_x86_64_machine':all(r['abi']!='x86_64' or ('X86-64' in (r['machine'] or '') or 'Advanced Micro Devices X86-64' in (r['machine'] or '')) for r in records),
 'missing_dependencies':sorted({d for r in records for d in r['missing_bundled_or_system_dependencies']})}
output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
PY_NATIVE
  local native_code=$?
  local package_ok=false abi_ok=false
  grep -q "$package" "$out/aapt2-packagename.txt" && package_ok=true || true
  python3 - "$out/native_elf_inventory.json" <<'PY_ABI' && abi_ok=true || true
import json,sys
p=json.load(open(sys.argv[1]))
raise SystemExit(0 if p.get('x86_64_godot_runtime_present') and p.get('all_x86_64_machine') and not p.get('missing_dependencies') else 1)
PY_ABI
  terminal="$(utc_now)"; result=PASS; reason=""
  if [[ $code -ne 0 || $aapt_code -ne 0 || $manifest_code -ne 0 || $unzip_code -ne 0 || $native_code -ne 0 || "$package_ok" != true || "$abi_ok" != true ]]; then
    result=FAIL; reason="APK signature, package, manifest, or x86_64 Godot library verification failed"; code=1
  else code=0; fi
  record_state "$state_file" PACKAGE_VERIFIED "$started" "$terminal" "apksigner + aapt2 + apkanalyzer + unzip" "$code" "$key/apksigner.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then fail_remaining_states "$state_file" "$reason" "$key/apksigner.txt" 1; return 1; fi

  if ! start_emulator "$key" "$out"; then
    write_json "$out/infrastructure_failure.json" '{"classification":"ANDROID_INFRASTRUCTURE_FAILURE","reason":"API 34 emulator failed to create or boot"}'
    started="$(utc_now)"; terminal="$started"
    record_state "$state_file" LAUNCHER_RESOLVED "$started" "$terminal" "emulator boot prerequisite" 1 "$key/emulator.log" FAIL "API 34 emulator failed to create or boot"
    fail_remaining_states "$state_file" "API 34 emulator unavailable" "$key/emulator.log" 2
    stop_emulator
    return 1
  fi

  "$ADB" uninstall "$package" > "$out/uninstall-before.txt" 2>&1 || true
  "$ADB" install -r -t "$apk" > "$out/install.txt" 2>&1; local install_code=$?
  printf '%s\n' "$install_code" > "$out/install-exit-code.txt"
  "$ADB" shell pm path "$package" > "$out/pm-path.txt" 2>&1; local pm_code=$?
  "$ADB" shell dumpsys package "$package" > "$out/dumpsys-package.txt" 2>&1 || true

  started="$(utc_now)"
  "$ADB" shell cmd package resolve-activity --brief "$package" > "$out/resolve-activity.txt" 2>&1; local resolve_code=$?
  "$ADB" shell cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER "$package" > "$out/query-activities.txt" 2>&1 || true
  resolved="$(tail -n 1 "$out/resolve-activity.txt" | tr -d '\r')"
  terminal="$(utc_now)"; result=PASS; reason=""; code=0
  if [[ $install_code -ne 0 ]]; then result=FAIL; reason="adb install failed"; code=$install_code
  elif [[ $pm_code -ne 0 || ! -s "$out/pm-path.txt" ]]; then result=FAIL; reason="installed package path not found"; code=1
  elif [[ $resolve_code -ne 0 || -z "$resolved" || "$resolved" == *"No activity"* ]]; then result=FAIL; reason="launcher component did not resolve"; code=1
  fi
  record_state "$state_file" LAUNCHER_RESOLVED "$started" "$terminal" "adb install; pm path; cmd package resolve-activity" "$code" "$key/resolve-activity.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then fail_remaining_states "$state_file" "$reason" "$key/install.txt" 2; stop_emulator; return 1; fi

  "$ADB" logcat -c
  started="$(utc_now)"
  "$ADB" logcat -v threadtime > "$out/logcat_full.txt" 2>&1 &
  logcat_pid=$!
  sleep 2
  terminal="$(utc_now)"
  if kill -0 "$logcat_pid" >/dev/null 2>&1; then result=PASS; code=0; reason=""; else result=FAIL; code=1; reason="background logcat did not remain active"; fi
  record_state "$state_file" LOG_CAPTURE_STARTED "$started" "$terminal" "adb logcat -v threadtime" "$code" "$key/logcat_full.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then fail_remaining_states "$state_file" "$reason" "$key/logcat_full.txt" 3; stop_emulator; return 1; fi

  "$ADB" shell am force-stop "$package" > "$out/force-stop.txt" 2>&1 || true
  "$ADB" shell pm clear "$package" > "$out/pm-clear.txt" 2>&1 || true
  "$ADB" shell dumpsys gfxinfo "$package" reset > "$out/gfxinfo-reset.txt" 2>&1 || true
  started="$(utc_now)"; launch_start_ms="$(epoch_ms)"
  "$ADB" shell am start -W -S -n "$resolved" > "$out/am-start.txt" 2>&1; code=$?
  terminal="$(utc_now)"; result=PASS; reason=""
  grep -Eq '^Status: (ok|warning)' "$out/am-start.txt" || { result=FAIL; reason="am start did not return an admissible status"; code=1; }
  record_state "$state_file" ACTIVITY_START_REQUESTED "$started" "$terminal" "adb shell am start -W -S -n $resolved" "$code" "$key/am-start.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/am-start.txt" 4; stop_emulator; return 1; fi

  started="$(utc_now)"; pid=""
  for _attempt in $(seq 1 60); do
    pid="$("$ADB" shell pidof "$package" 2>/dev/null | tr -d '\r')"
    "$ADB" shell dumpsys activity processes > "$out/activity-processes.txt" 2>&1 || true
    if [[ -n "$pid" ]] || grep -q "Start proc .*${package}" "$out/logcat_full.txt"; then break; fi
    sleep 1
  done
  terminal="$(utc_now)"; result=PASS; code=0; reason=""
  if [[ -z "$pid" ]] && ! grep -q "Start proc .*${package}" "$out/logcat_full.txt"; then result=FAIL; code=1; reason="no PID or ActivityManager process-start evidence"; fi
  printf '%s\n' "$pid" > "$out/pid-initial.txt"
  record_state "$state_file" PROCESS_CREATED "$started" "$terminal" "pidof + dumpsys activity processes + ActivityManager log" "$code" "$key/activity-processes.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/activity-processes.txt" 5; stop_emulator; return 1; fi

  started="$(utc_now)"; visible_ms=""; result=FAIL; code=1; reason="visible top-resumed window not observed"
  for _attempt in $(seq 1 90); do
    "$ADB" shell dumpsys activity activities > "$out/activity-state.txt" 2>&1 || true
    "$ADB" shell dumpsys window windows > "$out/window-state.txt" 2>&1 || true
    if grep -q "$package" "$out/activity-state.txt" && grep -Eq 'topResumedActivity|mResumedActivity' "$out/activity-state.txt" && \
       grep -q "$package" "$out/window-state.txt" && grep -Eq 'mCurrentFocus|isVisible=true|SurfaceView' "$out/window-state.txt"; then
      visible_ms="$(epoch_ms)"; result=PASS; code=0; reason=""; break
    fi
    sleep 1
  done
  terminal="$(utc_now)"
  printf '%s\n' "$visible_ms" > "$out/first-visible-window-epoch-ms.txt"
  record_state "$state_file" WINDOW_VISIBLE "$started" "$terminal" "dumpsys activity activities + dumpsys window windows top-resumed visible Surface" "$code" "$key/window-state.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/window-state.txt" 6; stop_emulator; return 1; fi

  started="$(utc_now)"; result=FAIL; code=1; reason="Godot startup marker absent"
  for _attempt in $(seq 1 120); do grep -q 'Godot Engine v' "$out/logcat_full.txt" && { result=PASS; code=0; reason=""; break; }; sleep 1; done
  terminal="$(utc_now)"; record_state "$state_file" GODOT_STARTED "$started" "$terminal" "Godot Engine startup log marker" "$code" "$key/logcat_full.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/logcat_full.txt" 7; stop_emulator; return 1; fi

  started="$(utc_now)"; result=FAIL; code=1; reason="expected renderer identity absent"
  for _attempt in $(seq 1 120); do
    if grep -q "G0_ANDROID_RENDERER_READY renderer=${expected_renderer}" "$out/logcat_full.txt"; then
      if [[ "$expected_renderer" == gl_compatibility ]] && grep -q 'OpenGL API.*Compatibility' "$out/logcat_full.txt"; then result=PASS; code=0; reason=""; break; fi
      if [[ "$expected_renderer" == mobile ]] && grep -q 'Vulkan .*Forward Mobile' "$out/logcat_full.txt"; then result=PASS; code=0; reason=""; break; fi
    fi
    sleep 1
  done
  terminal="$(utc_now)"; record_state "$state_file" RENDERER_IDENTIFIED "$started" "$terminal" "Godot startup log plus G0_ANDROID_RENDERER_READY" "$code" "$key/logcat_full.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/logcat_full.txt" 8; stop_emulator; return 1; fi

  started="$(utc_now)"; result=FAIL; code=1; reason="mission-start marker absent"
  for _attempt in $(seq 1 120); do grep -q 'BAHRAIN_BRICK_KARAK_MISSION_STARTED' "$out/logcat_full.txt" && { result=PASS; code=0; reason=""; break; }; sleep 1; done
  terminal="$(utc_now)"; record_state "$state_file" MISSION_STARTED "$started" "$terminal" "BAHRAIN_BRICK_KARAK_MISSION_STARTED marker" "$code" "$key/logcat_full.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/logcat_full.txt" 9; stop_emulator; return 1; fi

  started="$(utc_now)"; result=FAIL; code=1; reason="scene-readiness marker absent"
  for _attempt in $(seq 1 120); do grep -q 'BAHRAIN_BRICK_SOUQ_SLICE_READY assets=35 pedestrians=12 traffic=6' "$out/logcat_full.txt" && { result=PASS; code=0; reason=""; break; }; sleep 1; done
  terminal="$(utc_now)"; record_state "$state_file" SCENE_READY "$started" "$terminal" "BAHRAIN_BRICK_SOUQ_SLICE_READY marker" "$code" "$key/logcat_full.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/logcat_full.txt" 10; stop_emulator; return 1; fi

  started="$(utc_now)"; result=FAIL; code=1; reason="warmup or capture-frame marker absent"
  for _attempt in $(seq 1 180); do
    if grep -q 'G0_ANDROID_WARMUP_COMPLETE frame=180' "$out/logcat_full.txt" && grep -q 'G0_ANDROID_CAPTURE_FRAME frame=300' "$out/logcat_full.txt"; then result=PASS; code=0; reason=""; break; fi
    sleep 1
  done
  terminal="$(utc_now)"; record_state "$state_file" CAPTURE_FRAME_REACHED "$started" "$terminal" "warmup frame 180 and capture frame 300 markers" "$code" "$key/logcat_full.txt" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/logcat_full.txt" 11; stop_emulator; return 1; fi

  local alive_all=true
  # Twelve five-second samples are the required sleep 60 liveness window.
  for sample in $(seq -w 1 12); do
    "$ADB" shell dumpsys gfxinfo "$package" framestats > "$out/gfxinfo_samples/${sample}.txt" 2>&1 || true
    "$ADB" shell dumpsys meminfo "$package" > "$out/meminfo_samples/${sample}.txt" 2>&1 || true
    pid_after="$("$ADB" shell pidof "$package" 2>/dev/null | tr -d '\r')"
    [[ -n "$pid_after" ]] || alive_all=false
    sleep 5
  done
  printf '{"process_remained_alive_60s":%s,"initial_pid":"%s","final_pid":"%s","launch_start_epoch_ms":%s,"first_visible_window_epoch_ms":%s,"performance_label":"%s"}\n' \
    "$alive_all" "$pid" "$pid_after" "$launch_start_ms" "${visible_ms:-0}" "$PERFORMANCE_LABEL" > "$out/liveness.json"

  started="$(utc_now)"; "$ADB" exec-out screencap -p > "$out/screenshot.png"; code=$?; terminal="$(utc_now)"
  result=PASS; reason=""; [[ $code -eq 0 && -s "$out/screenshot.png" ]] || { result=FAIL; code=1; reason="screenshot capture failed"; }
  record_state "$state_file" SCREENSHOT_CAPTURED "$started" "$terminal" "adb exec-out screencap -p at 1920x1080" "$code" "$key/screenshot.png" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/screenshot.png" 12; stop_emulator; return 1; fi

  started="$(utc_now)"
  "$ADB" shell input keyevent 3 > "$out/pause-command.txt" 2>&1 || true
  local paused=false resumed=false
  for _attempt in $(seq 1 30); do grep -q 'G0_ANDROID_LIFECYCLE_PAUSED' "$out/logcat_full.txt" && { paused=true; break; }; sleep 1; done
  "$ADB" shell am start -W -n "$resolved" > "$out/resume-command.txt" 2>&1 || true
  for _attempt in $(seq 1 60); do
    "$ADB" shell dumpsys window windows > "$out/window-after-resume.txt" 2>&1 || true
    if grep -q 'G0_ANDROID_LIFECYCLE_RESUMED' "$out/logcat_full.txt" && grep -q "$package" "$out/window-after-resume.txt"; then resumed=true; break; fi
    sleep 1
  done
  terminal="$(utc_now)"; result=PASS; code=0; reason=""
  if [[ "$paused" != true || "$resumed" != true ]]; then result=FAIL; code=1; reason="pause or resume evidence missing"; fi
  printf '{"pause_observed":%s,"resume_observed":%s}\n' "$paused" "$resumed" > "$out/lifecycle.json"
  record_state "$state_file" PAUSE_RESUME_PASSED "$started" "$terminal" "HOME key then explicit activity resume" "$code" "$key/lifecycle.json" "$result" "$reason"
  if [[ "$result" != PASS ]]; then kill "$logcat_pid" >/dev/null 2>&1 || true; fail_remaining_states "$state_file" "$reason" "$key/lifecycle.json" 13; stop_emulator; return 1; fi

  "$ADB" shell dumpsys thermalservice > "$out/thermal.txt" 2>&1 || true
  "$ADB" shell dumpsys activity activities > "$out/activity-final.txt" 2>&1 || true
  "$ADB" shell dumpsys window windows > "$out/window-final.txt" 2>&1 || true
  "$ADB" shell dumpsys dropbox --print > "$out/dropbox.txt" 2>&1 || true
  "$ADB" shell ls -la /data/tombstones > "$out/tombstones.txt" 2>&1 || true
  kill "$logcat_pid" >/dev/null 2>&1 || true
  wait "$logcat_pid" >/dev/null 2>&1 || true

  started="$(utc_now)"; critical_scan "$out/logcat_full.txt" "$out/logcat_critical.txt" "$out/critical_scan.json"; code=$?; terminal="$(utc_now)"
  result=PASS; reason=""; [[ $code -eq 0 ]] || { result=FAIL; reason="critical Java/native/linker/ANR/resource/shader evidence detected"; }
  record_state "$state_file" CRITICAL_LOG_SCAN_PASSED "$started" "$terminal" "critical log scan" "$code" "$key/critical_scan.json" "$result" "$reason"
  if [[ "$result" != PASS ]]; then fail_remaining_states "$state_file" "$reason" "$key/logcat_critical.txt" 14; stop_emulator; return 1; fi

  started="$(utc_now)"; terminal="$(utc_now)"; result=PASS; code=0; reason=""
  for required in "$state_file" "$out/apksigner.txt" "$out/manifest.xml" "$out/install.txt" "$out/resolve-activity.txt" "$out/am-start.txt" "$out/liveness.json" "$out/screenshot.png" "$out/lifecycle.json" "$out/logcat_full.txt" "$out/critical_scan.json" "$out/emulator_environment.json"; do
    [[ -s "$required" ]] || { result=FAIL; code=1; reason="required raw evidence missing: ${required#$OUTPUT_ROOT/}"; break; }
  done
  record_state "$state_file" EVIDENCE_FINALIZED "$started" "$terminal" "raw evidence completeness check" "$code" "$key/state_machine.json" "$result" "$reason"
  stop_emulator
  [[ "$result" == PASS && "$alive_all" == true ]]
}

copy_shared_authority
GL_APK="$SOURCE_ROOT/bahrain-brick-g0-gl-compatibility-x86_64.apk"
MOBILE_APK="$SOURCE_ROOT/bahrain-brick-g0-mobile-vulkan-x86_64.apk"

set +e
run_candidate gl_compatibility gl_compatibility com.brickbahrain.g0gl "$GL_APK" "$SOURCE_ROOT/GL_VARIANT_OVERRIDE.json"
gl_candidate_rc=$?
run_candidate mobile_vulkan mobile com.brickbahrain.g0mobile "$MOBILE_APK" "$SOURCE_ROOT/MOBILE_VARIANT_OVERRIDE.json"
mobile_candidate_rc=$?
set -e

printf '{"schema_version":1,"gl_candidate_rc":%s,"mobile_candidate_rc":%s,"both_candidates_attempted":true,"performance_label":"%s"}\n' \
  "$gl_candidate_rc" "$mobile_candidate_rc" "$PERFORMANCE_LABEL" > "$OUTPUT_ROOT/candidate_exit_codes.json"

# Raw collection is successful when both candidates reached independent terminal evidence, regardless of pass/fail classification.
test -s "$OUTPUT_ROOT/gl_compatibility/state_machine.json"
test -s "$OUTPUT_ROOT/mobile_vulkan/state_machine.json"
exit 0
