# Bahrain Brick Graphics Upgrade v1 — G0 Terminal Report

## Classification

```text
G0_EVIDENCE_INSUFFICIENT
```

No renderer is selected, renderer defaults remain unchanged, and G1 remains blocked.

## Source authority

Renderer-evidence authority is `6ade72ed02084791128dcf4a91223e695d802c15`. PR #59 remains frozen at `5b4e2466ef84f3984f3bf336b31925d4d2e97a7f`. The execution-proven census is 1,256 frozen files and 1,279 graphics files, with 23 authorized additions, zero modified frozen paths, zero removed frozen paths, and 21 passing contracts.

`scripts/world.gd` remains governed by `BYTE_PROTECT_EXACT_FROZEN_WORLD_GD`; `_exit_tree` is absent and no claim is made that it exists.

## Tier A

Run `30064876927`, job `89393944500`, artifact `8586133620` completed successfully and passed enforcement. GL Compatibility and Mobile Vulkan used one byte-identical imported state. Both exited 0, matched startup renderer identity, reached readiness and mission markers, produced valid non-black 1920×1080 screenshots, recorded 360 metric rows, and reported zero critical errors.

Host metrics are diagnostic only. GL averaged 163.190 ms per frame with 2,138 draw calls; Mobile averaged 151.381 ms with 1,773 draw calls. Screenshot mean absolute channel delta was 21.241 and RMSE was 31.144. This does not select a renderer.

## Tier B existing artifact

Original run `30064876896`, artifact `8586122615`, is classified `TIER_B_APK_VERIFICATION_FAILURE`. Export, signing and `apksigner verify` succeeded. Legacy `aapt dump badging` then failed with:

`AndroidManifest.xml:0: error: failed to read attribute 'android:required': attribute is not an integer value`

This is an APK-verification harness failure, not a renderer failure.

Reducer run `30086594777` succeeded without rerunning Android and emitted the required inventories under `reports/graphics/g0/tier_b_reduction/`.

## Authorized targeted retry

The single authorized retry was run `30086966524`, job `89461293320`, artifact `8594128472`. It reused exact APK bytes, repeated neither reconstruction nor export, and passed signature, AAPT2 package-name and x86_64 ABI verification. The API 34 x86_64 emulator booted. The GL APK installed and launcher injection returned 0, but `pidof com.brickbahrain.g0gl` remained empty. No renderer identity, scene marker, screenshot or lifecycle evidence was reached; Mobile was not attempted.

Terminal classification is:

```text
TIER_B_APP_LAUNCH_FAILURE
```

Root cause is not proven and no renderer failure is proven.

## Terminalization exception

A terminal-packaging push unintentionally retriggered the same path-filtered workflow as run `30087878937`. It completed before cancellation workflow run `30088001461` took effect. Duplicate artifact `8594493723` has digest `sha256:ffa6bbaeaa7ba4e99847f24b957a8484f38c7758b9a8181e125f2eca7c58814a`.

The duplicate replay is excluded from renderer adjudication and does not change `TIER_B_APP_LAUNCH_FAILURE`. However, the requested no-more-than-one-execution constraint was not fully satisfied; `retry_limit_compliance` is false. Automatic reducer, targeted-resume and one-shot cancellation PR triggers are archived.

## Physical-device boundary

Named physical-device evidence is unavailable. The maximum admissible gate result remains `G0_EVIDENCE_INSUFFICIENT`. The unexecuted handoff package is in `reports/graphics/g0/device_handoff/`.

## Stop

Tier A is terminal; Tier B is reduced and diagnosed; the authorized retry and unintended duplicate replay are fully disclosed; terminal reports and device handoff are emitted. G1 has not begun.
