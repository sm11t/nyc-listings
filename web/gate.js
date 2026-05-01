/* Password gate — only kicks in when the listings payload is encrypted.
 *
 * The brain folder ships `data/listings.json` (plaintext) for local dev and
 * skips this gate entirely. The deploy script ships `data/listings.enc.json`
 * (an AES-GCM blob whose key is derived from the shared password via PBKDF2)
 * to the portfolio. Visitors must enter the password to decrypt.
 *
 * The plaintext password never appears in this file or anywhere in the
 * portfolio repo. We only see PBKDF2-derived bytes at runtime.
 *
 * Exports a single async function on window.NYCGate:
 *   loadListings()  ->  resolves with the parsed listings.json payload.
 */
(() => {
  'use strict';

  const PLAINTEXT_URL = 'data/listings.json';
  const CIPHER_URL    = 'data/listings.enc.json';
  const KEY_CACHE     = 'nyc-listings:gate-key:v1'; // base64 raw key bytes

  const b64decode = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  const bytesToB64 = (b) => btoa(String.fromCharCode(...new Uint8Array(b)));

  const enc = new TextEncoder();
  const dec = new TextDecoder();

  async function loadListings() {
    // 1. Plaintext path — brain / local dev.
    const direct = await tryFetch(PLAINTEXT_URL);
    if (direct) return JSON.parse(direct);

    // 2. Encrypted path — portfolio.
    const blobText = await tryFetch(CIPHER_URL);
    if (!blobText) {
      throw new Error('Could not load listings (neither plaintext nor encrypted file present).');
    }
    const blob = JSON.parse(blobText);
    const plaintext = await unlock(blob);
    return JSON.parse(plaintext);
  }

  async function tryFetch(url) {
    try {
      const r = await fetch(url, { cache: 'no-cache' });
      if (!r.ok) return null;
      return await r.text();
    } catch {
      return null;
    }
  }

  async function unlock(blob) {
    const cached = localStorage.getItem(KEY_CACHE);
    if (cached) {
      try {
        const key = await importRawKey(b64decode(cached));
        return await decryptWith(key, blob);
      } catch {
        // stale or wrong cached key — fall through and re-prompt
        localStorage.removeItem(KEY_CACHE);
      }
    }
    return promptUntilUnlocked(blob);
  }

  function promptUntilUnlocked(blob) {
    return new Promise((resolve) => {
      const overlay = buildOverlay();
      document.body.appendChild(overlay);
      const input = overlay.querySelector('input');
      const errorEl = overlay.querySelector('[data-role="err"]');
      const submit = overlay.querySelector('button');

      requestAnimationFrame(() => input.focus());

      async function tryOpen() {
        const pwd = input.value;
        if (!pwd) return;
        submit.disabled = true;
        submit.textContent = 'unlocking…';
        errorEl.textContent = '';
        try {
          const key = await deriveKey(pwd, blob);
          const plain = await decryptWith(key, blob);
          // success — cache key bytes for next visit
          const raw = await crypto.subtle.exportKey('raw', key);
          localStorage.setItem(KEY_CACHE, bytesToB64(raw));
          overlay.remove();
          resolve(plain);
        } catch (err) {
          errorEl.textContent = "wrong password";
          submit.disabled = false;
          submit.textContent = 'unlock';
          input.select();
        }
      }

      submit.addEventListener('click', tryOpen);
      overlay.querySelector('form').addEventListener('submit', (e) => { e.preventDefault(); tryOpen(); });
    });
  }

  async function deriveKey(password, blob) {
    const kdf = blob.kdf || {};
    const salt = b64decode(kdf.salt);
    const iterations = kdf.iterations || 250000;
    const hash = kdf.hash || 'SHA-256';
    const baseKey = await crypto.subtle.importKey(
      'raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']
    );
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt, iterations, hash },
      baseKey,
      { name: 'AES-GCM', length: 256 },
      true, // extractable so we can cache it
      ['decrypt'],
    );
  }

  async function importRawKey(rawBytes) {
    return crypto.subtle.importKey(
      'raw', rawBytes,
      { name: 'AES-GCM', length: 256 },
      true, ['decrypt'],
    );
  }

  async function decryptWith(key, blob) {
    const iv = b64decode(blob.iv);
    const ct = b64decode(blob.ct);
    const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
    return dec.decode(plainBuf);
  }

  function buildOverlay() {
    const div = document.createElement('div');
    div.className = 'gate-overlay';
    div.innerHTML = `
      <div class="gate-card">
        <div class="gate-mark"></div>
        <h2>NYC Listings</h2>
        <p class="gate-eyebrow">private map · ask asmit for the password</p>
        <form>
          <input type="password" autocomplete="current-password" placeholder="password" required />
          <button type="submit">unlock</button>
        </form>
        <p class="gate-err" data-role="err"></p>
      </div>
    `;
    return div;
  }

  window.NYCGate = { loadListings };
})();
