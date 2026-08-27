// Thin JS service. Owns things that are simpler in Node than Python:
// - Stripe/subscription webhook receivers (institutional + individual)
// - Any future real-time chat gateway (websocket fanout) if chat outgrows
//   simple request/response through FastAPI
//
// Deliberately does NOT touch Qiskit or grading logic — that boundary is
// the whole point of ADR-001.
import express from "express";
import { createClient } from "@supabase/supabase-js";

const app = express();
app.use(express.json());

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// Example: subscription-provider webhook -> updates `subscriptions` table.
// Swap the payload shape for whichever billing provider is wired up.
app.post("/webhooks/subscription", async (req, res) => {
  const { subscription_id, status, plan_scope, owner_id, plan, renews_at } = req.body;

  const { error } = await supabase.from("subscriptions").upsert({
    id: subscription_id,
    status,
    plan_scope,
    plan,
    renews_at,
    ...(plan_scope === "individual" ? { user_id: owner_id } : { institution_id: owner_id }),
  });

  if (error) return res.status(500).json({ error: error.message });
  res.json({ ok: true });
});

app.get("/health", (_req, res) => res.json({ status: "ok" }));

const port = process.env.PORT || 8787;
app.listen(port, () => console.log(`node-glue listening on ${port}`));
