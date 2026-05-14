# Godot Remote Executor

> Created: 2026-05-13

## What
WorkBuddy skill that executes GDScript code on a running Godot editor/game via Hastur broker-server HTTP API.

## Setup
- Skill name: `godot-remote-executor` (user-level, already installed)
- Transport: TCP/HTTP
- Allows creating/modifying scenes, adjusting node properties, running scripts remotely

## Use Cases
- Rapid iteration without switching between IDE and Godot
- Automated testing of scene setups
- Batch property modifications

## Caveats
- Godot editor (or game runtime) must be running with the broker server
- Only works when the skill is loaded and connection is alive
