import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The app is fully client-rendered, so it builds to static files that the
  // API serves itself (desktop build) or any static host serves (cloud);
  // no Node.js server is needed at runtime. Record pages take their IDs
  // from the query string for this reason; see lib/routes.ts.
  output: "export",
  // Emit contracts/view/index.html rather than contracts/view.html, the
  // layout a plain static file server resolves without rewrite rules.
  trailingSlash: true,
};

export default nextConfig;
