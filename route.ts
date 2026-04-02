import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const API_SECRET = process.env.INGEST_API_SECRET!;

type Category = "fitness" | "body" | "admin";

interface IngestPayload {
  category: Category;
  data: Record<string, unknown>;
  user_id: string;
}

const TABLE_MAP: Record<Category, string> = {
  fitness: "fitness_logs",
  body: "body_stats",
  admin: "admin_events",
};

export async function POST(req: NextRequest) {
  // Auth guard
  const secret = req.headers.get("x-api-secret");
  if (secret !== API_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: IngestPayload;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { category, data, user_id } = body;

  if (!category || !data || !user_id) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }

  const table = TABLE_MAP[category];
  if (!table) {
    return NextResponse.json({ error: `Unknown category: ${category}` }, { status: 400 });
  }

  const { error } = await supabase
    .from(table)
    .insert({ ...data, user_id, created_at: new Date().toISOString() });

  if (error) {
    console.error("[ingest] Supabase error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true, table }, { status: 201 });
}
