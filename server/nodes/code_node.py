"""
Python Code Transformation Node for ZFlow.
Executes custom Python functions for data shaping, regex parsing, and mathematical calculations.
"""
from typing import Dict, Any
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

DEFAULT_PYTHON_CODE = '''def main(inputs, context):
    """
    inputs: dict of incoming port data (e.g. inputs['input_data'])
    context: dict of workflow execution variables
    return: any JSON-serializable value or dict
    """
    text = str(inputs.get("input_data", ""))
    # Example transformation: clean and uppercase
    cleaned = text.strip()
    return {
        "text": cleaned,
        "char_count": len(cleaned),
        "word_count": len(cleaned.split())
    }
'''

@NodeRegistry.register
class CodeNode(BaseNode):
    node_type = "code"
    name = "Python Script"
    category = "logic"
    description = "Executes custom Python code to transform, clean, or structure data across nodes."
    icon = "Code2"

    inputs = [
        PortDef(name="input_data", data_type="any", label="Input Data", required=False),
        PortDef(name="secondary_data", data_type="any", label="Secondary Data", required=False)
    ]
    outputs = [
        PortDef(name="result", data_type="any", label="Output Result"),
        PortDef(name="status", data_type="string", label="Execution Status")
    ]

    config_schema = {
        "code": {
            "type": "textarea",
            "label": "Python Script (main function)",
            "default": DEFAULT_PYTHON_CODE
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        code_str = config.get("code", DEFAULT_PYTHON_CODE)
        
        # Local scope for execution
        local_scope: Dict[str, Any] = {}
        global_scope: Dict[str, Any] = {
            "__builtins__": {
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "dict": dict,
                "list": list,
                "set": set,
                "min": min,
                "max": max,
                "sum": sum,
                "range": range,
                "enumerate": enumerate,
                "isinstance": isinstance
            }
        }

        try:
            exec(code_str, global_scope, local_scope)
            if "main" not in local_scope or not callable(local_scope["main"]):
                raise ValueError("Script must define a 'main(inputs, context)' function.")

            inputs_normalized = dict(inputs)
            if "input" in inputs_normalized and "input_data" not in inputs_normalized:
                inputs_normalized["input_data"] = inputs_normalized["input"]
            if "data" in inputs_normalized and "input_data" not in inputs_normalized:
                inputs_normalized["input_data"] = inputs_normalized["data"]

            res = local_scope["main"](inputs_normalized, context.variables)
            context.set_variable("code_result", res)
            
            return {
                "result": res,
                "status": "success"
            }
        except Exception as e:
            err_msg = f"Script execution error: {str(e)}"
            context.log("error", err_msg)
            return {
                "result": err_msg,
                "status": "error"
            }
