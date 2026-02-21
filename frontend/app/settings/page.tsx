"use client";

/**
 * app/settings/page.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Settings page for theme and global configuration.
 * Uses next-themes for robust theme switching across Light, Dark, Ocean, and Royal.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { QPilotSidebar } from "@/components/qpilot/QPilotSidebar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { Palette, Check, Sun, Moon, Droplets, Crown } from "lucide-react";

const THEMES = [
    {
        id: "light",
        name: "Classic Light",
        icon: Sun,
        colors: "bg-white border-slate-200 text-slate-800",
        desc: "Standard institutional high-contrast view."
    },
    {
        id: "dark",
        name: "Modern Dark",
        icon: Moon,
        colors: "bg-slate-900 border-slate-800 text-white",
        desc: "Reduced eye strain for low-light environments."
    },
    {
        id: "ocean",
        name: "Ocean Breeze",
        icon: Droplets,
        colors: "bg-[#2872A1] text-white",
        desc: "Professional deep blue with soft sky accents."
    },
    {
        id: "royal",
        name: "Royal Ivory",
        icon: Crown,
        colors: "bg-[#5F4A8B] text-white",
        desc: "Elegant purple paired with vintage ivory tones."
    },
];

export default function SettingsPage() {
    const { theme, setTheme } = useTheme();

    return (
        <SidebarProvider>
            <div className="flex h-screen w-full bg-background overflow-hidden">
                <QPilotSidebar />

                <SidebarInset className="flex-1 overflow-auto bg-muted/20">
                    <main className="max-w-4xl mx-auto px-6 py-10 space-y-10">
                        <div className="space-y-1">
                            <h1 className="text-3xl font-bold tracking-tight text-foreground">Settings</h1>
                            <p className="text-sm text-muted-foreground">Manage your interface preferences and theme.</p>
                        </div>

                        <Card className="border-border/60 shadow-sm">
                            <CardHeader className="pb-4">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                                        <Palette className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <CardTitle className="text-base font-bold">Theme & Appearance</CardTitle>
                                        <CardDescription className="text-xs">Choose a theme that fits your institutional style.</CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {THEMES.map((t) => {
                                    const isActive = theme === t.id;
                                    const Icon = t.icon;

                                    return (
                                        <button
                                            key={t.id}
                                            onClick={() => setTheme(t.id)}
                                            className={cn(
                                                "group relative flex items-start gap-4 p-4 rounded-xl border-2 text-left transition-all duration-300",
                                                isActive
                                                    ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                                    : "border-border/40 hover:border-primary/40 hover:bg-muted/50"
                                            )}
                                        >
                                            <div className={cn(
                                                "h-10 w-10 rounded-lg flex items-center justify-center transition-transform group-hover:scale-110",
                                                t.colors
                                            )}>
                                                <Icon className="h-5 w-5" />
                                            </div>

                                            <div className="flex-1 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm font-bold">{t.name}</span>
                                                    {isActive && (
                                                        <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center animate-in zoom-in-50">
                                                            <Check className="h-3 w-3 text-primary-foreground" />
                                                        </div>
                                                    )}
                                                </div>
                                                <p className="text-[11px] text-muted-foreground leading-snug">{t.desc}</p>
                                            </div>
                                        </button>
                                    );
                                })}
                            </CardContent>
                        </Card>

                        <div className="py-10 text-center opacity-30">
                            <span className="text-[10px] uppercase font-bold tracking-[0.3em]">Institutional Configuration Panel</span>
                        </div>
                    </main>
                </SidebarInset>
            </div>
        </SidebarProvider>
    );
}
