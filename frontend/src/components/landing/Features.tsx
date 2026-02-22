"use client";
import React from "react";
import { cn } from "@/lib/utils";
import {
    Network,
    BrainCircuit,
    Timer,
    Settings2,
    Layout,
    BarChart3
} from "lucide-react";
import { motion } from "framer-motion";

const features = [
    {
        title: "Knowledge Graph Engine",
        description: "Our AI maps curriculum nodes into a semantic graph, ensuring 100% syllabus coverage and logical flow.",
        icon: <Network className="w-6 h-6 text-primary" />,
    },
    {
        title: "Bloom Distribution AI",
        description: "Automatically balance cognitive levels from Recall to Create using intelligent weightage algorithms.",
        icon: <BrainCircuit className="w-6 h-6 text-accent" />,
    },
    {
        title: "Real-time Generation",
        description: "Watch as multiple agents collaborate live to prepare sections, MCQ options, and answer keys.",
        icon: <Timer className="w-6 h-6 text-blue-500" />,
    },
    {
        title: "Multi-Agent Orchestration",
        description: "Separate agents for Syllabus, PYQ, and Design work in parallel for unparalleled speed and depth.",
        icon: <Settings2 className="w-6 h-6 text-green-500" />,
    },
    {
        title: "Exam Pattern Builder",
        description: "Drag-and-drop structural constraints to match any board pattern: CBSE, ICSE, or University standards.",
        icon: <Layout className="w-6 h-6 text-amber-500" />,
    },
    {
        title: "AI Analytics",
        description: "Get predictive difficulty scores and content density reports before you finalise your paper.",
        icon: <BarChart3 className="w-6 h-6 text-rose-500" />,
    },
];

export function Features() {
    return (
        <section id="features" className="py-24 bg-background">
            <div className="container mx-auto px-6">
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <h2 className="text-sm font-bold text-primary uppercase tracking-[0.3em] mb-4">Core Intelligence</h2>
                    <h3 className="text-4xl md:text-5xl font-black mb-6">Why QPilot is Different</h3>
                    <p className="text-lg text-muted-foreground">
                        We don't just generate text. We orchestrate a digital brain that understands your curriculum as deeply as you do.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {features.map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            viewport={{ once: true }}
                            className="group relative p-8 rounded-3xl bg-card border border-border hover:border-primary/50 transition-all duration-500 overflow-hidden"
                        >
                            {/* Glow effect */}
                            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-accent/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <div className="absolute -inset-2 bg-primary blur-3xl opacity-0 group-hover:opacity-[0.03] transition-opacity duration-500" />

                            <div className="relative z-10">
                                <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500">
                                    {feature.icon}
                                </div>
                                <h4 className="text-xl font-bold mb-4 group-hover:text-primary transition-colors">{feature.title}</h4>
                                <p className="text-muted-foreground line-clamp-3 group-hover:text-foreground transition-colors">
                                    {feature.description}
                                </p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
