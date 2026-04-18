"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { FileText, Database, Plus, Search, Calendar, Download, Eye, Trash, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getUserDocuments, deleteDocumentAndBlob } from "@/actions/dashboardActions";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useUser } from "@clerk/nextjs";

export default function RepositoryPage() {
    const { isLoaded, user } = useUser();
    const [documents, setDocuments] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!isLoaded) return;
        if (!user) {
            setDocuments([]);
            setIsLoading(false);
            return;
        }

        setIsLoading(true);
        getUserDocuments().then(docs => {
            setDocuments(docs);
            setIsLoading(false);
        });
    }, [isLoaded, user?.id]);

    const getPreviewUrl = (url: string, name?: string) => {
        const safeName = encodeURIComponent(name || "document");
        return `/api/file-preview?url=${encodeURIComponent(url)}&name=${safeName}`;
    };

    return (
        <SidebarProvider style={{ "--sidebar-width": "240px", "--sidebar-width-icon": "70px" } as React.CSSProperties}>
            <div className="flex h-screen w-full bg-background overflow-hidden">
                <QPilotSidebar />
                <SidebarInset className="flex-1 overflow-auto bg-slate-50/30 dark:bg-slate-950/20">
                    <main className="max-w-6xl mx-auto px-6 py-10 space-y-10">
                        {/* Header */}
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-[0.2em]">
                                <Database className="h-3 w-3" />
                                Knowledge Base
                            </div>
                            <div className="flex justify-between items-start">
                                <div>
                                    <h1 className="text-3xl font-bold tracking-tight text-foreground">Document Repository</h1>
                                    <p className="text-sm text-muted-foreground mt-1 max-w-xl">
                                        Manage all your uploaded syllabus files and previous year question papers. These documents act as the context for QPilot generation.
                                    </p>
                                </div>
                                <Button className="bg-primary text-primary-foreground shadow-md shadow-primary/20">
                                    <Plus className="h-4 w-4 mr-2" />
                                    Upload Document
                                </Button>
                            </div>
                        </div>

                        {/* Search and Filters */}
                        <div className="flex items-center gap-4 bg-card p-3 rounded-2xl border border-border/50 shadow-sm">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <input 
                                    type="text" 
                                    placeholder="Search syllabus or PYQs..." 
                                    className="w-full bg-transparent border-none focus:outline-none focus:ring-0 pl-10 text-sm font-medium"
                                />
                            </div>
                            <Button variant="secondary" size="sm" className="hidden sm:flex rounded-xl font-bold">
                                Syllabus Files
                            </Button>
                            <Button variant="ghost" size="sm" className="hidden sm:flex rounded-xl text-muted-foreground">
                                PYQ Files
                            </Button>
                        </div>

                        {/* List */}
                        {isLoading ? (
                            <div className="flex justify-center flex-col items-center h-40 opacity-50">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                <span className="mt-4 text-sm font-semibold text-muted-foreground">Loading Azure Repository...</span>
                            </div>
                        ) : documents.length === 0 ? (
                            <div className="flex flex-col items-center justify-center p-12 border border-dashed rounded-xl border-border/50 bg-card/50">
                                <Database className="h-10 w-10 text-muted-foreground/30 mb-3" />
                                <p className="text-muted-foreground font-medium">No documents uploaded yet.</p>
                            </div>
                        ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {documents.map((doc) => (
                                <Card key={doc.id} className="group overflow-hidden border-border/50 bg-card hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                                    <CardContent className="p-5 flex flex-col h-full gap-4">
                                        <div className="flex justify-between items-start">
                                            <div className="p-3 bg-primary/10 text-primary rounded-xl">
                                                <FileText className="h-5 w-5" />
                                            </div>
                                            <span className={cn(
                                                "text-[9px] font-black px-2 py-0.5 rounded-full border border-current/20 shadow-sm transition-all",
                                                doc.type === 'Syllabus' ? 'bg-blue-500/10 text-blue-600' : 
                                                doc.type === 'PYQ Upload' ? 'bg-purple-500/10 text-purple-600' :
                                                doc.type === 'Answer Key' ? 'bg-emerald-500/10 text-emerald-600' :
                                                doc.type === 'Generated PDF' ? 'bg-rose-500/10 text-rose-600' :
                                                doc.type === 'DOCX Template' ? 'bg-amber-500/10 text-amber-600' :
                                                doc.type === 'Generated DOCX' ? 'bg-sky-500/10 text-sky-600' :
                                                'bg-muted text-muted-foreground'
                                            )}>
                                                 {doc.type}
                                             </span>
                                        </div>
                                        
                                        <div className="flex-1">
                                            <h3 className="font-bold text-[15px] leading-tight line-clamp-2">{doc.name}</h3>
                                            <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground font-medium">
                                                <div className="flex items-center gap-1.5"><Calendar className="h-3 w-3" /> {doc.date}</div>
                                                <div>• {doc.size}</div>
                                            </div>
                                        </div>

                                        <div className="flex gap-2 pt-2 border-t border-border/50 mt-auto">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="flex-1 text-xs shadow-none"
                                                onClick={() => window.open(getPreviewUrl(doc.url, doc.name), "_blank", "noopener,noreferrer")}
                                            >
                                                <Eye className="h-3 w-3 mr-1" /> View
                                            </Button>
                                            <Button variant="outline" size="sm" className="flex-1 text-xs shadow-none" onClick={() => window.open(doc.url, '_blank')}>
                                                <Download className="h-3 w-3 mr-1" /> Download
                                            </Button>
                                        </div>
                                        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                                            <Button 
                                                variant="ghost" 
                                                size="sm" 
                                                className="w-full text-xs text-destructive hover:bg-destructive/10 mt-1"
                                                onClick={async () => {
                                                    const ok = await deleteDocumentAndBlob(doc.id, doc.url);
                                                    if(ok) {
                                                        setDocuments(documents.filter(d => d.id !== doc.id));
                                                        toast.success("Document deleted permanently.");
                                                    } else {
                                                        toast.error("Deletion failed.");
                                                    }
                                                }}
                                            >
                                                <Trash className="h-3 w-3 mr-1" /> Delete
                                            </Button>
                                        </motion.div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                        )}
                    </main>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
