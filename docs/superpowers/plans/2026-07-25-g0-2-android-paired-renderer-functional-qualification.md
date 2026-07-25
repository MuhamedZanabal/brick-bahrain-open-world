# G0.2 Android Paired-Renderer Functional Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Recover the exact paired APKs, execute independent GL and Mobile Android qualification on equivalent API 34 baselines, and commit terminal evidence without changing production renderer defaults.

**Architecture:** A one-shot PR-open workflow verifies the source artifact and APK hashes, runs a shared explicit state-machine collector for both candidates on recreated equivalent AVDs, and finalizes the required report and handoff outputs.

**Tech Stack:** GitHub Actions, Bash, Python 3, Android SDK API 34, ADB, AAPT2, apksigner, apkanalyzer, readelf, Pillow.

## Tasks

1. Establish exact G0.2 authority and contract-first tests.
2. Recover the exact artifact pair and shared-import authority without rebuilding.
3. Execute independent candidate state machines with non-fail-fast sequencing.
4. Finalize candidate classifications, screenshots, metrics, and terminal outcome.
5. Commit reports and update the dual-renderer physical-device handoff.
6. Verify PR #59, PR #60, and PR #61 remain unchanged; stop before G1.
