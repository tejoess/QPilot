"use client";
import React, { useState } from "react";
import { Check } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const plans = [
    {
        name: "Starter",
        price: "0",
        description: "Perfect for exploring the power of AI generation.",
        features: [
            "5 Papers per month",
            "Syllabus extraction",
            "Standard PDF templates",
            "Community support",
        ],
        cta: "Join Now",
        featured: false,
    },
    {
        name: "Pro",
        price: "49",
        description: "For professional educators and high-volume departments.",
        features: [
            "Unlimited papers",
            "Full Multi-Agent suite",
            "Custom templates",
            "Priority AI queue",
            "Analytics & Insights",
        ],
        cta: "Go Pro",
        featured: true,
    },
    {
        name: "Enterprise",
        price: "Custom",
        description: "Scalable solutions for large educational institutions.",
        features: [
            "API Access",
            "SSO integration",
            "Custom knowledge base",
            "Dedicated account manager",
            "On-prem deployment",
        ],
        cta: "Contact Sales",
        featured: false,
    },
];

export function Pricing() {
    const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

    return (
        <section id="pricing" className="py-24 bg-background">
            <div className="container mx-auto px-6">
                <div className="text-center max-w-2xl mx-auto mb-16">
                    <h2 className="text-sm font-bold text-primary uppercase tracking-[0.3em] mb-4">Pricing Plans</h2>
                    <h3 className="text-4xl md:text-5xl font-black mb-10">Scale Your Intelligence.</h3>

                    <div className="inline-flex items-center p-1 bg-muted rounded-full mb-8">
                        <button
                            onClick={() => setBilling("monthly")}
                            className={cn(
                                "px-6 py-2 rounded-full text-sm font-bold transition-all",
                                billing === "monthly" ? "bg-white dark:bg-zinc-800 shadow-md text-foreground" : "text-muted-foreground"
                            )}
                        >
                            Monthly
                        </button>
                        <button
                            onClick={() => setBilling("yearly")}
                            className={cn(
                                "px-6 py-2 rounded-full text-sm font-bold transition-all",
                                billing === "yearly" ? "bg-white dark:bg-zinc-800 shadow-md text-foreground" : "text-muted-foreground"
                            )}
                        >
                            Yearly
                        </button>
                    </div>
                    <p className="text-xs font-bold text-accent uppercase tracking-widest">Save 20% on yearly billing</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
                    {plans.map((plan, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            viewport={{ once: true }}
                            className={cn(
                                "relative group p-10 rounded-3xl flex flex-col items-start transition-all duration-500",
                                plan.featured
                                    ? "bg-zinc-950 text-white scale-105 shadow-2xl z-10"
                                    : "bg-card border border-border hover:border-primary/30"
                            )}
                        >
                            {plan.featured && (
                                <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-accent/20 rounded-3xl pointer-events-none" />
                            )}

                            <div className="relative z-10 w-full mb-8">
                                <span className={cn(
                                    "px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-muted mb-4 inline-block",
                                    plan.featured ? "bg-primary text-white" : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
                                )}>
                                    {plan.name}
                                </span>
                                <div className="flex items-baseline gap-1 mb-2">
                                    <span className="text-5xl font-black italic">
                                        {plan.price !== "Custom" ? `$${plan.price}` : plan.price}
                                    </span>
                                    {plan.price !== "Custom" && (
                                        <span className="text-muted-foreground font-bold">/mo</span>
                                    )}
                                </div>
                                <p className={cn(
                                    "text-sm",
                                    plan.featured ? "text-neutral-400 font-medium" : "text-muted-foreground font-medium"
                                )}>
                                    {plan.description}
                                </p>
                            </div>

                            <div className="relative z-10 flex-1 w-full space-y-4 mb-10">
                                {plan.features.map((feature, idx) => (
                                    <div key={idx} className="flex items-center gap-3">
                                        <div className={cn(
                                            "w-5 h-5 rounded-full flex items-center justify-center",
                                            plan.featured ? "bg-primary/20 text-primary" : "bg-primary/10 text-primary"
                                        )}>
                                            <Check className="w-3 h-3 stroke-[3]" />
                                        </div>
                                        <span className={cn(
                                            "text-sm font-medium",
                                            plan.featured ? "text-neutral-300" : "text-foreground"
                                        )}>{feature}</span>
                                    </div>
                                ))}
                            </div>

                            <button className={cn(
                                "relative z-10 w-full py-4 rounded-2xl font-black text-sm uppercase tracking-widest transition-all",
                                plan.featured
                                    ? "bg-white text-black hover:scale-105"
                                    : "bg-primary text-white hover:bg-primary/90"
                            )}>
                                {plan.cta}
                            </button>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
