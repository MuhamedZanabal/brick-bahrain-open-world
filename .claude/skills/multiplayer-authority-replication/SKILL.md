---
name: multiplayer-authority-replication
description: Design, implement, or audit Bahrain Brick dedicated-server authority, ENet replication, RPC validation, prediction, reconciliation, interest management, reconnect, anti-cheat, or load qualification.
paths:
  - "scripts/*multiplayer*.gd"
  - "scripts/*server*.gd"
  - "server/**"
  - "backend/**"
  - "tests/**/*network*"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(python3 tools/agent_env/verify_environment.py *)
disallowed-tools:
  - mcp__bahrain-brick-local__android_adb_smoke_test
---

## Non-negotiable authority

- The existing listen-server code is scaffolding, not evidence of a dedicated authoritative service.
- Server owns durable state, movement acceptance, rewards, mission completion, inventory, property, and economy.
- Never trust client-reported reward amounts, completion facts, timestamps, or ownership.

## Design procedure

1. Define authenticated peer identity and trust boundaries.
2. Define input commands, validation rules, sequence numbers, replay window, and rate limits.
3. Define server tick, snapshot cadence, interest cells, entity priorities, and bandwidth budget.
4. Add prediction/reconciliation only for latency-sensitive player movement; never predict durable rewards.
5. Make reconnect idempotent and bind restored state to server persistence checkpoints.
6. Record abuse telemetry without logging credentials or sensitive personal data.
7. Stage qualification at 2, 8, 16, 32, 64, then 100 players; do not skip gates.

## Required tests

- Serialization round trips and malformed payload rejection.
- Unauthorized peer and spoofed identity rejection.
- Duplicate/replayed transaction rejection.
- Movement speed/teleport validation with latency tolerance.
- Interest-management visibility boundaries.
- Join/leave/reconnect/server-restart behavior.
- Tick duration, CPU, RAM, bandwidth, packet loss, divergence, and crash evidence.
