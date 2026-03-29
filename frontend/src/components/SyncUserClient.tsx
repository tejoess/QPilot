"use client";
import { useUser } from "@clerk/nextjs";
import { useEffect } from "react";
import { useTemplateStore } from "@/store/templateStore";
import { useOrchestrationStore } from "@/store/orchestrationStore";

export default function SyncUserClient() {
    const { user, isLoaded } = useUser();
    const setUserId = useTemplateStore((state) => state.setUserId);
    // You might want to sync userId with other stores too

    useEffect(() => {
        if (isLoaded && user) {
            setUserId(user.id);
        } else if (isLoaded && !user) {
            setUserId("anonymous");
        }
    }, [user, isLoaded, setUserId]);

    return null;
}
