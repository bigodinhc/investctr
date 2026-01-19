// This file configures the initialization of Sentry on the client.
// The config you add here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

// Only initialize Sentry if DSN is configured
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    // Environment
    environment: process.env.NODE_ENV,

    // Adjust this value in production, or use tracesSampler for greater control
    tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

    // Setting this option to true will print useful information to the console while you're setting up Sentry.
    debug: false,

    // Replay configuration
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 0,

    // Integrations
    integrations: [
      Sentry.replayIntegration({
        // Additional replay options can be configured here
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    // Filter out certain errors
    beforeSend(event, hint) {
      // Don't send errors for certain conditions
      const error = hint.originalException;

      // Ignore network errors that might be caused by user connection issues
      if (error instanceof Error) {
        if (
          error.message.includes("NetworkError") ||
          error.message.includes("Failed to fetch") ||
          error.message.includes("Load failed")
        ) {
          return null;
        }
      }

      return event;
    },

    // Ignore certain errors by pattern
    ignoreErrors: [
      // Browser extension errors
      /extensions\//i,
      /^chrome:\/\//i,
      // Network errors
      "Network request failed",
      "Failed to fetch",
      // User-initiated navigation
      "ResizeObserver loop",
      // Common third-party script errors
      /gtag/i,
      /analytics/i,
    ],
  });
}
