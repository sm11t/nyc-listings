/* Firebase web config.
 *
 * This file ONLY sets window.FIREBASE_CONFIG. The actual SDK initialization
 * (initializeApp, anonymous auth, Firestore listeners) lives in firebase.js,
 * which is loaded as an ES module from gstatic — do NOT paste `import` lines
 * here, or the browser will throw SyntaxError and skip the whole file.
 *
 * NOTE: this config is NOT a secret. It only identifies your project; real
 * security is enforced by the Firestore security rules in web/README.md.
 *
 * If you reset this back to placeholder values the app falls back to per-
 * browser localStorage for notes & status (no cross-device sync).
 */
window.FIREBASE_CONFIG = {
  apiKey:            "AIzaSyCu8Mnxg5t7Ge1R1zvhDuLCN4JMQUkRxmM",
  authDomain:        "nyclistings-6d00e.firebaseapp.com",
  projectId:         "nyclistings-6d00e",
  storageBucket:     "nyclistings-6d00e.firebasestorage.app",
  messagingSenderId: "25702160596",
  appId:             "1:25702160596:web:92f8e09655f130b4e98341",
  measurementId:     "G-7P2CXV5CY0",
};
