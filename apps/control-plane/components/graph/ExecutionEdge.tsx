import { BaseEdge, getSmoothStepPath, type EdgeProps } from "@xyflow/react";
import type { EdgeState } from "@/lib/events";

/** idle: not traversed yet · active: handoff_started · done: handoff_completed. */
export function ExecutionEdge(props: EdgeProps) {
  const [path] = getSmoothStepPath(props);
  const state = ((props.data as { state?: EdgeState } | undefined)?.state ?? "idle") as EdgeState;
  return <BaseEdge id={props.id} path={path} markerEnd={props.markerEnd} className={`edge edge--${state}`} />;
}
