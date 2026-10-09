/** @type {import('next').NextConfig} */
const nextConfig = {
  // The build also writes a small self-contained server (.next/standalone) with only the files it needs.
  // The Docker image runs that instead of carrying node_modules and the source.
  output: "standalone",
}

module.exports = nextConfig
