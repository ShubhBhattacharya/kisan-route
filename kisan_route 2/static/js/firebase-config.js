/**
 * Firebase Configuration for KisanRoute Platform
 * Reads environment variables configured via Vite (VITE_FIREBASE_*)
 * or Flask backend window.__FIREBASE_CONFIG__ context injection.
 */

// Helper to safely access Vite import.meta.env or window global
function resolveEnv(key, windowFallback) {
  let val = '';
  try {
    if (typeof import.meta !== 'undefined' && import.meta && import.meta.env && import.meta.env[key]) {
      val = import.meta.env[key];
    }
  } catch (e) {}

  if (!val && typeof window !== 'undefined' && window.__FIREBASE_CONFIG__) {
    val = window.__FIREBASE_CONFIG__[windowFallback] || window.__FIREBASE_CONFIG__[key] || '';
  }

  if (!val && typeof process !== 'undefined' && process.env && process.env[key]) {
    val = process.env[key];
  }
  return val || '';
}

export const firebaseConfig = {
  apiKey: resolveEnv('VITE_FIREBASE_API_KEY', 'apiKey'),
  authDomain: resolveEnv('VITE_FIREBASE_AUTH_DOMAIN', 'authDomain'),
  projectId: resolveEnv('VITE_FIREBASE_PROJECT_ID', 'projectId'),
  appId: resolveEnv('VITE_FIREBASE_APP_ID', 'appId'),
  storageBucket: resolveEnv('VITE_FIREBASE_STORAGE_BUCKET', 'storageBucket'),
  messagingSenderId: resolveEnv('VITE_FIREBASE_MESSAGING_SENDER_ID', 'messagingSenderId'),
};

// Global export for non-module script tag usage
if (typeof window !== 'undefined') {
  window.krFirebaseConfig = firebaseConfig;
}

export function isFirebaseConfigured() {
  return Boolean(
    firebaseConfig.apiKey &&
    firebaseConfig.apiKey !== 'your_firebase_api_key' &&
    firebaseConfig.projectId
  );
}

export default firebaseConfig;
