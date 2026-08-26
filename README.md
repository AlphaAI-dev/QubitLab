Quantum Algorithm Learning Platform  Architecture

Monorepo. Three deployables + one shared data layer:

```
frontend/          Vite + React + TS + Tailwind (shadcn/ui components)
backend-fastapi/    Python — Qiskit grading, chatbot RAG, circuit validation
backend-node/       Node — thin auth glue, chat gateway, webhook receivers
supabase/           schema.sql — Postgres schema + RLS policies
```

## ADR-001: Why split FastAPI and Node instead of one runtime
Qiskit's `AerSimulator` is Python-only and CPU-bound per request — running it
inside a Node process means either a subprocess-per-request (fragile, slow
cold start) or a Python microservice (clean boundary). We chose the
microservice. Node owns nothing Qiskit needs to touch: it's the auth-adjacent
glue and the chat gateway that proxies to whichever LLM provider is
configured. This keeps the Python service stateless and horizontally
scalable independent of the chat traffic pattern, which has a different
load shape (bursty, long-lived streaming connections) than grading (short,
CPU-heavy, spiky at assignment deadlines).

Deferred cost: two deploy pipelines, two sets of env vars, one more
network hop for any request that touches both auth and grading. Accepted
because the alternative (Qiskit-in-Node via subprocess) is worse at scale.

## ADR-002: Why Supabase over custom Postgres + Auth
Institutional multi-seat accounts need row-level isolation from day one —
a college admin should never see another college's student progress, and a
student should never see another student's submitted predictions. Supabase
gives us Postgres + Auth + RLS + Storage as one operationally simple unit,
which matters more at pre-seed than infra flexibility. RLS is written into
`schema.sql` from the first migration, not retrofitted — retrofitting RLS
onto live institutional data is a real incident risk we're not taking on.

Deferred cost: vendor lock-in to Supabase's Auth model. If we ever need
SSO/SAML for a large university (likely, eventually), that's a real
migration, not a config flag. Flagging now so it doesn't surprise us later.

 ADR-003: Chatbot provider is swappable, not hardcoded
`backend-fastapi/app/chatbot/provider.py` defines a `ChatProvider` protocol.
`OpenAIProvider` and `OllamaProvider` both implement it; the active one is
selected by `CHAT_PROVIDER` env var. This exists because "just call OpenAI"
is the shortcut that becomes tech debt the moment we want a free tier for
individual learners or a self-hosted option for a privacy-sensitive
institutional client. The RAG context (the 5 topic explanations) is
provider-agnostic — it's assembled once and passed to whichever provider is
active.

 ADR-004: Topic count is not hardcoded
`topics` is a table with a `prerequisite_id` self-reference, not a fixed
enum of 5. The skill-tree UI (`frontend/src/components/SkillTree.tsx`, not
yet built) reads topic count from the API. Building this as "5 hardcoded
routes" would be the fast path and the wrong one — course expansion is the
entire business model past the beginner tier.

 ADR-005: Gating enforced server-side, not just UI-locked
`user_progress` is checked in FastAPI before grading logic runs for any
topic — a locked topic returns 403 regardless of what the frontend sends.
The UI lock state is a UX convenience, never the source of truth. Trusting
the frontend lock alone is the single most common "worked in the demo,
broken in production" mistake in gated-content products.

 Boot-speed vs. deferred-optimization split
**Optimized now:** route-based code splitting (`frontend/src/routes.tsx`),
lazy-loaded circuit builder (heaviest bundle — Qiskit-adjacent viz libs),
landing + auth in the initial chunk only, static topic explanations served
with long cache headers (content doesn't change per-user).

Deliberately deferred: service worker / offline support, edge caching
of the FastAPI grading endpoint (grading is per-user and stateful, caching
it is a correctness risk before it's a perf win), image optimization
pipeline beyond what Vercel/Netlify does automatically.

 Deployment
- **Frontend → Vercel.** Chosen over Netlify because Vite + React is a
  first-class zero-config target on Vercel and preview deployments per PR
  are the workflow we want for a small team iterating on curriculum UI daily.
  
- **FastAPI → Railway.** Qiskit simulation is CPU-bound and can run several
  seconds on multi-qubit circuits pure serverless (Vercel/Netlify
  functions, Lambda) imposes execution time limits and cold-start penalties
  that fight this workload. Railway gives us a long-running container with
  predictable CPU, which is what a simulator wants.
- **Node service → Railway** (same host, separate service) for now; split
  out only if traffic patterns diverge enough to justify it.
- **Supabase → three hosted projects**, `dev` / `staging` / `prod`, never
  one shared instance. Institutional data crossing an environment boundary
  is not an acceptable risk even during early development.
  
- **CI:** GitHub Actions — merge to `main` deploys `frontend` to Vercel prod
  and `backend-fastapi`/`backend-node` to Railway prod via their GitHub
  integrations. Env vars live in each platform's dashboard per environment,
  never committed. PR branches get Vercel preview URLs automatically.
