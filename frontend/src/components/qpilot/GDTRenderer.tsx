"use client";

/**
 * Shared GDT (Graph / Data-structure / Table) renderer.
 * Used by GeneratedPaperView and resultqp/page.
 */

import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface GDTTableContent {
    headers: string[];
    rows: (string | number)[][];
}

export interface GDTPlotContent {
    x: number[];
    y: number[];
    xlabel?: string;
    ylabel?: string;
    title?: string;
}

export interface GDTGraphContent {
    directed: boolean;
    edges: [string, string][];
    edge_labels?: Record<string, number | string>;
}

export type GDTBlock =
    | { type: "table";    content: GDTTableContent }
    | { type: "plot";     content: GDTPlotContent }
    | { type: "graph_ds"; content: GDTGraphContent }
    | { type: "formula";  content: string }
    | { type: string;     content: any };

// ─── Table ────────────────────────────────────────────────────────────────────

function GDTTable({ content }: { content: GDTTableContent }) {
    return (
        <div className="overflow-x-auto my-2">
            <table className="text-xs border-collapse w-full">
                <thead>
                    <tr>
                        {content.headers.map((h, i) => (
                            <th key={i} className="border border-border bg-muted px-3 py-1.5 text-left font-semibold">
                                {h}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {content.rows.map((row, ri) => (
                        <tr key={ri} className="even:bg-muted/30">
                            {row.map((cell, ci) => (
                                <td key={ci} className="border border-border px-3 py-1.5 min-w-[60px]">
                                    {String(cell)}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ─── Plot (recharts) ──────────────────────────────────────────────────────────

function GDTPlot({ content }: { content: GDTPlotContent }) {
    const data = content.x.map((xv, i) => ({ x: xv, y: content.y[i] ?? 0 }));
    return (
        <div className="my-2">
            {content.title && (
                <p className="text-[11px] font-semibold text-muted-foreground mb-1">{content.title}</p>
            )}
            <ResponsiveContainer width="100%" height={180}>
                <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#d4d4d8" />
                    <XAxis
                        dataKey="x"
                        tick={{ fontSize: 10 }}
                        label={{ value: content.xlabel || "x", position: "insideBottom", offset: -8, fontSize: 10 }}
                    />
                    <YAxis
                        tick={{ fontSize: 10 }}
                        label={{ value: content.ylabel || "y", angle: -90, position: "insideLeft", fontSize: 10 }}
                    />
                    <Tooltip />
                    <Line type="monotone" dataKey="y" stroke="#6366f1" dot={{ r: 3 }} strokeWidth={2} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

// ─── Graph SVG ────────────────────────────────────────────────────────────────

function getEdgeWeight(
    edgeLabels: Record<string, number | string> | undefined,
    from: string,
    to: string,
): string | null {
    if (!edgeLabels) return null;
    const key = Object.keys(edgeLabels).find(
        k => k.includes(`"${from}"`) && k.includes(`"${to}"`)
    );
    return key != null ? String(edgeLabels[key]) : null;
}

function GDTGraph({ content }: { content: GDTGraphContent }) {
    const edges     = content.edges || [];
    const directed  = content.directed ?? false;
    const edgeLbls  = content.edge_labels;

    // Collect unique nodes preserving appearance order
    const nodeSet = new Set<string>();
    edges.forEach(([a, b]) => { nodeSet.add(a); nodeSet.add(b); });
    const nodes = Array.from(nodeSet);
    const n = nodes.length;

    if (n === 0) return null;

    const W = 300, H = 230;
    const cx = W / 2, cy = H / 2;
    const layoutR = Math.min(cx, cy) - 38;
    const nodeR   = 17;
    const ARROW   = "gdt-arrowhead";

    // Circular layout
    const pos: Record<string, { x: number; y: number }> = {};
    nodes.forEach((node, i) => {
        const angle = (2 * Math.PI * i) / n - Math.PI / 2;
        pos[node] = {
            x: cx + layoutR * Math.cos(angle),
            y: cy + layoutR * Math.sin(angle),
        };
    });

    // Detect bidirectional pairs for curved edges
    const edgeSet = new Set(edges.map(([a, b]) => `${a}§${b}`));
    const isBidi  = (a: string, b: string) => edgeSet.has(`${b}§${a}`);

    return (
        <div className="my-2">
            <svg
                width={W}
                height={H}
                viewBox={`0 0 ${W} ${H}`}
                style={{ display: "block", background: "white", borderRadius: 6, border: "1px solid #e4e4e7" }}
            >
                <defs>
                    {directed && (
                        <marker
                            id={ARROW}
                            markerWidth="8"
                            markerHeight="8"
                            refX="7"
                            refY="3"
                            orient="auto"
                        >
                            <path d="M0,0 L0,6 L8,3 z" fill="#71717a" />
                        </marker>
                    )}
                </defs>

                {/* Edges */}
                {edges.map(([from, to], ei) => {
                    const p1 = pos[from];
                    const p2 = pos[to];
                    if (!p1 || !p2) return null;

                    const dx   = p2.x - p1.x;
                    const dy   = p2.y - p1.y;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    const arrowGap = directed ? nodeR + 8 : nodeR;

                    const sx = p1.x + (dx / dist) * nodeR;
                    const sy = p1.y + (dy / dist) * nodeR;
                    const ex = p2.x - (dx / dist) * arrowGap;
                    const ey = p2.y - (dy / dist) * arrowGap;

                    const curved = isBidi(from, to);
                    const curveOff = 20;
                    // Perpendicular offset for curved edges
                    const qx = (sx + ex) / 2 + (curved ? (dy / dist) * curveOff : 0);
                    const qy = (sy + ey) / 2 + (curved ? -(dx / dist) * curveOff : 0);

                    const d = curved
                        ? `M ${sx} ${sy} Q ${qx} ${qy} ${ex} ${ey}`
                        : `M ${sx} ${sy} L ${ex} ${ey}`;

                    // Weight label at midpoint
                    const lx = curved ? qx : (sx + ex) / 2;
                    const ly = curved ? qy : (sy + ey) / 2;
                    const weight = getEdgeWeight(edgeLbls, from, to);

                    return (
                        <g key={ei}>
                            <path
                                d={d}
                                stroke="#71717a"
                                strokeWidth={1.5}
                                fill="none"
                                markerEnd={directed ? `url(#${ARROW})` : undefined}
                            />
                            {weight != null && (
                                <text
                                    x={lx + (curved ? 0 : (dy / dist) * 8)}
                                    y={ly - (curved ? 0 : (dx / dist) * 8) - 3}
                                    textAnchor="middle"
                                    fontSize={9}
                                    fill="#4b5563"
                                    fontWeight="700"
                                >
                                    {weight}
                                </text>
                            )}
                        </g>
                    );
                })}

                {/* Nodes */}
                {nodes.map(node => {
                    const { x, y } = pos[node];
                    return (
                        <g key={node}>
                            <circle cx={x} cy={y} r={nodeR} fill="white" stroke="#374151" strokeWidth={1.5} />
                            <text
                                x={x}
                                y={y}
                                textAnchor="middle"
                                dominantBaseline="middle"
                                fontSize={11}
                                fontWeight="600"
                                fill="#111827"
                            >
                                {node}
                            </text>
                        </g>
                    );
                })}
            </svg>
        </div>
    );
}

// ─── Formula ──────────────────────────────────────────────────────────────────

function GDTFormula({ content }: { content: string }) {
    return (
        <div className="my-2 font-mono text-sm bg-muted/50 rounded px-3 py-1.5 inline-block">
            {content}
        </div>
    );
}

// ─── Main renderer ────────────────────────────────────────────────────────────

export function GDTRenderer({ blocks }: { blocks: GDTBlock[] }) {
    if (!blocks || blocks.length === 0) return null;
    return (
        <div className="mt-2 space-y-1 pl-4 border-l-2 border-primary/30">
            {blocks.map((block, idx) => {
                switch (block.type) {
                    case "table":
                        return <GDTTable key={idx} content={block.content as GDTTableContent} />;
                    case "plot":
                        return <GDTPlot key={idx} content={block.content as GDTPlotContent} />;
                    case "graph_ds":
                        return <GDTGraph key={idx} content={block.content as GDTGraphContent} />;
                    case "formula":
                        return <GDTFormula key={idx} content={String(block.content)} />;
                    default:
                        return null;
                }
            })}
        </div>
    );
}
