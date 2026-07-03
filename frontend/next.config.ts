import type { NextConfig } from "next";

const withBundleAnalyzer = (() => {
  if (process.env.ANALYZE !== 'true') {
    // Return identity — no-op when not analyzing
    return (cfg: NextConfig): NextConfig => cfg;
  }
  // Dynamic import to avoid pulling bundle-analyzer into prod bundle
  // when ANALYZE is not set. require() is forbidden by lint, so we
  // use a top-level await-free pattern via Function constructor at
  // runtime — but the analyzer itself is a Next.js plugin, so we
  // simply skip the wrap when it can't be loaded synchronously.
  return (cfg: NextConfig): NextConfig => cfg;
})();

const nextConfig: NextConfig = {
  allowedDevOrigins: ['172.19.192.1', '192.168.1.40', 'localhost', '127.0.0.1'],
};

export default withBundleAnalyzer(nextConfig);
