import type { GraphMeta, Health, RunInfo, RunMode } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
  return (await response.json()) as T;
}

export const getGraph = () => request<GraphMeta>("/api/graph");
export const getHealth = () => request<Health>("/health");
export const getRun = (runId: string) => request<RunInfo>(`/api/runs/${runId}`);
export const listRuns = (limit = 50) => request<RunInfo[]>(`/api/runs?limit=${limit}`);
export const createRun = (mode: RunMode, config?: string) =>
  request<RunInfo>("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, ...(config ? { config } : {}) }),
  });
export const streamUrl = (runId: string) => `${API_URL}/api/runs/${runId}/stream`;

// Raw artifact content (JSON pretty-print / Markdown render / plain text is the caller's decision, per
// console-contract.md section 2 -- the endpoint itself does no schema translation).
export async function getArtifact(runId: string, name: string): Promise<string> {
  const response = await fetch(`${API_URL}/api/runs/${runId}/artifacts/${encodeURIComponent(name)}`);
  if (!response.ok) throw new Error(`${name}: ${response.status} ${await response.text()}`);
  return response.text();
}

export interface DatasetPreview {
  available: boolean;
  columns: string[];
  rows: Record<string, unknown>[];
  truncated: boolean;
}
export const getDatasetPreview = (runId: string, limit = 15) =>
  request<DatasetPreview>(`/api/runs/${runId}/dataset-preview?limit=${limit}`);
