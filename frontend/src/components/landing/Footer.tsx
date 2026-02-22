"use client";
import React from "react";
import {
    Twitter,
    Github,
    Linkedin,
    ChevronRight
} from "lucide-react";
import { motion } from "framer-motion";

export function Footer() {
    return (
        <footer className="bg-background border-t border-border pt-24 pb-12 overflow-hidden">
            <div className="container mx-auto px-6">
                {/* Final CTA Section */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    className="relative bg-zinc-950 rounded-[40px] p-12 md:p-24 overflow-hidden mb-24"
                >
                    {/* Animated Glow Beam */}
                    <div className="absolute -top-[500px] left-1/2 -rotate-45 w-[100px] h-[1000px] bg-primary/20 blur-[100px] animate-pulse" />

                    <div className="relative z-10 flex flex-col items-center text-center">
                        <h2 className="text-4xl md:text-7xl font-black italic text-white mb-8 max-w-4xl leading-[1.1]">
                            Ready to Transform <br /> Exam Creation?
                        </h2>
                        <div className="flex flex-wrap justify-center gap-6 mt-6">
                            <button className="bg-white text-black px-10 py-5 rounded-3xl font-black uppercase tracking-widest text-sm hover:scale-105 transition-all">
                                Get Started Now
                            </button>
                            <button className="bg-white/10 backdrop-blur-md text-white border border-white/20 px-10 py-5 rounded-3xl font-black uppercase tracking-widest text-sm hover:bg-white/20 transition-all">
                                Contact Sales
                            </button>
                        </div>
                    </div>
                </motion.div>

                {/* Links Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-12 mb-20">
                    <div className="col-span-2">
                        <div className="flex items-center gap-2 mb-8">
                            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-white font-black italic shadow-lg">Q</div>
                            <span className="text-2xl font-black italic tracking-tighter uppercase">Pilot</span>
                        </div>
                        <p className="text-muted-foreground max-w-xs mb-8">
                            Revolutionising educational assessments with powerful multi-agent AI orchestration.
                        </p>
                        <div className="flex gap-4">
                            <Twitter className="w-5 h-5 text-muted-foreground hover:text-primary cursor-pointer" />
                            <Github className="w-5 h-5 text-muted-foreground hover:text-primary cursor-pointer" />
                            <Linkedin className="w-5 h-5 text-muted-foreground hover:text-primary cursor-pointer" />
                        </div>
                    </div>

                    <div>
                        <h4 className="font-black uppercase tracking-widest text-xs mb-8">Product</h4>
                        <ul className="space-y-4">
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Features</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Integrations</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Enterprise</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Changelog</a></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-black uppercase tracking-widest text-xs mb-8">Resources</h4>
                        <ul className="space-y-4">
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Documentation</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Help Center</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Community</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Knowledge Base</a></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-black uppercase tracking-widest text-xs mb-8">Company</h4>
                        <ul className="space-y-4">
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">About Us</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Privacy Policy</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Terms of Service</a></li>
                            <li><a href="#" className="text-muted-foreground hover:text-primary transition-colors">Careers</a></li>
                        </ul>
                    </div>
                </div>

                {/* Giant Logo Background */}
                <div className="border-t border-border pt-12 flex flex-col md:flex-row justify-between items-center opacity-40">
                    <p className="text-xs font-medium text-muted-foreground">
                        &copy; 2026 QPilot Systems. All rights reserved.
                    </p>
                    <p className="text-[10px] font-black uppercase tracking-[0.5em]">INVESTOR READY // SEED-2026</p>
                </div>

                <div className="relative pointer-events-none mt-20 select-none">
                    <h1 className="text-[15vw] lg:text-[200px] font-black italic tracking-tighter leading-none opacity-5 dark:opacity-[0.03] text-center w-full">
                        RELEARN
                    </h1>
                </div>
            </div>
        </footer>
    );
}
