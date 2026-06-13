import type { MetadataRoute } from "next";
import { SITE_DESCRIPTION, SITE_NAME } from "../lib/site";

// Required when output: "export" is set in next.config.ts — the manifest is a
// Route Handler under the hood; force-static lands it as a plain
// /manifest.webmanifest in the SWA bundle.
export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: SITE_NAME,
    short_name: SITE_NAME,
    description: SITE_DESCRIPTION,
    id: "/",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#0b1220",
    theme_color: "#4f8cff",
    icons: [],
  };
}
