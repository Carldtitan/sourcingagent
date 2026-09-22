import type { Metadata } from "next";
import "./globals.css";
import { db } from "@/lib/db";
import { Rail } from "@/components/Rail";

export const metadata: Metadata = {
  title: "Aonic Sourcing",
  description:
    "An agent-driven sourcing engine that turns one ingredient brief into three to five validated, comparable supplier offers.",
};

export const dynamic = "force-dynamic";

async function pendingCount(): Promise<number> {
  try {
    const { count } = await db()
      .from("approvals")
      .select("id", { count: "exact", head: true })
      .eq("status", "open");
    return count ?? 0;
  } catch {
    return 0;
  }
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const waiting = await pendingCount();

  return (
    <html lang="en">
      <body>
        <div className="chassis">
          <Rail waiting={waiting} />
          <main className="stage">{children}</main>
        </div>
      </body>
    </html>
  );
}
