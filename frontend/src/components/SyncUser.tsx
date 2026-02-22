import { currentUser } from "@clerk/nextjs/server";
import { db } from "@/index";
import { usersTable } from "@/db/schema";
import { eq } from "drizzle-orm";

export default async function SyncUser() {
    const user = await currentUser();

    if (!user) return null;

    try {
        // Check if user already exists
        const existingUser = await db
            .select()
            .from(usersTable)
            .where(eq(usersTable.clerkId, user.id))
            .limit(1);

        if (existingUser.length === 0) {
            // Insert new user
            await db.insert(usersTable).values({
                clerkId: user.id,
                name: `${user.firstName || ""} ${user.lastName || ""}`.trim() || user.username || "Unknown",
                email: user.emailAddresses[0]?.emailAddress || "no-email",
            });
            console.log(`Synced new user: ${user.id}`);
        }
    } catch (error) {
        console.error("Error syncing user to database:", error);
    }

    return null;
}
