/**
 * ThemePreviewCard component
 *
 * Renders a visual preview swatch for a given theme palette (ocean / royal).
 * Used inside the RadioGroup on the settings page so users can see the colours
 * before committing a choice.
 *
 * Props:
 *  • name          – display name shown in the card
 *  • primaryColor  – hex for the primary (darker) swatch
 *  • accentColor   – hex for the accent (lighter) swatch
 *  • isSelected    – whether this card is the active RadioGroup option
 *  • value         – RadioGroup item value forwarded to Radix
 */

"use client";

import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
import { cn } from "@/lib/utils";

interface ThemePreviewCardProps {
    name: string;
    primaryColor: string;
    accentColor: string;
    isSelected: boolean;
    value: string;
    id: string;
}

export function ThemePreviewCard({
    name,
    primaryColor,
    accentColor,
    isSelected,
    value,
    id,
}: ThemePreviewCardProps) {
    return (
        <RadioGroupPrimitive.Item
            value={value}
            id={id}
            aria-label={`Select ${name} theme`}
            className={cn(
                // Layout
                "relative flex flex-col gap-3 rounded-2xl border-2 p-5 cursor-pointer",
                "transition-all duration-200 ease-out outline-none",
                // Focus-visible ring (accessibility)
                "focus-visible:ring-4 focus-visible:ring-offset-2",
                // Selected vs. idle states
                isSelected
                    ? "border-blue-500 bg-blue-50/60 dark:bg-blue-950/20 shadow-md scale-[1.02]"
                    : "border-border bg-card hover:border-muted-foreground/40 hover:shadow-sm"
            )}
        >
            {/* Colour swatches */}
            <div className="flex gap-2 h-14 overflow-hidden rounded-xl">
                <div
                    className="flex-1 rounded-lg transition-transform duration-200"
                    style={{ background: primaryColor }}
                    aria-hidden="true"
                />
                <div
                    className="flex-1 rounded-lg transition-transform duration-200"
                    style={{ background: accentColor }}
                    aria-hidden="true"
                />
            </div>

            {/* Theme name + hex codes */}
            <div className="space-y-0.5">
                <p className="font-semibold text-sm text-foreground">{name}</p>
                <div className="flex gap-2">
                    <span className="text-xs text-muted-foreground font-mono">
                        {primaryColor}
                    </span>
                    <span className="text-xs text-muted-foreground">·</span>
                    <span className="text-xs text-muted-foreground font-mono">
                        {accentColor}
                    </span>
                </div>
            </div>

            {/* Selected indicator */}
            {isSelected && (
                <span
                    className="absolute top-3 right-3 flex h-5 w-5 items-center justify-center
                     rounded-full bg-blue-500 text-white text-[10px] font-bold
                     shadow-sm ring-2 ring-white dark:ring-background"
                    aria-hidden="true"
                >
                    ✓
                </span>
            )}
        </RadioGroupPrimitive.Item>
    );
}
