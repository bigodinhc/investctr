// This file configures the initialization of Sentry on the server.
// The config you add here will be used whenever the server handles a request.
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

    // Filter out certain errors
    beforeSend(event, hint) {
      const error = hint.originalException;

      // Filter out certain server-side errors if needed
      if (error instanceof Error) {
        // Ignore authentication errors (expected behavior)
        if (error.message.includes("Invalid token")) {
          return null;
        }
      }

      return event;
    },

    // Ignore certain errors
    ignoreErrors: [
      // Ignore cancelled requests
      "AbortError",
      "cancelled",
    ],
  });
}
