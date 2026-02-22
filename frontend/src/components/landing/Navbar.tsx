"use client";
import React from "react";
import { FloatingNav } from "@/components/ui/floating-navbar";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { Home, Zap, DollarSign, BookOpen, Mail } from "lucide-react";

export function Navbar() {
    const navItems = [
        {
            name: "Home",
            link: "/",
            icon: <Home className="h-4 w-4" />,
        },
        {
            name: "Features",
            link: "#features",
            icon: <Zap className="h-4 w-4" />,
        },
        {
            name: "Pricing",
            link: "#pricing",
            icon: <DollarSign className="h-4 w-4" />,
        },
        {
            name: "Blog",
            link: "#blog",
            icon: <BookOpen className="h-4 w-4" />,
        },
        {
            name: "Contact",
            link: "#contact",
            icon: <Mail className="h-4 w-4" />,
        },
    ];

    return (
        <div className="relative w-full">
            <FloatingNav navItems={navItems} />
            {/* Absolute Header for initial landing view */}
            <header className="absolute top-0 w-full z-50 px-6 py-8">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-black text-xl italic shadow-lg shadow-primary/20">
                            Q
                        </div>
                        <span className="text-2xl font-black tracking-tighter text-foreground uppercase italic">Pilot</span>
                    </div>

                    <nav className="hidden lg:flex items-center gap-8">
                        <a href="#features" className="text-sm font-medium hover:text-primary transition-colors">Features</a>
                        <a href="#pricing" className="text-sm font-medium hover:text-primary transition-colors">Pricing</a>
                        <a href="#blog" className="text-sm font-medium hover:text-primary transition-colors">Blog</a>
                    </nav>

                    <div className="flex items-center gap-4">
                        <ThemeToggle />
                        <button className="text-sm font-bold text-foreground px-4 py-2 hover:bg-muted rounded-full transition-all">Sign In</button>
                        <button className="bg-primary text-primary-foreground text-sm font-bold px-6 py-2 rounded-full shadow-lg shadow-primary/20 hover:scale-105 transition-all">Get Started</button>
                    </div>
                </div>
            </header>
        </div>
    );
}
