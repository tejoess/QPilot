/**
 * components/dashboard/SystemStatusPanel.tsx
 */

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SystemStats } from "@/store/dashboardStore";
import { TrendingUp, Clock, Activity, Database } from "lucide-react";

interface SystemStatusPanelProps {
    stats: SystemStats | null;
    isLoading: boolean;
}

export function SystemStatusPanel({ stats, isLoading }: SystemStatusPanelProps) {
    if (isLoading || !stats) {
        return (
            <Card className="border-border/50 shadow-sm">
                <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                        {[1, 2, 3, 4].map((i) => (
                            <div key={i} className="space-y-3">
                                <Skeleton className="h-4 w-24" />
                                <Skeleton className="h-8 w-32" />
                                <Skeleton className="h-4 w-40" />
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    const metrics = [
        {
            label: "Total Papers Generated",
            value: stats.totalPapers.toLocaleString(),
            description: "Across all subjects and grades",
            trend: stats.trends.totalPapers,
            icon: Activity
        },
        {
            label: "Last Generation Time",
            value: stats.lastGenTime,
            description: "Time since last synthesis",
            icon: Clock
        },
        {
            label: "Average Generation Time",
            value: stats.avgGenTime,
            description: "Based on last 50 papers",
            icon: TrendingUp
        },
        {
            label: "PYQ Database Size",
            value: stats.pyqDbSize,
            description: "Verified unique questions",
            icon: Database
        }
    ];

    return (
        <Card className="border-border/50 shadow-sm bg-card/50 overflow-hidden">
            <CardContent className="p-0">
                <div className="grid grid-cols-1 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-border/20">
                    {metrics.map((m, i) => (
                        <div key={i} className="p-6 space-y-3 transition-colors hover:bg-muted/30">
                            <div className="flex items-center justify-between">
                                <span className="text-[11px] font-black uppercase tracking-widest text-muted-foreground/70">
                                    {m.label}
                                </span>
                                <m.icon className="h-3.5 w-3.5 text-primary/40" />
                            </div>

                            <div className="flex items-baseline gap-2">
                                <h4 className="text-3xl font-black tracking-tighter text-foreground">
                                    {m.value}
                                </h4>
                                {m.trend && (
                                    <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-100/50 hover:bg-emerald-500/10 text-[10px] px-1.5 h-5 font-bold">
                                        {m.trend}
                                    </Badge>
                                )}
                            </div>

                            <p className="text-[11px] font-medium text-muted-foreground/60 leading-tight">
                                {m.description}
                            </p>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
