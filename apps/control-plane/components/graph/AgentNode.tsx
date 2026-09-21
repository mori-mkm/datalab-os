import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { memo } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import type { AgentNodeData } from "@/lib/graph";

// One node type for every agent/department. A DepartmentNode (a group that expands into a
// subgraph) is a later-phase concern, once departments become real subgraphs.
function AgentNodeImpl({ data, selected }: NodeProps<Node<AgentNodeData>>) {
  return (
    <div className={`node node--${data.status}${selected ? " node--selected" : ""}`}>
      <Handle type="target" position={Position.Top} isConnectable={false} />
      <div className="node__kind">{data.kind}</div>
      <div className="node__label">{data.label}</div>
      <div className="node__role">{data.role}</div>
      <div className="node__foot">
        <StatusBadge status={data.status} />
        {data.detail && <span className="node__detail">{data.detail}</span>}
      </div>
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}

export const AgentNode = memo(AgentNodeImpl);
