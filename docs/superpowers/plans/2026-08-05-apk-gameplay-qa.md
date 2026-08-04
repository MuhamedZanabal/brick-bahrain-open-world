# APK Gameplay QA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an x86_64 Godot Android QA APK, execute it in an accelerated API 35 emulator, and retain screenshots, video, install/launch diagnostics, and logcat as one workflow artifact.

**Architecture:** Reuse the repository's proven production-scene reconstruction/export path, switch only the QA export copy to x86_64, and run a standalone adb probe under ReactiveCircus/android-emulator-runner. The probe extracts APK identity from Android tooling, preserves evidence through an EXIT trap, and fails closed if required media or logs are missing.

**Tech Stack:** Godot 4.3, Android SDK 34/35, Bash, adb, ReactiveCircus/android-emulator-runner, GitHub Actions.

## Global Constraints

- Work on `work/bahrain-brick-reference-visual-upgrade`.
- Do not publish, release, or production-sign the APK.
- Do not use repository secrets.
- Preserve all failure evidence with `if: always()`.
- Use API 35, Google APIs, x86_64, and Pixel 6 for emulator QA.

---

### Task 1: Define the QA contract

**Files:**
- Create: `tests/ci/test_apk_gameplay_qa_contract.py`

- [x] Assert every required evidence path, adb action, emulator setting, and artifact policy.
- [x] Verify the test fails before the workflow and probe exist.

### Task 2: Implement the gameplay probe

**Files:**
- Create executable: `ci/apk-gameplay-probe.sh`

- [x] Extract package, activity, ABI, SDK, and orientation from the APK.
- [x] Boot-wait, install, resolve/launch with monkey fallback, interact, record, screenshot, and capture logs.
- [x] Preserve report and logs through an EXIT trap.
- [x] Validate with `bash -n` and the source contract.

### Task 3: Implement and run emulator CI

**Files:**
- Create: `.github/workflows/apk-gameplay-qa.yml`

- [x] Build a signed x86_64 debug APK from the production-scene source.
- [x] Enable KVM and run API 35 Pixel 6 emulator QA.
- [x] Upload `gameplay-qa-evidence` with `if: always()`.
- [ ] Verify the workflow run and download the artifact.
