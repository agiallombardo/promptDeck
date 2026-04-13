export type DiagramNode = {
  id: string;
  type?: "default" | "input" | "output";
  position: { x: number; y: number };
  data: { label?: string; icon?: string };
};

export type DiagramEdge = {
  id: string;
  source: string;
  target: string;
  type?: "default" | "straight" | "step" | "smoothstep" | "simplebezier" | "bezier";
  label?: string;
};

export type DiagramDocument = {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  viewport: { x: number; y: number; zoom: number };
};

export function blankDiagramDocument(): DiagramDocument {
  return { nodes: [], edges: [], viewport: { x: 0, y: 0, zoom: 1 } };
}

function finite(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return fallback;
}

export function decodeDiagramDocumentSafe(raw: unknown): {
  document: DiagramDocument;
  repaired: boolean;
} {
  if (!raw || typeof raw !== "object") {
    return { document: blankDiagramDocument(), repaired: true };
  }
  let repaired = false;
  const src = raw as Record<string, unknown>;
  const nodesRaw = Array.isArray(src.nodes) ? src.nodes : ((repaired = true), []);
  const edgesRaw = Array.isArray(src.edges) ? src.edges : ((repaired = true), []);
  const viewportRaw =
    src.viewport && typeof src.viewport === "object"
      ? (src.viewport as Record<string, unknown>)
      : ((repaired = true), {});
  const nodes: DiagramNode[] = nodesRaw
    .map((row, idx) => {
      if (!row || typeof row !== "object") return null;
      const r = row as Record<string, unknown>;
      const id = typeof r.id === "string" ? r.id.trim() : "";
      if (!id) {
        repaired = true;
        return null;
      }
      const pos =
        r.position && typeof r.position === "object" ? (r.position as Record<string, unknown>) : {};
      const data = r.data && typeof r.data === "object" ? (r.data as Record<string, unknown>) : {};
      const label = typeof data.label === "string" ? data.label : undefined;
      const icon = typeof data.icon === "string" ? data.icon : undefined;
      return {
        id,
        type:
          r.type === "input" || r.type === "output" || r.type === "default" ? r.type : "default",
        position: {
          x: finite(pos.x, (idx % 6) * 260),
          y: finite(pos.y, Math.floor(idx / 6) * 160),
        },
        data: { label, icon },
      } satisfies DiagramNode;
    })
    .filter((v): v is DiagramNode => v != null);
  const nodeIds = new Set(nodes.map((n) => n.id));
  const edges: DiagramEdge[] = edgesRaw
    .map((row, idx) => {
      if (!row || typeof row !== "object") return null;
      const r = row as Record<string, unknown>;
      const id = typeof r.id === "string" && r.id.trim() ? r.id : `e${idx + 1}`;
      const source = typeof r.source === "string" ? r.source : "";
      const target = typeof r.target === "string" ? r.target : "";
      if (!nodeIds.has(source) || !nodeIds.has(target)) {
        repaired = true;
        return null;
      }
      const type =
        r.type === "default" ||
        r.type === "straight" ||
        r.type === "step" ||
        r.type === "smoothstep" ||
        r.type === "simplebezier" ||
        r.type === "bezier"
          ? r.type
          : "default";
      const label = typeof r.label === "string" ? r.label : undefined;
      return { id, source, target, type, label } satisfies DiagramEdge;
    })
    .filter((v): v is DiagramEdge => v != null);
  return {
    document: {
      nodes,
      edges,
      viewport: {
        x: finite(viewportRaw.x, 0),
        y: finite(viewportRaw.y, 0),
        zoom: finite(viewportRaw.zoom, 1),
      },
    },
    repaired,
  };
}

export function decodeDiagramDocument(raw: unknown): DiagramDocument {
  return decodeDiagramDocumentSafe(raw).document;
}
