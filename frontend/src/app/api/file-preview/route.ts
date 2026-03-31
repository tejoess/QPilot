import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
    const target = req.nextUrl.searchParams.get("url");
    const name = req.nextUrl.searchParams.get("name") || "document";

    if (!target) {
        return NextResponse.json({ error: "Missing url parameter" }, { status: 400 });
    }

    let parsed: URL;
    try {
        parsed = new URL(target);
    } catch {
        return NextResponse.json({ error: "Invalid url parameter" }, { status: 400 });
    }

    if (!["http:", "https:"].includes(parsed.protocol)) {
        return NextResponse.json({ error: "Only http/https URLs are allowed" }, { status: 400 });
    }

    try {
        const upstream = await fetch(parsed.toString(), { cache: "no-store" });
        if (!upstream.ok || !upstream.body) {
            return NextResponse.json({ error: "Failed to fetch source file" }, { status: 502 });
        }

        const sourceHint = `${parsed.pathname} ${name}`.toLowerCase();
        const isPdf = sourceHint.includes(".pdf");
        const isDocx = sourceHint.includes(".docx");
        const upstreamType = upstream.headers.get("content-type") || "application/octet-stream";
        const contentType = isPdf
            ? "application/pdf"
            : isDocx
                ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                : upstreamType;

        return new NextResponse(upstream.body, {
            status: 200,
            headers: {
                "content-type": contentType,
                // Force browser inline rendering in iframe where possible.
                "content-disposition": `inline; filename="${name.replace(/"/g, "")}"`,
                "cache-control": "no-store",
            },
        });
    } catch {
        return NextResponse.json({ error: "Preview proxy failed" }, { status: 502 });
    }
}

