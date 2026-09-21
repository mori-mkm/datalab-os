import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { memo } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import type { GraphNodeData } from "@/lib/graph";

// Any executable node: an agent inside a department, or a top-level node (head, review, report).
// Handles are ids the edges refer to: t/b (top/bottom) for handoffs between units, l/r for agents in a department.
function AgentNodeImpl({ data, selected }: NodeProps<Node<GraphNodeData>>) {
  return (
    <div className={`node node--${data.status} node--${data.kind}${selected ? " node--selected" : ""}`}>
      <Handle id="t" type="target" position={Position.Top} isConnectable={false} />
      <Handle id="l" type="target" position={Position.Left} isConnectable={false} />
      {data.kind !== "agent" && <div className="node__kind">{data.kind}</div>}
      <div className="node__label">{data.label}</div>
      <div className="node__role" title={data.role}>
        {data.role}
      </div>
      <div className="node__foot">
        <StatusBadge status={data.status} />
        {data.detail && <span className="node__detail">{data.detail}</span>}
      </div>
      <Handle id="r" type="source" position={Position.Right} isConnectable={false} />
      <Handle id="b" type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}

export const AgentNode = memo(AgentNodeImpl);
