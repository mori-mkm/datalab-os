import type { Node, NodeProps } from "@xyflow/react";
import { memo } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import type { GraphNodeData } from "@/lib/graph";

// A department container: a real React Flow node whose agents are its children (parentId), so moving or
// selecting it works like any node. Its status comes from the backend's department lifecycle events.
function DepartmentNodeImpl({ data, selected }: NodeProps<Node<GraphNodeData>>) {
  return (
    <div className={`dept dept--${data.status}${selected ? " dept--selected" : ""}`}>
      <div className="dept__head">
        <span className="dept__label">{data.label}</span>
        <span className="dept__role" title={data.role}>
          {data.role}
        </span>
        {data.detail && <span className="node__detail">{data.detail}</span>}
        <StatusBadge status={data.status} />
      </div>
    </div>
  );
}

export const DepartmentNode = memo(DepartmentNodeImpl);
