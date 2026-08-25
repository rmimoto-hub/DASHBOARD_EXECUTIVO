/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Nao anuncia "X-Powered-By: Next.js" nas respostas.
  poweredByHeader: false,
  // Nao gera AGENTS.md/CLAUDE.md automaticamente no diretorio do frontend.
  agentRules: false,
};

module.exports = nextConfig;
