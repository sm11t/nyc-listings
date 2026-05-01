/* Firebase bridge module.
 *
 * Loads the Firebase v10 modular SDK from gstatic, initializes auth + firestore
 * if window.FIREBASE_CONFIG has real values, and exposes a small RPC-like API
 * on window.NYCFirebase that app.js consumes.
 *
 * If the config still has placeholders, we set window.NYCFirebase = { enabled: false }
 * so app.js can degrade to localStorage-only.
 *
 * Always dispatches a 'nyc-firebase-ready' event when finished probing.
 */

const SDK = 'https://www.gstatic.com/firebasejs/10.13.2';

const cfg = window.FIREBASE_CONFIG || {};
const isPlaceholder =
  !cfg.apiKey ||
  /REPLACE/i.test(cfg.apiKey) ||
  /REPLACE/i.test(cfg.projectId || '');

const api = {
  enabled: false,
  ready: Promise.resolve(false),
  uid: null,
  // listeners (set when enabled)
  onListingNotes: null,   // (listingId, cb) => unsubscribe
  addNote: null,          // (listingId, text, author) => Promise<docRef>
  deleteNote: null,       // (listingId, noteId) => Promise<void>
  onAllStatus: null,      // (cb) => unsubscribe — single listener for all statuses
  setStatus: null,        // (listingId, value) => Promise<void>
  onAllNoteCounts: null,  // (cb) => unsubscribe — single listener for note counts
  // failure surface for UI
  lastError: null,
};

if (isPlaceholder) {
  console.info('[firebase] config is placeholder — running in local-only mode');
  window.NYCFirebase = api;
  window.dispatchEvent(new Event('nyc-firebase-ready'));
} else {
  bootstrap().catch((err) => {
    console.error('[firebase] init failed', err);
    api.enabled = false;
    api.lastError = err;
    window.NYCFirebase = api;
    window.dispatchEvent(new Event('nyc-firebase-ready'));
  });
}

async function bootstrap() {
  const [{ initializeApp }, fs, authMod] = await Promise.all([
    import(`${SDK}/firebase-app.js`),
    import(`${SDK}/firebase-firestore.js`),
    import(`${SDK}/firebase-auth.js`),
  ]);

  const {
    getFirestore, collection, collectionGroup, doc, query, orderBy,
    onSnapshot, addDoc, deleteDoc, setDoc, serverTimestamp,
  } = fs;
  const { getAuth, signInAnonymously, onAuthStateChanged } = authMod;

  const app  = initializeApp(cfg);
  const db   = getFirestore(app);
  const auth = getAuth(app);

  // Wait for an authenticated UID before resolving ready=true.
  api.ready = new Promise((resolve) => {
    let resolved = false;
    onAuthStateChanged(auth, (u) => {
      api.uid = u?.uid || null;
      if (u && !resolved) { resolved = true; resolve(true); }
    });
    signInAnonymously(auth).catch((err) => {
      console.error('[firebase] anonymous sign-in failed', err);
      api.lastError = err;
      if (!resolved) { resolved = true; resolve(false); }
    });
  });

  api.enabled = true;

  // notes for one listing — ordered ascending by createdAt
  api.onListingNotes = (listingId, cb) => {
    const q = query(
      collection(db, 'listings', listingId, 'notes'),
      orderBy('createdAt', 'asc'),
    );
    return onSnapshot(q, (snap) => {
      const notes = [];
      snap.forEach((d) => {
        const data = d.data();
        notes.push({
          id: d.id,
          text: data.text || '',
          author: data.author || 'anonymous',
          uid: data.uid || null,
          createdAt: data.createdAt?.toMillis?.() ?? null,
        });
      });
      cb(notes);
    }, (err) => {
      console.error('[firebase] notes subscribe error', err);
      api.lastError = err;
      cb([]);
    });
  };

  api.addNote = async (listingId, text, author) => {
    if (!api.uid) throw new Error('not signed in');
    const trimmed = String(text || '').trim().slice(0, 2000);
    if (!trimmed) throw new Error('empty note');
    return addDoc(
      collection(db, 'listings', listingId, 'notes'),
      {
        text: trimmed,
        author: String(author || 'anonymous').slice(0, 40),
        uid: api.uid,
        createdAt: serverTimestamp(),
      },
    );
  };

  api.deleteNote = async (listingId, noteId) => {
    return deleteDoc(doc(db, 'listings', listingId, 'notes', noteId));
  };

  // status: one doc per listing in /listings/{id}/meta/status
  api.onAllStatus = (cb) => {
    const q = collectionGroup(db, 'meta');
    return onSnapshot(q, (snap) => {
      const map = {};
      snap.forEach((d) => {
        if (d.id !== 'status') return;
        const parent = d.ref.parent.parent;
        if (!parent) return;
        const v = d.data().value;
        if (v) map[parent.id] = v;
      });
      cb(map);
    }, (err) => {
      console.error('[firebase] status subscribe error', err);
      api.lastError = err;
      cb({});
    });
  };

  api.setStatus = async (listingId, value) => {
    if (!api.uid) throw new Error('not signed in');
    return setDoc(
      doc(db, 'listings', listingId, 'meta', 'status'),
      {
        value: value || null,
        uid: api.uid,
        updatedAt: serverTimestamp(),
      },
      { merge: true },
    );
  };

  // note counts: aggregated via collectionGroup('notes')
  api.onAllNoteCounts = (cb) => {
    const q = collectionGroup(db, 'notes');
    return onSnapshot(q, (snap) => {
      const counts = {};
      snap.forEach((d) => {
        const parent = d.ref.parent.parent;
        if (!parent) return;
        counts[parent.id] = (counts[parent.id] || 0) + 1;
      });
      cb(counts);
    }, (err) => {
      console.error('[firebase] note-counts subscribe error', err);
      api.lastError = err;
      cb({});
    });
  };

  window.NYCFirebase = api;
  await api.ready;
  window.dispatchEvent(new Event('nyc-firebase-ready'));
}
