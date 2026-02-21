"use client";

/**
 * components/qpilot/QPilotSidebar.tsx
 */

import { LayoutDashboard, Rocket, History, Settings } from "lucide-react";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
    { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { title: "QPilot", href: "/qpilot", icon: Rocket },
    { title: "History", href: "/history", icon: History },
    { title: "Settings", href: "/settings", icon: Settings },
];

export function QPilotSidebar() {
    const pathname = usePathname();

    return (
        <Sidebar className="border-r border-border/50 bg-card/10" collapsible="none">
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel className="px-4 py-6 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50">
                        Control Center
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu className="px-3 space-y-1">
                            {NAV_ITEMS.map((item) => {
                                const isActive = item.title === "QPilot"
                                    ? pathname?.startsWith("/qpilot")
                                    : pathname === item.href;

                                return (
                                    <SidebarMenuItem key={item.title}>
                                        <SidebarMenuButton asChild isActive={isActive} className={cn(
                                            "transition-all duration-200 h-10 px-3 rounded-xl",
                                            isActive
                                                ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                                : "text-muted-foreground hover:bg-muted"
                                        )}>
                                            <Link href={item.href} className="flex items-center gap-3">
                                                <item.icon className={cn("h-4 w-4", isActive ? "text-primary-foreground" : "text-muted-foreground/70")} />
                                                <span className="text-[13px] font-bold">{item.title}</span>
                                                {isActive && <div className="ml-auto w-1 h-3 bg-primary-foreground/40 rounded-full" />}
                                            </Link>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
        </Sidebar>
    );
}
