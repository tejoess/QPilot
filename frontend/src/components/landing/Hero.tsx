"use client";
import React from "react";
import Image from "next/image";
import { Spotlight } from "@/components/ui/spotlight";
import { BackgroundBeams } from "@/components/ui/background-beams";
import { HoverBorderGradient } from "@/components/ui/hover-border-gradient";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

export function Hero() {
    return (
        <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-background pt-20">
            <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="var(--primary)" />
            <BackgroundBeams />

            <div className="container mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center z-10">
                <motion.div
                    initial={{ opacity: 0, x: -50 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8 }}
                    className="flex flex-col gap-6"
                >
                    <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-foreground leading-[1.1]">
                        Build Smarter Exams with <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent italic">AI Intelligence</span>
                    </h1>
                    <p className="text-lg md:text-xl text-muted-foreground max-w-lg">
                        Experience the future of curriculum design. QPilot uses multi-agent orchestration to craft high-integrity exam papers in seconds.
                    </p>

                    <div className="flex flex-wrap gap-4 mt-4">
                        <Link href="/qpilot">
                            <HoverBorderGradient className="bg-primary text-primary-foreground font-bold px-8 py-4 text-lg">
                                Start Generating
                            </HoverBorderGradient>
                        </Link>
                        <button className="px-8 py-4 rounded-full border border-border bg-transparent text-foreground font-medium hover:bg-muted transition-colors text-lg">
                            Watch Demo
                        </button>
                    </div>

                </motion.div>

                <motion.div
                    initial={{ opacity: 0, scale: 0.8, rotate: 5 }}
                    animate={{ opacity: 1, scale: 1, rotate: 0 }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="relative flex justify-center lg:justify-end"
                >
                    <div className="relative w-full max-w-[600px] aspect-square">
                        {/* Orbit Lines Animation */}
                        <div className="absolute inset-0 border border-primary/20 rounded-full animate-orbit-slow" />
                        <div className="absolute inset-10 border border-accent/10 rounded-full animate-orbit-fast" />

                        {/* Main Image */}
                        <Image
                            src="/1.png"
                            alt="QPilot AI Visualization"
                            width={600}
                            height={600}
                            className="object-contain drop-shadow-[0_0_50px_var(--glow-primary)] z-20"
                            priority
                        />

                        {/* Floating Cards */}
                        <motion.div
                            animate={{ y: [0, -20, 0] }}
                            transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
                            className="absolute top-20 -left-10 bg-card/80 backdrop-blur-md p-4 rounded-2xl border border-border shadow-2xl z-30"
                        >
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-[10px] font-bold">SAI</div>
                                <div className="text-xs font-bold">Syllabus AI Output</div>
                            </div>
                        </motion.div>

                        <motion.div
                            animate={{ y: [0, 20, 0] }}
                            transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
                            className="absolute bottom-20 -right-5 bg-card/80 backdrop-blur-md p-4 rounded-2xl border border-border shadow-2xl z-30"
                        >
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-white text-[10px] font-bold">PDF</div>
                                <div className="text-xs font-bold">Instant PDF Ready</div>
                            </div>
                        </motion.div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
