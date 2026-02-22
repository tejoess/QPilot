"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { motion } from "framer-motion";

export function ThemeToggle() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = React.useState(false);

    React.useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) return null;

    const isDark = theme === "dark";

    return (
        <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="relative flex h-8 w-14 items-center rounded-full bg-zinc-200 p-1 transition-colors focus:outline-none dark:bg-zinc-800"
            aria-label="Toggle theme"
        >
            <motion.div
                className="flex h-6 w-6 items-center justify-center rounded-full bg-white shadow-sm dark:bg-zinc-950"
                animate={{ x: isDark ? 24 : 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
            >
                {isDark ? (
                    <Moon className="h-4 w-4 text-purple-400" />
                ) : (
                    <Sun className="h-4 w-4 text-amber-500" />
                )}
            </motion.div>
        </button>
    );
}
