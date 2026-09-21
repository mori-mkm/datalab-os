"use client";

import { Background, Controls, ReactFlow, type NodeChange } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useMemo, useState } from "react";
import type { RunView } from "@/lib/events";
import { buildEdges, buildNodes, layout } from "@/lib/graph";
import type { GraphMeta } from "@/lib/types";
import { AgentNode } from "./AgentNode";
import { ExecutionEdge } from "./ExecutionEdge";

const nodeTypes = { agent: AgentNode };
const edgeTypes = { execution: ExecutionEdge };

interface Props {
  meta: GraphMeta;
  view: RunView;
  now: number;
  selected: string | null;
  onSelect: (id: string | null) => void;
}

/**
 * Live execution viewer, not a workflow builder: nodes can be panned/zoomed/moved for readability,
 * but moving them only changes local positions, never the workflow (which comes from /api/graph).
 */
export function ExecutionGraph({ meta, view, now, selected, onSelect }: Props) {
  const positions = useMemo(() => layout(meta), [meta]);
  const [moved, setMoved] = useState<Record<string, { x: number; y: number }>>({});

  const nodes = useMemo(
    () => buildNodes(meta, view, now, { ...positions, ...moved }).map((n) => ({ ...n, selected: n.id === selected })),
    [meta, view, now, positions, moved, selected],
  );
  const edges = useMemo(() => buildEdges(meta, view), [meta, view]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    for (const change of changes) {
      if (change.type === "position" && change.position) {
        const { id, position } = change;
        setMoved((m) => ({ ...m, [id]: position }));
      }
    }
  }, []);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onNodeClick={(_, node) => onSelect(node.id)}
      onPaneClick={() => onSelect(null)}
      nodesConnectable={false}
      edgesFocusable={false}
      deleteKeyCode={null}
      colorMode="system"
      fitView
      fitViewOptions={{ padding: 0.08 }}
      minZoom={0.3}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={20} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
