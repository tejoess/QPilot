"use client";
import React from "react";
import { motion } from "framer-motion";

const steps = [
    {
        title: "Create Exam Metadata",
        description: "Input subject, grade, and duration. Our system initializes the session for your specific needs.",
        number: "01",
    },
    {
        title: "AI Builds Knowledge Graph",
        description: "The Syllabus Agent extracts core concepts and creates a semantic map of dependencies.",
        number: "02",
    },
    {
        title: "Agents Collaborate",
        description: "Multi-agent systems work on bloom taxonomy, paper patterns, and content selection simultaneously.",
        number: "03",
    },
    {
        title: "Paper Generated",
        description: "Review your structured PDF with MCQ, Short, and Long answer sections pre-formatted.",
        number: "04",
    },
];

export function HowItWorks() {
    return (
        <section className="py-24 bg-zinc-950 text-white overflow-hidden relative">
            {/* Background radial glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />

            <div className="container mx-auto px-6 relative z-10">
                <div className="flex flex-col lg:flex-row gap-20 items-start">
                    <div className="lg:w-1/3">
                        <h2 className="text-sm font-bold text-accent uppercase tracking-[0.3em] mb-4">The Workflow</h2>
                        <h3 className="text-4xl md:text-6xl font-black mb-8 leading-tight">From Logic to Layout.</h3>
                        <p className="text-lg text-neutral-400 mb-10">
                            We've simplified the complex process of exam design into four intelligent phases.
                        </p>
                        <div className="h-1 lg:w-32 bg-gradient-to-r from-primary to-accent rounded-full" />
                    </div>

                    <div className="lg:w-2/3 space-y-12">
                        {steps.map((step, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, x: 50 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.2 }}
                                viewport={{ once: true }}
                                className="flex gap-8 group"
                            >
                                <div className="flex flex-col items-center">
                                    <div className="w-16 h-16 rounded-full border border-neutral-800 flex items-center justify-center text-2xl font-black italic text-neutral-600 group-hover:border-primary group-hover:text-primary transition-all duration-500 shadow-2xl group-hover:shadow-primary/20">
                                        {step.number}
                                    </div>
                                    {index !== steps.length - 1 && (
                                        <div className="w-px h-full bg-neutral-800 my-4" />
                                    )}
                                </div>
                                <div className="pt-2">
                                    <h4 className="text-2xl font-bold mb-4 group-hover:translate-x-2 transition-transform duration-500">{step.title}</h4>
                                    <p className="text-neutral-400 max-w-lg leading-relaxed">{step.description}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
}
