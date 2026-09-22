import { createClient } from "@supabase/supabase-js";

/**
 * Server-only Supabase client.
 *
 * The secret key never reaches the browser. Every page in this app is a
 * server component, so reads happen here and the rendered HTML is what
 * the browser receives.
 */
export function db() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SECRET_KEY;

  if (!url || !key) {
    throw new Error(
      "SUPABASE_URL and SUPABASE_SECRET_KEY must be set. Copy .env.example to .env and fill them in."
    );
  }

  return createClient(url, key, {
    auth: { persistSession: false },
    db: { schema: "public" },
  });
}
