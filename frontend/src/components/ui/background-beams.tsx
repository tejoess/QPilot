"use client";
import React, { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

export const BackgroundBeams = ({ className }: { className?: string }) => {
    const beamsRef = useRef<HTMLDivElement>(null);

    return (
        <div
            ref={beamsRef}
            className={cn(
                "absolute inset-0 z-0 pointer-events-none overflow-hidden",
                className
            )}
        >
            <svg
                className="absolute h-full w-full"
                xmlns="http://www.w3.org/2000/svg"
            >
                <defs>
                    <linearGradient id="beam-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="var(--primary)" stopOpacity="0" />
                        <stop offset="50%" stopColor="var(--primary)" stopOpacity="0.1" />
                        <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
                    </linearGradient>
                </defs>
                <rect width="100%" height="100%" fill="url(#beam-gradient)" />
            </svg>
            {/* Simulation of beams */}
            {[...Array(5)].map((_, i) => (
                <div
                    key={i}
                    className="absolute h-[1px] w-full bg-gradient-to-r from-transparent via-primary/20 to-transparent animate-beam"
                    style={{
                        top: `${20 * i + Math.random() * 10}%`,
                        animationDelay: `${i * 2}s`,
                        animationDuration: `${10 + Math.random() * 5}s`,
                    }}
                />
            ))}
        </div>
    );
};
