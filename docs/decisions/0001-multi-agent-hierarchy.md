# ADR 0001: Hierarchical Multi-Agent Architecture

## Status
Accepted

## Context
Large-scale software development with LLM agents frequently degrades into chaotic deadlocks, file collisions, and hallucinated interfaces when organized as a flat peer-to-peer network.

## Decision
We enforce a strict 3-tier hierarchy:
- Master Orchestrator (Level 0)
- Domain Orchestrators: Backend & Frontend (Level 1)
- Specialized Engineers (Level 2)
Cross-domain communication requires binding interface contracts approved by the Software Architect.

## Consequences
- Positive: Predictable task execution, bounded retries, zero cross-domain file collisions.
- Positive: Enforceable Quality Gates (1 to 4) before task closure.
- Negative: Requires formal handoff overhead and contract schemas.
