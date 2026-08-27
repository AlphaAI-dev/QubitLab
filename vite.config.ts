import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Manual chunk split keeps the heaviest deps (three.js, recharts) and the
// challenge components out of the initial landing+auth chunk — a visitor
// who never gets past the landing page only downloads the hero + tokens.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          three: ["three"],
          recharts: ["recharts"],
          challenges: [
            "./src/components/challenges/ChallengeRunner.tsx",
            "./src/components/challenges/PredictChallenge.tsx",
            "./src/components/challenges/BuildChallenge.tsx",
            "./src/components/challenges/FixChallenge.tsx",
            "./src/components/challenges/ExperimentChallenge.tsx",
            "./src/components/challenges/ExplainChallenge.tsx",
            "./src/components/challenges/BossChallenge.tsx",
          ],
        },
      },
    },
  },
});
