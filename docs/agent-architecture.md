# GitPulse Multi-Agent Orchestration Architecture

## 1. Principles of Organization
The multi-agent system uses strict hierarchical coordination rather than a peer-to-peer flat mesh:
1. **Master Orchestrator (Level 0)** holds single top-level strategic authority.
2. **Backend & Frontend Orchestrators (Level 1)** operate independently within their domain and report structured receipts.
3. **Specialized Engineering Agents (Level 2)** perform focused work within isolated file boundaries.
4. **Shared Cross-Cut Squad** enforces architectural consistency, security, and quality gates.

## 2. Programmatic Runtime (`agent_runtime/`)
The Python orchestration engine implements:
- `TaskStore`: Persistent state tracking with legal state transition enforcement.
- `PermissionManager`: Sandboxes file write access per agent persona.
- `CheckpointManager`: Point-in-time state snapshots for crash recovery.
- `TelemetryLogger`: Append-only structured JSONL event logging.
- `TestTools`: Evaluator for Quality Gates 1 through 4.
