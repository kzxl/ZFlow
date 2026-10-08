import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  useReactFlow
} from '@xyflow/react';

import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatDrawer } from './components/ChatDrawer';
import { NodeConfigModal } from './components/NodeConfigModal';
import { ApiModal } from './components/ApiModal';
import { ContextMenu } from './components/ContextMenu';
import { CustomFlowCard } from './components/nodes/CustomFlowCard';

import { NodeMetadata, WorkflowDefinition, CustomNodeData, ContextMenuState } from './types/workflow';
import { fetchNodeDefinitions, fetchWorkflow, saveWorkflow } from './api/client';

const DEFAULT_FLOW_ID = 'starter_chatbot_flow';

function FlowCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<CustomNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [nodeDefs, setNodeDefs] = useState<NodeMetadata[]>([]);
  const [flowName, setFlowName] = useState('Standard Chatbot Flow');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isApiModalOpen, setIsApiModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Context Menu state
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    isOpen: false,
    type: 'pane',
    x: 0,
    y: 0
  });

  // Copied Node state for clipboard paste
  const [copiedNode, setCopiedNode] = useState<{
    type: string;
    title: string;
    config: Record<string, any>;
  } | null>(null);

  // Modal state
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    nodeId: string | null;
    nodeTitle: string;
    nodeConfig: Record<string, any>;
    nodeType: string;
  }>({
    isOpen: false,
    nodeId: null,
    nodeTitle: '',
    nodeConfig: {},
    nodeType: ''
  });

  const reactFlowInstance = useReactFlow();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  const handleOpenConfigModal = useCallback((nodeId: string, nodeTitle: string, nodeType: string, config: any) => {
    setModalState({
      isOpen: true,
      nodeId,
      nodeTitle: nodeTitle || nodeType,
      nodeConfig: config || {},
      nodeType
    });
  }, []);

  const handleDeleteNode = useCallback((nodeId: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
  }, [setNodes, setEdges]);

  const handleDuplicateNode = useCallback((nodeId: string) => {
    setNodes((nds) => {
      const target = nds.find((n) => n.id === nodeId);
      if (!target) return nds;

      const newId = `node_${target.type}_${Date.now().toString().slice(-4)}`;
      const title = `${target.data?.title || target.type} (Copy)`;
      const config = { ...(target.data?.config || {}) };

      const duplicatedNode: Node<CustomNodeData> = {
        ...target,
        id: newId,
        position: {
          x: target.position.x + 30,
          y: target.position.y + 30
        },
        selected: true,
        data: {
          ...target.data,
          title,
          config,
          openConfigModal: () => handleOpenConfigModal(newId, title, target.type || 'base', config),
          onDuplicate: () => handleDuplicateNode(newId),
          onDelete: () => handleDeleteNode(newId)
        }
      };

      return [...nds.map((n) => ({ ...n, selected: false })), duplicatedNode];
    });
  }, [handleOpenConfigModal, handleDeleteNode, setNodes]);

  const bindNode = useCallback((n: any): Node<CustomNodeData> => {
    const title = n.title || n.data?.title || n.type;
    const config = n.data?.config || {};
    return {
      ...n,
      data: {
        ...n.data,
        title,
        config,
        openConfigModal: () => handleOpenConfigModal(n.id, title, n.type, config),
        onDuplicate: () => handleDuplicateNode(n.id),
        onDelete: () => handleDeleteNode(n.id)
      }
    };
  }, [handleOpenConfigModal, handleDuplicateNode, handleDeleteNode]);

  // Load node definitions & initial default workflow
  useEffect(() => {
    async function init() {
      try {
        const defs = await fetchNodeDefinitions();
        setNodeDefs(defs);

        const flow = await fetchWorkflow(DEFAULT_FLOW_ID);
        if (flow) {
          setFlowName(flow.name || 'Standard Chatbot Flow');
          setNodes(flow.nodes.map(bindNode));
          setEdges(flow.edges || []);
        }
      } catch (err) {
        console.error('Failed to initialize ZFlow canvas:', err);
      }
    }
    init();
  }, [bindNode]);

  const handleSaveNodeConfig = useCallback((nodeId: string, newTitle: string, newConfig: Record<string, any>) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              title: newTitle,
              config: newConfig
            }
          };
        }
        return node;
      })
    );
  }, [setNodes]);

  // Connect edges
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  // Drag-and-drop node onto canvas
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const meta = nodeDefs.find((d) => d.type === type);
      const defaultConfig: Record<string, any> = {};
      if (meta?.configSchema) {
        Object.entries(meta.configSchema).forEach(([k, v]) => {
          defaultConfig[k] = v.default;
        });
      }

      const newNodeId = `node_${type}_${Date.now().toString().slice(-4)}`;
      const newNode: Node<CustomNodeData> = bindNode({
        id: newNodeId,
        type: type,
        position,
        data: {
          title: meta?.name || type,
          config: defaultConfig
        }
      });

      setNodes((nds) => nds.concat(newNode));
    },
    [nodeDefs, reactFlowInstance, bindNode, setNodes]
  );

  // Add node by clicking palette or context menu
  const handleAddNode = useCallback(
    (type: string, position?: { x: number; y: number }) => {
      const meta = nodeDefs.find((d) => d.type === type);
      const defaultConfig: Record<string, any> = {};
      if (meta?.configSchema) {
        Object.entries(meta.configSchema).forEach(([k, v]) => {
          defaultConfig[k] = v.default;
        });
      }

      const newNodeId = `node_${type}_${Date.now().toString().slice(-4)}`;
      const newPos = position || {
        x: 300 + Math.random() * 100,
        y: 200 + Math.random() * 100
      };

      const newNode: Node<CustomNodeData> = bindNode({
        id: newNodeId,
        type: type,
        position: newPos,
        data: {
          title: meta?.name || type,
          config: defaultConfig
        }
      });

      setNodes((nds) => nds.concat(newNode));
    },
    [nodeDefs, bindNode, setNodes]
  );

  const handleDeleteEdge = useCallback(
    (edgeId: string) => {
      setEdges((eds) => eds.filter((e) => e.id !== edgeId));
    },
    [setEdges]
  );

  const handleCopyNode = useCallback(
    (nodeId: string) => {
      const target = nodes.find((n) => n.id === nodeId);
      if (target) {
        setCopiedNode({
          type: target.type || 'base',
          title: (target.data as any)?.title || target.type || 'Node',
          config: { ...((target.data as any)?.config || {}) }
        });
      }
    },
    [nodes]
  );

  const handlePasteNode = useCallback(
    (position?: { x: number; y: number }) => {
      if (!copiedNode) return;

      const newNodeId = `node_${copiedNode.type}_${Date.now().toString().slice(-4)}`;
      const newPos = position || {
        x: 350 + Math.random() * 50,
        y: 250 + Math.random() * 50
      };

      const newNode: Node<CustomNodeData> = bindNode({
        id: newNodeId,
        type: copiedNode.type,
        position: newPos,
        selected: true,
        data: {
          title: `${copiedNode.title} (Copy)`,
          config: { ...copiedNode.config }
        }
      });

      setNodes((nds) => [...nds.map((n) => ({ ...n, selected: false })), newNode]);
    },
    [copiedNode, bindNode, setNodes]
  );

  const handleSelectAll = useCallback(() => {
    setNodes((nds) => nds.map((n) => ({ ...n, selected: true })));
  }, [setNodes]);

  const handleFitView = useCallback(() => {
    reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
  }, [reactFlowInstance]);

  const closeContextMenu = useCallback(() => {
    setContextMenu((prev) => (prev.isOpen ? { ...prev, isOpen: false } : prev));
  }, []);

  const onPaneContextMenu = useCallback(
    (event: MouseEvent | React.MouseEvent) => {
      event.preventDefault();
      const flowPosition = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY
      });
      setContextMenu({
        isOpen: true,
        type: 'pane',
        x: event.clientX,
        y: event.clientY,
        flowPosition
      });
    },
    [reactFlowInstance]
  );

  const onNodeContextMenu = useCallback(
    (event: MouseEvent | React.MouseEvent, node: Node) => {
      event.preventDefault();
      event.stopPropagation();

      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          selected: n.id === node.id
        }))
      );

      setContextMenu({
        isOpen: true,
        type: 'node',
        x: event.clientX,
        y: event.clientY,
        targetId: node.id,
        nodeData: {
          id: node.id,
          type: node.type || 'default',
          title: (node.data as any)?.title || node.type || 'Node',
          config: (node.data as any)?.config || {}
        }
      });
    },
    [setNodes]
  );

  const onEdgeContextMenu = useCallback(
    (event: MouseEvent | React.MouseEvent, edge: Edge) => {
      event.preventDefault();
      event.stopPropagation();

      setContextMenu({
        isOpen: true,
        type: 'edge',
        x: event.clientX,
        y: event.clientY,
        targetId: edge.id,
        edgeData: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle,
          targetHandle: edge.targetHandle
        }
      });
    },
    []
  );

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      // Ctrl+C / Cmd+C: Copy selected node
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c') {
        const selectedNode = nodes.find((n) => n.selected);
        if (selectedNode) {
          e.preventDefault();
          handleCopyNode(selectedNode.id);
        }
      }

      // Ctrl+V / Cmd+V: Paste copied node
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'v') {
        if (copiedNode) {
          e.preventDefault();
          handlePasteNode();
        }
      }

      // Ctrl+D / Cmd+D: Duplicate selected node
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
        const selectedNode = nodes.find((n) => n.selected);
        if (selectedNode) {
          e.preventDefault();
          handleDuplicateNode(selectedNode.id);
        }
      }

      // F: Fit View
      if (e.key.toLowerCase() === 'f' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        handleFitView();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nodes, copiedNode, handleCopyNode, handlePasteNode, handleDuplicateNode, handleFitView]);

  // Custom node types generator
  const nodeTypes = useMemo(() => {
    const typesMap: Record<string, React.ComponentType<any>> = {};
    const knownTypes = ['input', 'prompt', 'llm', 'router', 'tool', 'memory', 'output', 'code', 'http', 'default'];
    
    knownTypes.forEach((t) => {
      const meta = nodeDefs.find((d) => d.type === t);
      typesMap[t] = (props: any) => <CustomFlowCard {...props} metadata={meta} />;
    });

    nodeDefs.forEach((def) => {
      typesMap[def.type] = (props: any) => (
        <CustomFlowCard {...props} metadata={def} />
      );
    });
    return typesMap;
  }, [nodeDefs]);

  // Current workflow definition for live testing & export
  const currentWorkflow: WorkflowDefinition = useMemo(() => {
    return {
      id: DEFAULT_FLOW_ID,
      name: flowName,
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type,
        title: n.data?.title || n.type,
        position: n.position,
        data: {
          title: n.data?.title,
          config: n.data?.config
        }
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle
      }))
    };
  }, [nodes, edges, flowName]);

  // Actions
  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveWorkflow(currentWorkflow);
      alert('Workflow saved successfully!');
    } catch (e: any) {
      alert(`Save failed: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetDefault = async () => {
    try {
      const flow = await fetchWorkflow(DEFAULT_FLOW_ID);
      setFlowName(flow.name || 'Standard Chatbot Flow');
      setNodes(flow.nodes.map(bindNode));
      setEdges(flow.edges || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleClear = () => {
    if (confirm('Are you sure you want to clear the canvas?')) {
      setNodes([]);
      setEdges([]);
    }
  };

  const handleExport = () => {
    const jsonStr = JSON.stringify(currentWorkflow, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${flowName.toLowerCase().replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (content: string) => {
    try {
      const parsed = JSON.parse(content);
      if (parsed.nodes && parsed.edges) {
        setFlowName(parsed.name || 'Imported Workflow');
        setNodes(parsed.nodes.map(bindNode));
        setEdges(parsed.edges);
      }
    } catch (e) {
      alert('Invalid Workflow JSON file format');
    }
  };

  const handleNodeStatusChange = useCallback(
    (nodeId: string, status: 'idle' | 'running' | 'completed' | 'error', durationMs?: number) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id === nodeId) {
            return {
              ...n,
              data: {
                ...n.data,
                status,
                executionTimeMs: durationMs
              }
            };
          }
          return n;
        })
      );
    },
    [setNodes]
  );

  const selectedMeta = nodeDefs.find((d) => d.type === modalState.nodeType);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#090a0f]">
      <Header
        flowName={flowName}
        onFlowNameChange={setFlowName}
        onSave={handleSave}
        onResetDefault={handleResetDefault}
        onClear={handleClear}
        onExport={handleExport}
        onImport={handleImport}
        onOpenApiModal={() => setIsApiModalOpen(true)}
        isChatOpen={isChatOpen}
        onToggleChat={() => setIsChatOpen(!isChatOpen)}
        isSaving={isSaving}
      />

      <div className="flex flex-1 relative overflow-hidden">
        {/* Left Draggable Sidebar Palette */}
        <Sidebar nodeDefs={nodeDefs} onAddNode={handleAddNode} />

        {/* Center Infinite Flow Canvas */}
        <div className="flex-1 h-full relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onPaneContextMenu={onPaneContextMenu}
            onNodeContextMenu={onNodeContextMenu}
            onEdgeContextMenu={onEdgeContextMenu}
            onPaneClick={closeContextMenu}
            onNodeClick={closeContextMenu}
            onEdgeClick={closeContextMenu}
            fitView
            className="bg-[#090a0f]"
          >
            <Background color="#1c2438" gap={20} size={1.5} variant={BackgroundVariant.Dots} />
            <Controls className="!bg-[#0e121e] !border-slate-800 !text-slate-200 fill-slate-200" />
            <MiniMap
              nodeColor="#4f46e5"
              maskColor="rgba(9, 10, 15, 0.75)"
              className="!bg-[#0c0f17] !border !border-slate-800 rounded-xl"
            />
          </ReactFlow>
        </div>

        {/* Right Live Testing Chat Drawer */}
        <ChatDrawer
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          workflow={currentWorkflow}
          onNodeStatusChange={handleNodeStatusChange}
        />
      </div>

      {/* Node Options Configuration Modal */}
      <NodeConfigModal
        isOpen={modalState.isOpen}
        onClose={() => setModalState((prev) => ({ ...prev, isOpen: false }))}
        nodeId={modalState.nodeId}
        nodeTitle={modalState.nodeTitle}
        nodeConfig={modalState.nodeConfig}
        metadata={selectedMeta}
        onSave={handleSaveNodeConfig}
      />

      {/* External API Integration Modal */}
      <ApiModal
        isOpen={isApiModalOpen}
        onClose={() => setIsApiModalOpen(false)}
        flowId={DEFAULT_FLOW_ID}
        flowName={flowName}
      />

      {/* Right-click Context Menu */}
      <ContextMenu
        state={contextMenu}
        nodeDefs={nodeDefs}
        onClose={closeContextMenu}
        onAddNode={handleAddNode}
        onConfigureNode={handleOpenConfigModal}
        onDuplicateNode={handleDuplicateNode}
        onDeleteNode={handleDeleteNode}
        onDeleteEdge={handleDeleteEdge}
        onFitView={handleFitView}
        onSelectAll={handleSelectAll}
        onClearCanvas={handleClear}
        onCopyNode={handleCopyNode}
        onPasteNode={handlePasteNode}
        hasClipboard={!!copiedNode}
      />
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  );
}
