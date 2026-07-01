import type { MetadataRoute } from "next";
import { config } from "@/lib/config";

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ["", "/discovery", "/store"];
  return routes.map((path) => ({
    url: `${config.siteUrl}${path}`,
    changeFrequency: "daily",
    priority: path === "" ? 1 : 0.8,
  }));
}
