# Hex-Star Node Map

> Created: 2026-05-13

## Concept
Graph-based world navigation using hex-star shaped nodes instead of traditional tilemap.

## Architecture
- Nodes represent locations/areas
- Edges represent connections between locations
- Star-shaped connectors for visual style (water-ink aesthetic)

## Implementation Notes
- Part of Godot 4.6.1 RPG project at `D:/RPG/`
- Needs integration with dialogue system for NPC encounters
- Camera system TBD (follow player vs. free pan)

## References
- Godot GraphNode or custom Control-based rendering
- Consider `GraphEdit` node as starting point
