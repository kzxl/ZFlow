"""
Subflow Node for ZFlow.
Enables nesting, modularizing, and executing other saved workflows as reusable subgraphs.
Protects against circular dependencies and seamlessly pipes tokens and variables between workflows.
"""
from typing import Dict, Any, AsyncGenerator, List
import copy
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext
from engine.graph import WorkflowGraph

@NodeRegistry.register
class SubflowNode(BaseNode):
    node_type = "subflow"
    name = "Sub-Flow Composite"
    category = "logic"
    description = "Embeds and executes another saved workflow as a nested subgraph with isolated context and data forwarding."
    icon = "Workflow"

    inputs = [
        PortDef(name="input", data_type="string", label="Query / Payload", required=False),
        PortDef(name="variables", data_type="object", label="Injected Variables", required=False)
    ]
    outputs = [
        PortDef(name="output", data_type="string", label="Primary Output"),
        PortDef(name="reply", data_type="string", label="Assistant Reply"),
        PortDef(name="all_outputs", data_type="object", label="Subflow Variables")
    ]

    config_schema = {
        "subflow_id": {
            "type": "string",
            "label": "Subflow ID",
            "default": "default_flow"
        },
        "inherit_context": {
            "type": "boolean",
            "label": "Inherit Parent Context Variables",
            "default": True
        },
        "stream_subflow_tokens": {
            "type": "boolean",
            "label": "Stream Subflow Tokens to Client",
            "default": True
        },
        "max_subflow_depth": {
            "type": "number",
            "label": "Max Nesting Depth",
            "min": 1,
            "max": 10,
            "default": 5
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Non-streaming execution of subflow.
        """
        result_data: Dict[str, Any] = {}
        async for chunk in self.execute_stream(inputs, config, context):
            if chunk.get("type") == "result":
                result_data = chunk.get("data", {})
        return result_data

    async def execute_stream(
        self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        from api.workflows import load_flow_data
        from engine.runner import WorkflowRunner

        subflow_id = str(config.get("subflow_id", "default_flow")).strip()
        inherit_ctx = config.get("inherit_context", True)
        stream_tokens = config.get("stream_subflow_tokens", True)
        max_depth = int(config.get("max_subflow_depth", 5))

        # Circular dependency & depth check
        current_stack: List[str] = list(context.get_variable("_subflow_call_stack") or [])
        if len(current_stack) >= max_depth:
            err_msg = f"Subflow recursion limit exceeded: maximum depth {max_depth} reached (Call stack: {' -> '.join(current_stack)})"
            context.log("error", err_msg)
            yield {"type": "result", "data": {"output": f"[Subflow Error: {err_msg}]", "reply": "", "all_outputs": {}}}
            return

        if current_stack.count(subflow_id) >= 2:
            err_msg = f"Circular subflow dependency detected on '{subflow_id}'. Aborting subflow invocation."
            context.log("error", err_msg)
            yield {"type": "result", "data": {"output": f"[Subflow Error: {err_msg}]", "reply": "", "all_outputs": {}}}
            return

        # Load child workflow definition
        try:
            flow_data = load_flow_data(subflow_id)
        except Exception as exc:
            err_msg = f"Failed to load subflow '{subflow_id}': {str(exc)}"
            context.log("error", err_msg)
            yield {"type": "result", "data": {"output": f"[Subflow Error: {err_msg}]", "reply": "", "all_outputs": {}}}
            return

        # Prepare child variables
        child_vars: Dict[str, Any] = {}
        if inherit_ctx:
            child_vars.update(copy.deepcopy(context.variables))

        # Injected input payload & parameters
        in_val = inputs.get("input")
        if in_val is None:
            in_val = context.get_variable("input") or context.get_variable("query", "")
        child_vars["input"] = in_val
        child_vars["query"] = in_val
        child_vars["prompt"] = in_val

        in_vars = inputs.get("variables")
        if isinstance(in_vars, dict):
            child_vars.update(in_vars)

        # Update call stack
        child_vars["_subflow_call_stack"] = current_stack + [subflow_id]

        child_sess_id = f"{context.session_id}_sub_{subflow_id}"
        child_context = ExecutionContext(
            session_id=child_sess_id,
            chat_history=copy.deepcopy(context.chat_history),
            initial_variables=child_vars
        )

        child_graph = WorkflowGraph.from_dict(flow_data)
        runner = WorkflowRunner(max_steps=50)

        context.log("info", f"Executing Sub-flow '{subflow_id}' (Depth: {len(current_stack) + 1})...")

        # Stream child execution
        final_reply = ""
        async for sse_event in runner.run_stream(child_graph, child_context):
            event_type = sse_event.get("event")
            event_data = sse_event.get("data", {})

            if event_type == "token" and stream_tokens:
                token_text = event_data.get("token", "")
                final_reply += token_text
                yield {"type": "token", "token": token_text}
            elif event_type == "workflow_complete":
                if not final_reply:
                    final_reply = str(event_data.get("final_output") or "")

        # Extract outputs
        subflow_final_output = child_context.get_variable("final_output") or final_reply or child_context.get_variable("reply") or ""
        subflow_reply = child_context.get_variable("reply") or final_reply or subflow_final_output

        result_payload = {
            "output": subflow_final_output,
            "reply": subflow_reply,
            "all_outputs": child_context.variables
        }

        context.log("info", f"Sub-flow '{subflow_id}' completed successfully.")
        yield {"type": "result", "data": result_payload}
