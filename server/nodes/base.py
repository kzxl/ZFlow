"""
ZFlow Base Node and Node Registry.
Defines execution contracts, metadata schemas, and input/output port definitions.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator, Type
from engine.context import ExecutionContext

class PortDef:
    def __init__(self, name: str, data_type: str = "any", label: Optional[str] = None, required: bool = False, description: str = ""):
        self.name = name
        self.data_type = data_type
        self.label = label or name.title()
        self.required = required
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.data_type,
            "label": self.label,
            "required": self.required,
            "description": self.description
        }


class BaseNode(ABC):
    node_type: str = "base"
    name: str = "Base Node"
    category: str = "general" # input, prompt, llm, logic, tool, memory, output
    description: str = ""
    icon: str = "Cpu"

    inputs: List[PortDef] = []
    outputs: List[PortDef] = []
    config_schema: Dict[str, Any] = {} # Schema for user-configurable options

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return {
            "type": cls.node_type,
            "name": cls.name,
            "category": cls.category,
            "description": cls.description,
            "icon": cls.icon,
            "inputs": [p.to_dict() for p in cls.inputs],
            "outputs": [p.to_dict() for p in cls.outputs],
            "configSchema": cls.config_schema
        }

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Standard execution method. Receives resolved inputs and node config, returns dictionary of outputs.
        """
        pass

    async def execute_stream(
        self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming execution method. Default implementation calls execute() and yields the final result.
        Subclasses (like LlmNode) override this to yield real-time tokens.
        """
        result = await self.execute(inputs, config, context)
        yield {"type": "result", "data": result}


class NodeRegistry:
    _registry: Dict[str, Type[BaseNode]] = {}

    @classmethod
    def register(cls, node_class: Type[BaseNode]) -> Type[BaseNode]:
        cls._registry[node_class.node_type] = node_class
        return node_class

    @classmethod
    def get(cls, node_type: str) -> Optional[Type[BaseNode]]:
        return cls._registry.get(node_type)

    @classmethod
    def list_all_metadata(cls) -> List[Dict[str, Any]]:
        return [node_cls.get_metadata() for node_cls in cls._registry.values()]
