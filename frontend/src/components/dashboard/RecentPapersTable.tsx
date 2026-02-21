/**
 * components/dashboard/RecentPapersTable.tsx
 */

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Project, ProjectStatus } from "@/types/api";
import { MoreHorizontal, FileText, Download, Eye } from "lucide-react";
import { format } from "date-fns";
import Link from "next/link";

interface RecentPapersTableProps {
    papers: Project[];
    isLoading: boolean;
}

const STATUS_MAP: Record<ProjectStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
    draft: { label: "Draft", variant: "outline" },
    processing: { label: "Generating", variant: "default" },
    done: { label: "Generated", variant: "secondary" },
    error: { label: "Failed", variant: "destructive" },
};

export function RecentPapersTable({ papers, isLoading }: RecentPapersTableProps) {
    if (isLoading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-12 w-full rounded-lg" />
                ))}
            </div>
        );
    }

    if (papers.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-border/40 rounded-xl bg-muted/10">
                <FileText className="h-12 w-12 text-muted-foreground/30 mb-4" />
                <p className="text-sm font-bold text-muted-foreground">No papers generated yet.</p>
                <p className="text-xs text-muted-foreground/60">Your recent drafts will appear here.</p>
            </div>
        );
    }

    return (
        <div className="rounded-xl border border-border/50 bg-card/50 overflow-hidden shadow-sm">
            <Table>
                <TableHeader className="bg-muted/30">
                    <TableRow className="hover:bg-transparent border-border/20">
                        <TableHead className="text-[11px] font-black uppercase tracking-widest h-11">Paper Name</TableHead>
                        <TableHead className="text-[11px] font-black uppercase tracking-widest h-11">Subject</TableHead>
                        <TableHead className="text-[11px] font-black uppercase tracking-widest h-11">Date</TableHead>
                        <TableHead className="text-[11px] font-black uppercase tracking-widest h-11">Status</TableHead>
                        <TableHead className="text-right h-11"></TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {papers.map((paper) => {
                        const statusCfg = STATUS_MAP[paper.status] || STATUS_MAP.draft;
                        return (
                            <TableRow key={paper.id} className="group border-border/20 transition-colors">
                                <TableCell className="py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 rounded-md bg-primary/5 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                                            <FileText className="h-4 w-4" />
                                        </div>
                                        <span className="font-bold text-sm tracking-tight text-foreground">{paper.name}</span>
                                    </div>
                                </TableCell>
                                <TableCell className="text-sm font-medium text-muted-foreground">
                                    <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-tight px-1.5 h-5">
                                        {paper.subject}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-xs font-semibold text-muted-foreground/60 whitespace-nowrap">
                                    {format(new Date(paper.updatedAt), "MMM dd, yyyy")}
                                </TableCell>
                                <TableCell>
                                    <Badge variant={statusCfg.variant} className="text-[10px] uppercase font-bold tracking-tight px-1.5 h-5">
                                        {statusCfg.label}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-right">
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end" className="w-40 font-bold">
                                            <DropdownMenuItem asChild>
                                                <Link href={`/qpilot/${paper.id}`} className="flex items-center cursor-pointer">
                                                    <Eye className="mr-2 h-4 w-4" /> View / Edit
                                                </Link>
                                            </DropdownMenuItem>
                                            <DropdownMenuItem className="flex items-center cursor-pointer">
                                                <Download className="mr-2 h-4 w-4" /> Download
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        );
                    })}
                </TableBody>
            </Table>
        </div>
    );
}
