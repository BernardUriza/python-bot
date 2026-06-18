import dynamic from "next/dynamic";

import { AgentChat } from "../components/AgentChat";
import { isEnabled } from "../lib/features";

// Optional module UIs are dynamically imported so each lands in its own lazy
// chunk — an app whose NEXT_PUBLIC_APP_MODULES omits the feature never fetches
// its code. The chat (core) stays statically imported; it's always on.
const CmsFeed = dynamic(() => import("../components/CmsFeed").then((m) => m.CmsFeed));
const MarketplaceCatalog = dynamic(() =>
  import("../components/MarketplaceCatalog").then((m) => m.MarketplaceCatalog),
);

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl space-y-12 px-4 py-8">
      {isEnabled("chat") && (
        <section>
          <AgentChat />
        </section>
      )}

      {isEnabled("cms") && (
        <section>
          <h2 className="mb-4 text-xl font-bold">Publicaciones</h2>
          <CmsFeed />
        </section>
      )}

      {isEnabled("marketplace") && (
        <section>
          <h2 className="mb-4 text-xl font-bold">Tienda</h2>
          <MarketplaceCatalog />
        </section>
      )}
    </main>
  );
}
