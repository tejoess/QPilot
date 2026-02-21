"use client";

/**
 * components/builder/GenerationSettings.tsx
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Settings2, Zap } from "lucide-react";
import type { GenerationSettings as SettingsType } from "@/types/api";

interface GenerationSettingsProps {
    settings: SettingsType;
    onChange: (updates: Partial<SettingsType>) => void;
    isLoading: boolean;
}

export function GenerationSettings({ settings, onChange, isLoading }: GenerationSettingsProps) {
    if (isLoading) {
        return (
            <Card className="shadow-sm border-border/60">
                <CardContent className="pt-6 space-y-4">
                    <div className="h-4 w-1/3 bg-muted animate-pulse rounded" />
                    <div className="h-8 w-full bg-muted animate-pulse rounded" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="shadow-sm border-border/60">
            <CardHeader className="pb-4">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <Settings2 className="h-4 w-4 text-muted-foreground" />
                    Generation Settings
                </CardTitle>
                <CardDescription>Advanced controls for paper generation.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label htmlFor="ans-key">Include Answer Key</Label>
                            <p className="text-xs text-muted-foreground">Attach solutions at the end.</p>
                        </div>
                        <Switch
                            id="ans-key"
                            checked={settings.includeAnswerKey}
                            onCheckedChange={(v) => onChange({ includeAnswerKey: v })}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label htmlFor="shuffle">Shuffle Questions</Label>
                            <p className="text-xs text-muted-foreground">Randomize question order.</p>
                        </div>
                        <Switch
                            id="shuffle"
                            checked={settings.shuffleQuestions}
                            onCheckedChange={(v) => onChange({ shuffleQuestions: v })}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label htmlFor="neg-mark">Negative Marking</Label>
                            <p className="text-xs text-muted-foreground">Enable penalty for wrong answers.</p>
                        </div>
                        <Switch
                            id="neg-mark"
                            checked={settings.negativeMarking}
                            onCheckedChange={(v) => onChange({ negativeMarking: v })}
                        />
                    </div>
                </div>

                <div className="space-y-4 pt-4 border-t">
                    <div className="flex items-center gap-2">
                        <Zap className="h-4 w-4 text-amber-500" />
                        <Label className="text-sm font-semibold">Difficulty Distribution</Label>
                    </div>

                    <div className="space-y-3">
                        <div className="flex justify-between text-xs font-mono">
                            <span className="text-green-600 dark:text-green-400">Easy: {settings.difficultyDistribution[0]}%</span>
                            <span className="text-amber-600 dark:text-amber-400">Med: {settings.difficultyDistribution[1]}%</span>
                            <span className="text-red-600 dark:text-red-400">Hard: {settings.difficultyDistribution[2]}%</span>
                        </div>

                        {/* Simple slider to showcase the interaction. True difficulty dist slider usually has multiple handles. */}
                        <Slider
                            defaultValue={[settings.difficultyDistribution[0]]}
                            max={100}
                            step={5}
                            onValueChange={(v) => {
                                // Mock logic: shift Med based on Easy change, keeping Hard fixed for simplicity in demo
                                const newEasy = v[0];
                                const remainder = 100 - newEasy - 30; // 30 is fixed for Hard in this simple demo
                                onChange({
                                    difficultyDistribution: [newEasy, Math.max(0, remainder), 30]
                                });
                            }}
                        />
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
