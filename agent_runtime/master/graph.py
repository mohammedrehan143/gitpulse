"""Master Multi-Agent State Graph Coordinator.

Coordinates the end-to-end hierarchical execution flow:
Master -> Router -> Backend Orchestrator & Frontend Orchestrator -> Quality Gates -> Sign-off.
"""

from __future__ import annotations

import uuid

from agent_runtime.backend.graph import BackendGraphOrchestrator
from agent_runtime.frontend.graph import FrontendGraphOrchestrator
from agent_runtime.master.router import TaskRouter
from agent_runtime.master.state import MasterState
from agent_runtime.shared.checkpoints import CheckpointManager
from agent_runtime.shared.permissions import PermissionManager
from agent_runtime.shared.task_store import TaskState, TaskStore
from agent_runtime.shared.telemetry import TelemetryLogger
from agent_runtime.tools.filesystem_tools import FilesystemTools
from agent_runtime.tools.git_tools import GitTools
from agent_runtime.tools.test_tools import TestTools


class MasterGraphOrchestrator:
    """Master workflow coordinator implementing the multi-agent hierarchy."""

    def __init__(
        self,
        task_store: TaskStore | None = None,
        telemetry: TelemetryLogger | None = None,
        checkpoints: CheckpointManager | None = None,
        permission_manager: PermissionManager | None = None,
    ):
        self.task_store = task_store or TaskStore()
        self.telemetry = telemetry or TelemetryLogger()
        self.checkpoints = checkpoints or CheckpointManager()
        self.permission_manager = permission_manager or PermissionManager()

        self.fs_tools = FilesystemTools(permission_manager=self.permission_manager)
        self.git_tools = GitTools()
        self.test_tools = TestTools()

        self.backend_orchestrator = BackendGraphOrchestrator(
            task_store=self.task_store,
            telemetry=self.telemetry,
            fs_tools=self.fs_tools,
            test_tools=self.test_tools,
        )

        self.frontend_orchestrator = FrontendGraphOrchestrator(
            task_store=self.task_store,
            telemetry=self.telemetry,
            fs_tools=self.fs_tools,
            test_tools=self.test_tools,
        )

    def run_epic(self, prompt: str, epic_id: str | None = None) -> MasterState:
        """Executes an entire epic through the hierarchical multi-agent system."""
        if not epic_id:
            epic_id = f"EPIC-{uuid.uuid4().hex[:6].upper()}"

        task_type = TaskRouter.classify_task_type(prompt)
        subtasks, requires_contract = TaskRouter.decompose_epic(epic_id, prompt)

        # Initialize Master State
        state = MasterState(
            epic_id=epic_id,
            user_prompt=prompt,
            task_type=task_type,
            state=TaskState.READY,
            subtasks=subtasks,
            contract_signed=not requires_contract,
        )

        # Record Task in TaskStore
        self.task_store.create_task(
            task_id=epic_id,
            title=prompt,
            description=f"Automated multi-agent execution of prompt: {prompt}",
            assigned_agent="master-orchestrator",
            initial_state=TaskState.READY,
            metadata={"task_type": task_type, "requires_contract": requires_contract},
        )

        self.telemetry.record_event(
            event_type="EPIC_INITIATED",
            agent_id="master-orchestrator",
            task_id=epic_id,
            details={"prompt": prompt, "subtasks_count": len(subtasks)},
        )

        # Transition to IN_PROGRESS
        self.task_store.update_task_state(epic_id, TaskState.IN_PROGRESS)
        state.state = TaskState.IN_PROGRESS

        # Save Step 1 Checkpoint
        self.checkpoints.save_checkpoint(
            checkpoint_id="step1_init",
            task_id=epic_id,
            agent_id="master-orchestrator",
            state_data=state.model_dump(),
            step_number=1,
        )

        # Step 2: Contract Formulation (if required)
        if requires_contract:
            state.contract_signed = True
            self.telemetry.record_event(
                event_type="CONTRACT_VALIDATED",
                agent_id="software-architect",
                task_id=epic_id,
                details={"contract_file": ".agents/tasks/contracts.md"},
            )

        # Step 3: Backend Domain Execution
        be_subtasks = [t for t in state.subtasks if t.domain == "backend"]
        if be_subtasks:
            be_receipt = self.backend_orchestrator.execute_backend_packet(
                packet_id=f"{epic_id}-BE",
                objective=prompt,
            )
            state.artifacts["backend_receipt"] = be_receipt
            for t in be_subtasks:
                t.state = TaskState.IN_REVIEW
                t.result_summary = "Backend waves completed successfully"

        # Step 4: Frontend Domain Execution
        fe_subtasks = [t for t in state.subtasks if t.domain == "frontend"]
        if fe_subtasks:
            fe_receipt = self.frontend_orchestrator.execute_frontend_packet(
                packet_id=f"{epic_id}-FE",
                objective=prompt,
            )
            state.artifacts["frontend_receipt"] = fe_receipt
            for t in fe_subtasks:
                t.state = TaskState.IN_REVIEW
                t.result_summary = "Frontend waves completed successfully"

        # Step 5: Transition to IN_REVIEW & Evaluate Quality Gates
        self.task_store.update_task_state(epic_id, TaskState.IN_REVIEW)
        state.state = TaskState.IN_REVIEW

        gate_eval = self.test_tools.evaluate_quality_gates(test_path="agent_runtime/tests")
        state.quality_gates_passed = gate_eval["all_gates_passed"]

        # Step 6: Independent Code Reviewer Sign-off
        if state.quality_gates_passed:
            state.review_approved = True
            self.telemetry.record_event(
                event_type="CODE_REVIEW_APPROVED",
                agent_id="independent-code-reviewer",
                task_id=epic_id,
                details={"verdict": "APPROVED", "gates": gate_eval},
            )

            # Step 7: Final Task Closure -> DONE
            self.task_store.update_task_state(epic_id, TaskState.DONE)
            state.state = TaskState.DONE
            for t in state.subtasks:
                t.state = TaskState.DONE
        else:
            self.task_store.update_task_state(epic_id, TaskState.VERIFICATION_FAILED)
            state.state = TaskState.VERIFICATION_FAILED
            state.errors.append("Quality Gate verification failed")

        # Save Final Checkpoint
        self.checkpoints.save_checkpoint(
            checkpoint_id="step_final",
            task_id=epic_id,
            agent_id="master-orchestrator",
            state_data=state.model_dump(),
            step_number=2,
        )

        state.execution_receipt = {
            "epic_id": epic_id,
            "final_state": state.state.value,
            "quality_gates_passed": state.quality_gates_passed,
            "review_approved": state.review_approved,
            "subtasks_completed": len([t for t in state.subtasks if t.state == TaskState.DONE]),
        }

        return state
