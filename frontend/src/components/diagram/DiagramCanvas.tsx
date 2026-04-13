import "@xyflow/react/dist/style.css";

import { useEffect, useMemo, useState } from "react";
import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeMouseHandler,
  type OnConnect,
  type OnMoveEnd,
  type Viewport,
} from "@xyflow/react";
import type { MouseEvent as ReactMouseEvent } from "react";
import type { DiagramDocument } from "../../lib/diagram";
import type { ThreadDto } from "../../lib/api";

type Props = {
  document: DiagramDocument;
  readOnly?: boolean;
  commentMode?: boolean;
  onDocumentChange?: (doc: DiagramDocument) => void;
  onPickTarget?: (target: { kind: "node" | "edge"; id: string; x: number; y: number }) => void;
  threads?: ThreadDto[];
  onSelectThread?: (threadId: string) => void;
  hideCommentMarkers?: boolean;
};

function toNodes(document: DiagramDocument): Node[] {
  return document.nodes.map((n) => ({
    id: n.id,
    type: n.type ?? "default",
    position: n.position,
    data: {
      label: (() => {
        const icon = n.data?.icon ?? "";
        const glyph = ICON_GLYPH[icon] ?? "";
        const label = n.data?.label ?? n.id;
        return glyph ? `${glyph} ${label}` : label;
      })(),
      rawLabel: n.data?.label ?? n.id,
      icon: n.data?.icon ?? "",
    },
    draggable: true,
    selectable: true,
  }));
}

function toEdges(document: DiagramDocument): Edge[] {
  return document.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: e.type ?? "default",
    label: e.label,
  }));
}

function toDocument(nodes: Node[], edges: Edge[], viewport: Viewport): DiagramDocument {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: (n.type as "default" | "input" | "output" | undefined) ?? "default",
      position: {
        x: Number.isFinite(n.position?.x) ? n.position.x : 0,
        y: Number.isFinite(n.position?.y) ? n.position.y : 0,
      },
      data: {
        label: (() => {
          const d = n.data as { rawLabel?: unknown; label?: unknown } | undefined;
          if (typeof d?.rawLabel === "string") return d.rawLabel ?? "";
          if (typeof d?.label === "string") return d.label ?? "";
          return "";
        })(),
        icon:
          typeof (n.data as { icon?: unknown } | undefined)?.icon === "string"
            ? ((n.data as { icon?: string }).icon ?? "")
            : "",
      },
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type:
        (e.type as
          | "default"
          | "straight"
          | "step"
          | "smoothstep"
          | "simplebezier"
          | "bezier"
          | undefined) ?? "default",
      label: typeof e.label === "string" ? e.label : undefined,
    })),
    viewport: {
      x: Number.isFinite(viewport.x) ? viewport.x : 0,
      y: Number.isFinite(viewport.y) ? viewport.y : 0,
      zoom: Number.isFinite(viewport.zoom) ? viewport.zoom : 1,
    },
  };
}

const ICON_GLYPH: Record<string, string> = {
  // Technical
  cloud: "☁",
  server: "🖥",
  database: "🗄",
  router: "📡",
  switch: "🔀",
  firewall: "🛡",
  load_balancer: "⚖",
  client: "👤",
  service: "⚙",
  storage: "💾",
  queue: "📬",
  api: "🔌",
  worker: "🧰",
  device: "📱",
  container: "📦",
  kubernetes: "☸",
  vm: "🧱",
  cdn: "🌐",
  dns: "🧭",
  vpn: "🔐",
  gateway: "🚪",
  cache: "⚡",
  message_bus: "🚌",
  etl: "🔄",
  data_lake: "🛶",
  warehouse: "🏭",
  monitoring: "📈",
  ci_cd: "🔁",
  auth: "🔑",
  secret: "🗝",
  notebook: "📓",
  // Business
  process: "🧩",
  decision: "🔷",
  start: "🟢",
  end: "🏁",
  document: "📄",
  form: "📝",
  user: "👤",
  team: "👥",
  role: "🎭",
  approval: "✅",
  task: "☑",
  event: "📣",
  kpi: "📊",
  goal: "🎯",
  risk: "⚠",
  control: "🎛",
  invoice: "🧾",
  payment: "💳",
  order: "📦",
  customer: "🤝",
  supplier: "🏢",
  product: "📦",
  sales: "💼",
  marketing: "📣",
  hr: "🧑‍💼",
  finance: "💰",
  support: "🛟",
  project: "📁",
  milestone: "🏁",
  calendar: "📅",
  email: "✉",
  chat: "💬",
  meeting: "📆",
  crm: "🗂",
  erp: "🏬",
  legal: "⚖",
  compliance: "📜",
};

