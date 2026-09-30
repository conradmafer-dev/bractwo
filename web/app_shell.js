/* Browser features only: fullscreen and an optional installed web-app shortcut. */
(function (root) {
  'use strict';
  let installPrompt = null, instance = null, installed = false;
  root.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); installPrompt = event;
    instance?.refresh();
  });
  root.addEventListener('appinstalled', () => {
    installPrompt = null; installed = true;
    instance?.refresh();
    instance?.announce('Bractwo Krain zostało dodane do aplikacji. Uruchomisz je z jego ikony.');
  });

  function create({ stop = () => {} } = {}) {
    if (instance) return instance;
    const doc = root.document, nav = root.navigator;
    const standaloneMedia = root.matchMedia('(display-mode: standalone)');
    const isStandalone = () => standaloneMedia.matches || nav.standalone === true;
    const isAppleMobile = () => /iPad|iPhone|iPod/.test(nav.userAgent) || (nav.platform === 'MacIntel' && nav.maxTouchPoints > 1);
    const inFullscreen = () => Boolean(doc.fullscreenElement || doc.webkitFullscreenElement);
    const makeButton = (id, label, glyph, className) => {
      const el = doc.createElement('button'); el.id = id; el.type = 'button';
      el.className = className; el.textContent = glyph;
      el.title = label; el.setAttribute('aria-label', label); el.dataset.mobileLabel = label;
      return el;
    };
    const authActions = doc.createElement('div'); authActions.className = 'app-auth-actions';
    authActions.setAttribute('aria-label', 'Aplikacja i ekran');
    const authFullscreen = makeButton('authFullscreenButton', 'Pełny ekran', '⛶ Pełny ekran', 'app-text-button');
    const authInstall = makeButton('authInstallButton', 'Zainstaluj grę', '⇩ Zainstaluj grę', 'app-text-button');
    authActions.append(authFullscreen, authInstall);
    const authCard = doc.querySelector('#authScreen .auth-card');
    authCard.insertBefore(authActions, authCard.querySelector('.auth-foot'));
    const fullscreen = makeButton('fullscreenButton', 'Pełny ekran', '⛶', 'icon-button app-icon-button');
    const install = makeButton('installAppButton', 'Zainstaluj grę', '⇩', 'icon-button app-icon-button');
    const actions = doc.querySelector('#gameUI .top-actions');
    actions.insertBefore(fullscreen, doc.getElementById('logoutButton'));
    actions.insertBefore(install, doc.getElementById('logoutButton'));
    const mobileFullscreen = makeButton('mobileFullscreenButton', 'Pełny ekran', '⛶', 'mobile-control app-icon-button');
    doc.getElementById('gameUI').append(mobileFullscreen);
    const fullscreenButtons = [authFullscreen, fullscreen, mobileFullscreen];
    const installButtons = [authInstall, install];

    const status = doc.createElement('div'); status.id = 'appShellStatus'; status.className = 'app-shell-status';
    status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); doc.body.append(status);
    let statusTimer;
    function announce(message) {
      root.clearTimeout(statusTimer); status.textContent = message;
      statusTimer = root.setTimeout(() => { status.textContent = ''; }, 7000);
    }
    const dialog = doc.createElement('dialog'); dialog.id = 'appHelpDialog';
    dialog.setAttribute('aria-labelledby', 'appHelpTitle');
    const head = doc.createElement('header');
    const title = doc.createElement('h2'); title.id = 'appHelpTitle';
    const close = makeButton('appHelpClose', 'Zamknij', '×', 'app-text-button');
    head.append(title, close);
    const body = doc.createElement('div'); body.id = 'appHelpBody';
    dialog.append(head, body); doc.body.append(dialog);
    let previousFocus = null;
    function closeHelp() { if (dialog.open) dialog.close(); }
    close.addEventListener('click', closeHelp);
    dialog.addEventListener('close', () => { stop(); previousFocus?.focus({ preventScroll: true }); });
    // The native modal supplies focus trapping and blocks mouse/touch behind it.
    root.addEventListener('keydown', event => {
      if (!dialog.open) return;
      if (event.key === 'Escape') { event.preventDefault(); closeHelp(); }
      event.stopImmediatePropagation();
    }, true);
    function help(heading, paragraphs) {
      stop(); title.textContent = heading; body.replaceChildren();
      for (const text of paragraphs) {
        const p = doc.createElement('p'); p.textContent = text; body.append(p);
      }
      if (!dialog.open) { previousFocus = doc.activeElement; dialog.showModal(); }
      close.focus({ preventScroll: true });
    }
    function installationHelp() {
      if (isStandalone() || installed) {
        help('Bractwo Krain jako aplikacja', ['Gra jest już otwarta jako aplikacja lub została dodana do aplikacji na tym urządzeniu.', 'Do gry wieloosobowej potrzebujesz połączenia z internetem.']);
      } else if (isAppleMobile()) {
        help('Dodaj Bractwo Krain do ekranu początkowego', ['Otwórz tę stronę w Safari. Wybierz Udostępnij → Dodaj do ekranu początkowego, a następnie Dodaj. Jeśli widzisz opcję „Otwórz jako aplikację internetową”, pozostaw ją włączoną.', 'Następnym razem uruchomisz grę z ikony Bractwa Krain. Gra wieloosobowa wymaga internetu.']);
      } else {
        help('Zainstaluj Bractwo Krain', ['W menu przeglądarki poszukaj „Zainstaluj aplikację”, „Zainstaluj tę stronę jako aplikację” lub „Dodaj do ekranu głównego”. Nazwa opcji zależy od przeglądarki.', 'Jeśli tej opcji nie ma, otwórz stronę w Chrome lub Edge albo dodaj ją do zakładek. Instalacja przez przeglądarkę wymaga bezpiecznego adresu HTTPS.', 'Po dodaniu aplikacji uruchomisz grę z jej ikony. Gra wieloosobowa wymaga internetu.']);
      }
    }
    function refresh() {
      const full = inFullscreen(), label = full ? 'Opuść pełny ekran' : 'Pełny ekran';
      for (const button of fullscreenButtons) {
        button.setAttribute('aria-pressed', String(full)); button.setAttribute('aria-label', label);
        button.title = label; button.dataset.mobileLabel = label;
      }
      authFullscreen.textContent = (full ? '⛶ Opuść pełny ekran' : '⛶ Pełny ekran');
      for (const button of installButtons) button.hidden = isStandalone() || installed;
    }
    let fullscreenBusy = false;
    async function toggleFullscreen() {
      if (fullscreenBusy) return;
      stop(); fullscreenBusy = true;
      try {
        if (inFullscreen()) {
          const exit = doc.exitFullscreen || doc.webkitExitFullscreen;
          if (exit) await exit.call(doc);
        } else {
          const request = doc.documentElement.requestFullscreen || doc.documentElement.webkitRequestFullscreen;
          if (!request) {
            help('Pełny ekran w tej przeglądarce', isAppleMobile()
              ? ['Ta przeglądarka nie udostępnia pełnego ekranu dla gry. W Safari wybierz Udostępnij → Dodaj do ekranu początkowego, a potem otwórz Bractwo Krain z jego ikony.', 'Aplikacja otworzy się bez zwykłego paska adresu. Do gry nadal potrzebujesz internetu.']
              : ['Ta przeglądarka nie udostępnia pełnego ekranu dla gry. Na komputerze możesz użyć klawisza F11 lub opcji pełnego ekranu w menu przeglądarki.']);
            return;
          }
          // Call before any await: fullscreen must start during the user's gesture.
          await request.call(doc.documentElement);
        }
        refresh();
      } catch (_) {
        help('Nie udało się włączyć pełnego ekranu', ['Przeglądarka odmówiła zmiany trybu ekranu. Spróbuj ponownie, otwierając grę bezpośrednio w osobnej karcie. Możesz też użyć opcji pełnego ekranu w menu przeglądarki.']);
      } finally { fullscreenBusy = false; }
    }
    let installBusy = false;
    async function installApp() {
      if (installBusy) return;
      stop();
      if (!installPrompt || isStandalone() || installed) { installationHelp(); return; }
      installBusy = true;
      const prompt = installPrompt; installPrompt = null;
      try {
        await prompt.prompt();
        const choice = await prompt.userChoice;
        announce(choice?.outcome === 'accepted'
          ? 'Prośba o instalację została zaakceptowana. Dokończ ją w przeglądarce.'
          : 'Instalację anulowano. Możesz wrócić do niej z menu przeglądarki.');
      } catch (_) { installationHelp(); }
      finally { installBusy = false; refresh(); }
    }
    for (const button of fullscreenButtons) button.addEventListener('click', toggleFullscreen);
    for (const button of installButtons) button.addEventListener('click', installApp);
    doc.addEventListener('fullscreenchange', refresh);
    doc.addEventListener('webkitfullscreenchange', refresh);
    standaloneMedia.addEventListener('change', refresh);
    // The worker saves only a disconnected-screen fallback and application icons.
    // Game data, credentials, HTTP APIs and the game code always use the network.
    if (root.isSecureContext && 'serviceWorker' in nav) {
      nav.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' }).catch(() => {
        // A failed worker must never prevent online play or claim installation.
      });
    }
    instance = { blocksControls: () => dialog.open, refresh, announce };
    refresh(); return instance;
  }
  root.BractwoAppShell = { create };
})(globalThis);
