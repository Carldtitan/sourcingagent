import { db } from "@/lib/db";

/** Serves a certificate PDF back out of the database. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { data, error } = await db()
    .from("files")
    .select("name, content_type, data")
    .eq("id", id)
    .single();

  if (error || !data) {
    return new Response("Not found", { status: 404 });
  }

  // Postgres returns bytea as a hex string prefixed with \x
  const hex = String(data.data).replace(/^\\x/, "");
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i += 1) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }

  return new Response(bytes, {
    headers: {
      "Content-Type": data.content_type ?? "application/pdf",
      "Content-Disposition": `inline; filename="${data.name}"`,
      "Cache-Control": "private, max-age=600",
    },
  });
}