export function DiagramCanvas({
  document,
  readOnly = false,
  commentMode = false,
  onDocumentChange,
  onPickTarget,
  threads = [],
  onSelectThread,
  hideCommentMarkers = false,
}: Props) {
  const [nodes, setNodes] = useState<Node[]>(() => toNodes(document));
  const [edges, setEdges] = useState<Edge[]>(() => toEdges(document));
  const [viewport, setViewport] = useState<Viewport>(() => document.viewport);

  useEffect(() => {
    setNodes(toNodes(document));
    setEdges(toEdges(document));
    setViewport(document.viewport);
  }, [document]);

  const emit = useMemo(
    () => (nextNodes: Node[], nextEdges: Edge[], nextViewport: Viewport) => {
      onDocumentChange?.(toDocument(nextNodes, nextEdges, nextViewport));
    },
    [onDocumentChange],
  );

  const onConnect: OnConnect = (conn: Connection) => {
    if (readOnly) return;
    setEdges((prev) => {
      const next = addEdge({ ...conn, id: `e-${crypto.randomUUID()}` }, prev);
      emit(nodes, next, viewport);
      return next;
    });
  };

  return (
    <div className="relative mx-auto h-[min(82vh,72vw)] min-h-[320px] w-full overflow-hidden rounded-sharp border border-border bg-bg-recessed shadow-elevated">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        defaultViewport={viewport}
        fitView={nodes.length === 0}
        onMoveEnd={
          ((_event, vp) => {
            setViewport(vp);
            emit(nodes, edges, vp);
          }) satisfies OnMoveEnd
        }
        onNodesChange={(changes: NodeChange[]) => {
          if (readOnly) return;
          setNodes((prev) => {
            const next = prev.map((node) => {
              const hit = changes.find((c: NodeChange) => c.id === node.id);
              if (!hit || hit.type !== "position" || !hit.position) return node;
              return { ...node, position: hit.position };
            });
            emit(next, edges, viewport);
            return next;
          });
        }}
        onEdgesChange={(changes: EdgeChange[]) => {
          if (readOnly) return;
          setEdges((prev) => {
            const remove = new Set(
              changes.filter((c: EdgeChange) => c.type === "remove").map((c: EdgeChange) => c.id),
            );
            const next = prev.filter((e) => !remove.has(e.id));
            emit(nodes, next, viewport);
            return next;
          });
        }}
        onConnectEnd={() => undefined}
        onConnect={onConnect}
        onNodeClick={
          ((event, node) => {
            if (!commentMode || !onPickTarget) return;
            const rect = (event.currentTarget as Element).getBoundingClientRect();
            const x = rect.width ? (event.clientX - rect.left) / rect.width : 0;
            const y = rect.height ? (event.clientY - rect.top) / rect.height : 0;
            onPickTarget({ kind: "node", id: node.id, x, y });
          }) satisfies NodeMouseHandler
        }
        onEdgeClick={(event: ReactMouseEvent, edge: Edge) => {
          if (!commentMode || !onPickTarget) return;
          const rect = (event.currentTarget as Element).getBoundingClientRect();
          const x = rect.width ? (event.clientX - rect.left) / rect.width : 0;
          const y = rect.height ? (event.clientY - rect.top) / rect.height : 0;
          onPickTarget({ kind: "edge", id: edge.id, x, y });
        }}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={!readOnly}
        zoomOnDoubleClick={false}
      >
        <MiniMap pannable zoomable />
        <Controls />
        <Background gap={24} size={1} />
      </ReactFlow>
      {!hideCommentMarkers ? (
        <div className="pointer-events-none absolute inset-0 z-20">
          {threads.map((thread) => {
            let left = `${Math.max(0, Math.min(1, thread.anchor_x)) * 100}%`;
            let top = `${Math.max(0, Math.min(1, thread.anchor_y)) * 100}%`;
            if (thread.target_kind === "node" && thread.target_id) {
              const node = nodes.find((n) => n.id === thread.target_id);
              if (node) {
                left = `${node.position.x + 95}px`;
                top = `${node.position.y + 36}px`;
              }
            }
            return (
              <button
                key={thread.id}
                type="button"
                className="pointer-events-auto absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-bg-void bg-primary/90 shadow"
                style={{ left, top }}
                title="Jump to thread"
                onClick={() => onSelectThread?.(thread.id)}
              />
            );
          })}
        </div>
      ) : null}
      <div className="pointer-events-none absolute left-2 top-2 z-20 flex flex-wrap gap-1">
        {nodes.slice(0, 20).map((node) => {
          const icon = String((node.data as { icon?: unknown } | undefined)?.icon ?? "");
          const glyph = ICON_GLYPH[icon] ?? "";
          if (!glyph) return null;
          return (
            <span
              key={`glyph-${node.id}`}
              className="rounded border border-border bg-bg-elevated/90 px-1.5 py-0.5 text-[10px]"
            >
              {glyph}
            </span>
          );
        })}
      </div>
    </div>
  );
}
