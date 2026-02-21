/**
 * components/dashboard/QuickActionCard.tsx
 */

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface QuickActionCardProps {
    title: string;
    description: string;
    icon: LucideIcon;
    buttonText: string;
    onClick: () => void;
    className?: string;
    variant?: "primary" | "default";
}

export function QuickActionCard({
    title,
    description,
    icon: Icon,
    buttonText,
    onClick,
    className,
    variant = "default"
}: QuickActionCardProps) {
    return (
        <Card className={cn(
            "group relative overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1 border-border/50",
            variant === "primary" ? "bg-primary/[0.02] border-primary/20" : "bg-card",
            className
        )}>
            <CardContent className="p-6 space-y-4">
                <div className={cn(
                    "p-3 rounded-xl w-fit transition-colors",
                    variant === "primary" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary"
                )}>
                    <Icon className="h-6 w-6" />
                </div>

                <div className="space-y-1.5">
                    <h3 className="font-bold text-lg tracking-tight text-foreground">{title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
                </div>

                <Button
                    onClick={onClick}
                    className={cn(
                        "w-full font-bold transition-all",
                        variant === "primary" ? "" : "bg-muted text-muted-foreground hover:bg-primary hover:text-primary-foreground"
                    )}
                >
                    {buttonText}
                </Button>
            </CardContent>
        </Card>
    );
}
