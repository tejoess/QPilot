"use client";

/**
 * components/qpilot/QPilotSidebar.tsx
 */

import { LayoutDashboard, Rocket, History, Settings, ChevronLeft, ChevronRight } from "lucide-react";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarHeader,
    useSidebar
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
    { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { title: "QPilot", href: "/qpilot", icon: Rocket },
    { title: "History", href: "/history", icon: History },
    { title: "Settings", href: "/settings", icon: Settings },
];

export function QPilotSidebar() {
    const pathname = usePathname();
    const { state, toggleSidebar, isMobile } = useSidebar();
    const isCollapsed = state === "collapsed";

    return (
        <Sidebar
            className="border-r border-border/50 bg-card/10 transition-all duration-300 ease-in-out"
            collapsible="icon"
        >
            <SidebarHeader className="h-14 flex items-center justify-between px-3 border-b border-border/30">
                {!isCollapsed && (
                    <span className="text-[11px] font-black uppercase tracking-[0.2em] text-primary pl-1 animate-in fade-in duration-300">
                        QPilot System
                    </span>
                )}
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleSidebar}
                    className={cn(
                        "h-8 w-8 text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors",
                        isCollapsed && "mx-auto"
                    )}
                >
                    {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                </Button>
            </SidebarHeader>

            <SidebarContent>
                <SidebarGroup>
                    {!isCollapsed && (
                        <SidebarGroupLabel className="px-4 py-4 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/50 animate-in fade-in duration-500">
                            Control Center
                        </SidebarGroupLabel>
                    )}
                    <SidebarGroupContent>
                        <SidebarMenu className={cn("px-3 space-y-2", isCollapsed && "px-2")}>
                            {NAV_ITEMS.map((item) => {
                                const isActive = item.title === "QPilot"
                                    ? pathname?.startsWith("/qpilot")
                                    : pathname === item.href;

                                return (
                                    <SidebarMenuItem key={item.title}>
                                        <SidebarMenuButton
                                            asChild
                                            isActive={isActive}
                                            tooltip={item.title}
                                            className={cn(
                                                "transition-all duration-300 h-10 rounded-xl group relative",
                                                isActive
                                                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20"
                                                    : "text-muted-foreground hover:bg-muted hover:text-primary",
                                                isCollapsed ? "justify-center px-0" : "px-3"
                                            )}
                                        >
                                            <Link href={item.href} className="flex items-center gap-3">
                                                <item.icon className={cn(
                                                    "h-4 w-4 transition-transform group-hover:scale-110",
                                                    isActive ? "text-primary-foreground" : "text-muted-foreground/70 group-hover:text-primary"
                                                )} />
                                                {!isCollapsed && (
                                                    <span className="text-[13px] font-bold">{item.title}</span>
                                                )}
                                                {isActive && !isCollapsed && (
                                                    <div className="ml-auto w-1 h-3 bg-primary-foreground/40 rounded-full" />
                                                )}
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
