const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode for development
  reactStrictMode: true,

  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
    ],
  },

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_APP_NAME: 'InvestCTR',
  },
};

// Sentry configuration options
const sentryWebpackPluginOptions = {
  // For all available options, see:
  // https://github.com/getsentry/sentry-webpack-plugin#options

  // Only upload source maps in production
  silent: true,

  // Organization and project in Sentry
  // These are set via environment variables: SENTRY_ORG and SENTRY_PROJECT
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // Auth token for source map uploads
  // Set via SENTRY_AUTH_TOKEN environment variable
  authToken: process.env.SENTRY_AUTH_TOKEN,

  // For hiding source maps in production
  hideSourceMaps: true,

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,

  // Enable component annotations for better debugging
  reactComponentAnnotation: {
    enabled: true,
  },
};

// Only wrap with Sentry config if DSN is provided
const hasSentryDSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

module.exports = hasSentryDSN
  ? withSentryConfig(nextConfig, sentryWebpackPluginOptions)
  : nextConfig;
