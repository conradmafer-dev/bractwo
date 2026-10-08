/* Google Identity Services: short-lived credentials stay in this closure only. */
(function (root) {
  'use strict';
  const GIS_URL = 'https://accounts.google.com/gsi/client?hl=pl';
  const CLASSES = new Set(['knight', 'ranger', 'mage', 'druid']);

  function sameOriginServer(raw, location) {
    if (!['http:', 'https:'].includes(location.protocol)) return false;
    try {
      const url = new URL(raw);
      return url.protocol === (location.protocol === 'https:' ? 'wss:' : 'ws:') &&
        url.host === location.host && url.pathname === '/ws' &&
        !url.search && !url.hash && !url.username && !url.password;
    } catch (_) { return false; }
  }

  function profilePacket(ticket, mode, name, classId) {
    if (!ticket || mode !== 'create') throw new Error('Wybierz ponownie konto Google.');
    name = String(name || '').trim();
    if (name.length < 3 || name.length > 20) throw new Error('Imię postaci musi mieć od 3 do 20 znaków.');
    if (!CLASSES.has(classId)) throw new Error('Wybierz klasę postaci.');
    return {type:'hello_google', ticket, mode:'create', name, class_id:classId, compact_state:true};
  }

  function mount(options) {
    const doc = options.document || root.document, loc = options.location || root.location;
    const fetcher = options.fetch || root.fetch.bind(root);
    const ids = ['googleSignIn','googleButton','googleStatus','googleRetry','googleAccount','googleCharacters',
      'googleCharacterCount','googleAccountHint','googleNewCharacter','googleProfile',
      'googleProfileTitle','googleName','googleClassPicker','googleContinue',
      'googleProfileBack','googleCancel','googleIntro','authError'];
    const ui = Object.fromEntries(ids.map(id => [id, doc.getElementById(id)]));
    if (Object.values(ui).some(value => !value)) return null;
    let config = null, ticket = '', challenge = '', classId = 'knight', account = null;
    let generation = 0, timer = null, pending = false, externalBusy = false, scriptPromise = null, preparing = false;
    let commentsSigningOut = false, retryCommentsLogout = false, verificationRequest = null;
    let buttonReady = false, buttonWidth = 0;
    const eligible = () => sameOriginServer(options.server, loc);
    const allowed = () => eligible() && !commentsSigningOut && (!options.canStart || options.canStart());
    const current = serial => generation === serial && allowed();
    const googleApi = () => root.google?.accounts?.id;
    const atLimit = () => (account?.characters?.length || 0) >= 4;
    const names = {knight:'Wojownik',ranger:'Łowca',mage:'Czarodziej',druid:'Druid'};

    function status(message, error = false) {
      ui.googleStatus.textContent = message || '';
      ui.googleStatus.classList.toggle('error', error);
    }
    function setBusy(value) {
      externalBusy = value;
      const disabled = pending || value || commentsSigningOut;
      ui.googleButton.inert = disabled;
      ui.googleButton.setAttribute('aria-disabled', String(disabled));
      for (const input of ui.googleAccount.querySelectorAll('input,button')) input.disabled = disabled;
      ui.googleNewCharacter.disabled = disabled || atLimit();
      ui.googleRetry.disabled = disabled;
      ui.googleCancel.disabled = value || commentsSigningOut;
      if (!disabled) renderGoogleButton();
    }
    function renderGoogleButton() {
      if (!buttonReady || !allowed() || !challenge || pending || externalBusy || ui.googleButton.hidden) return;
      const available = ui.googleSignIn.clientWidth;
      if (!available) return;
      const width = Math.max(200, Math.min(348, available));
      if (width === buttonWidth) return;
      ui.googleButton.replaceChildren();
      googleApi().renderButton(ui.googleButton, {type:'standard',theme:'outline',size:'large',text:'signin_with',
        shape:'rectangular',logo_alignment:'left',locale:'pl',width});
      buttonWidth = width;
    }
    function createProfile() {
      if (atLimit()) return;
      ui.googleProfile.hidden = false;
      ui.googleProfileTitle.textContent = 'Nowa postać';
      ui.googleName.autocomplete = 'off'; ui.googleName.value = '';
      ui.googleClassPicker.hidden = false;
      ui.googleContinue.textContent = 'Stwórz postać i wyrusz';
      ui.googleName.focus();
    }
    function clearSecrets() {
      ++generation; clearTimeout(timer); timer = null; ticket = ''; challenge = ''; pending = false; preparing = false;
      buttonReady = false; buttonWidth = 0;
      account = null; ui.googleName.value = '';
      googleApi()?.cancel();
      setBusy(externalBusy);
    }
    function reset({refresh = true, logout = false} = {}) {
      clearSecrets(); ui.googleAccount.hidden = true; ui.googleProfile.hidden = true;
      ui.googleButton.hidden = false; ui.googleIntro.hidden = false; ui.googleButton.replaceChildren();
      ui.googleCharacters.replaceChildren(); ui.googleRetry.hidden = true; ui.authError.textContent = ''; status('');
      if (logout) {
        googleApi()?.disableAutoSelect();
        if (root.BractwoComments) { void root.BractwoComments.logout(); return; }
      }
      if (refresh && allowed()) void prepare();
      else ui.googleRetry.hidden = !config?.enabled;
    }
    async function request(path, body) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 12000);
      try {
        const response = await fetcher(path, {
          method: body === undefined ? 'GET' : 'POST', credentials:'same-origin', cache:'no-store',
          redirect:'error', signal:controller.signal,
          ...(body === undefined ? {} : {headers:{'Content-Type':'application/json','X-Bractwo-Auth':'1'},body:JSON.stringify(body)})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Logowanie przez Google nie powiodło się. Spróbuj ponownie.');
        return data;
      } catch (error) {
        if (error.name === 'AbortError' || error instanceof TypeError) throw new Error('Nie można połączyć się z logowaniem Google. Sprawdź połączenie i spróbuj ponownie.');
        throw error;
      } finally { clearTimeout(timeout); }
    }
    function loadGoogle() {
      if (googleApi()) return Promise.resolve();
      if (scriptPromise) return scriptPromise;
      scriptPromise = new Promise((resolve, reject) => {
        const script = doc.createElement('script'); script.src = GIS_URL; script.async = true;
        let timeout = setTimeout(() => finish(new Error('Google nie odpowiedział. Sprawdź połączenie lub blokadę skryptów.')), 15000);
        function finish(error) {
          if (!timeout) return;
          clearTimeout(timeout); timeout = null; script.onload = null; script.onerror = null;
          if (error) { script.remove(); scriptPromise = null; reject(error); } else resolve();
        }
        script.onload = () => finish(googleApi() ? null : new Error('Nie udało się uruchomić logowania Google.'));
        script.onerror = () => finish(new Error('Nie udało się wczytać Google. Sprawdź połączenie i spróbuj ponownie.'));
        doc.head.append(script);
      });
      return scriptPromise;
    }
    function showAccount(value) {
      if (!value || !Array.isArray(value.characters)) throw new Error('Serwer nie przesłał listy postaci.');
      account = value;
      ui.googleButton.hidden = true; ui.googleIntro.hidden = true; ui.googleRetry.hidden = true;
      ui.googleAccount.hidden = false; ui.googleProfile.hidden = true; ui.googleCharacters.replaceChildren();
      for (const character of account.characters) {
        const button = doc.createElement('button'); button.type = 'button'; button.className = 'google-character';
        const name = doc.createElement('strong'); name.textContent = String(character.name || 'Postać');
        const detail = doc.createElement('span'); detail.textContent = `${names[character.class_id] || 'Poszukiwacz'} · poziom ${Number(character.level) || 1}`;
        const play = doc.createElement('b'); play.textContent = 'Graj ↗';
        button.append(name, detail, play);
        button.addEventListener('click', () => {
          if (!allowed() || pending || externalBusy || !ticket) return;
          status('Wczytywanie postaci…'); ui.authError.textContent = '';
          options.connect({type:'hello_google',ticket,mode:'select',character_id:String(character.id),compact_state:true});
        });
        ui.googleCharacters.append(button);
      }
      ui.googleCharacterCount.textContent = `${account.characters.length} / 4`;
      ui.googleAccountHint.textContent = atLimit() ? 'Masz już 4 postacie. Wybierz jedną, aby wejść do gry.' :
        account.characters.length ? 'Wybierz postać albo wykorzystaj wolne miejsce na kolejną.' : 'Stwórz pierwszą postać i rozpocznij wyprawę.';
      setBusy(externalBusy); status('Konto Google potwierdzone.');
      if (!account.characters.length) createProfile();
      else ui.googleCharacters.querySelector('button')?.focus();
    }
    async function receiveCredential(response, serial) {
      if (!current(serial) || pending || externalBusy || !challenge) return;
      let credential = typeof response?.credential === 'string' ? response.credential : '';
      if (!credential) { status('Google nie potwierdził logowania. Spróbuj ponownie.', true); return; }
      pending = true; setBusy(externalBusy); status('Potwierdzanie konta Google…'); ui.authError.textContent = '';
      // Only this page's own server verifies the ID token. It is never decoded or persisted here.
      const payload = {challenge, credential}; credential = '';
      try { response.credential = ''; } catch (_) { /* SDK may freeze its response. */ }
      const verification = verificationRequest = request('/auth/google/verify', payload);
      try {
        const result = await verification;
        if (!current(serial)) return;
        if (typeof result.ticket !== 'string' || !result.ticket) throw new Error('Serwer nie potwierdził logowania Google.');
        ticket = result.ticket; challenge = ''; clearTimeout(timer); pending = false; setBusy(externalBusy);
        showAccount(result.account);
        root.dispatchEvent(new CustomEvent('bractwo:account-verified'));
        timer = setTimeout(() => {
          if (generation !== serial || externalBusy) return;
          reset({refresh:false}); status('Potwierdzenie Google wygasło. Wybierz konto ponownie.', true);
        }, Math.max(1, Number(result.expires_in) || 300) * 1000);
      } catch (error) {
        if (current(serial)) { reset({refresh:false}); ui.googleRetry.hidden = false; status(error.message, true); }
      } finally {
        if (verificationRequest === verification) verificationRequest = null;
        payload.credential = '';
        if (generation === serial) { pending = false; setBusy(externalBusy); }
      }
    }
    async function prepare() {
      if (!allowed() || preparing) return;
      clearSecrets(); const serial = generation; preparing = true;
      ui.googleRetry.hidden = true; ui.googleAccount.hidden = true;
      ui.googleButton.hidden = false; ui.googleIntro.hidden = false;
      try {
        status('Przygotowywanie logowania Google…');
        if (!config) config = await request('/auth/google/config');
        if (!current(serial)) return;
        if (!config.enabled || typeof config.client_id !== 'string' || !config.client_id) {
          status('Logowanie Google nie jest jeszcze skonfigurowane.'); ui.googleIntro.hidden = true; return;
        }
        const start = await request('/auth/google/start', {});
        if (!current(serial)) return;
        if (!start.challenge || !start.nonce) throw new Error('Nie udało się przygotować logowania Google.');
        challenge = start.challenge; await loadGoogle();
        if (!current(serial)) return;
        googleApi().initialize({client_id:config.client_id, nonce:start.nonce, auto_select:false,
          ux_mode:'popup', callback:response => receiveCredential(response, serial)});
        buttonReady = true;
        renderGoogleButton();
        status('Wybierz konto Google, aby wejść do gry.');
        timer = setTimeout(() => {
          if (generation !== serial || pending || externalBusy || ticket) return;
          reset({refresh:false}); status('Aby użyć Google, odśwież przycisk logowania.');
        }, Math.max(1, (Number(start.expires_in) || 300) - 10) * 1000);
      } catch (error) {
        if (current(serial)) { ui.googleButton.replaceChildren(); ui.googleRetry.hidden = false; status(error.message, true); }
      } finally { if (generation === serial) preparing = false; }
    }

    for (const button of ui.googleClassPicker.querySelectorAll('[data-class]')) button.addEventListener('click', () => {
      classId = button.dataset.class;
      for (const item of ui.googleClassPicker.querySelectorAll('[data-class]')) {
        item.classList.toggle('selected', item.dataset.class === classId);
        item.setAttribute('aria-pressed', String(item.dataset.class === classId));
      }
    });
    ui.googleNewCharacter.addEventListener('click', () => createProfile());
    ui.googleProfileBack.addEventListener('click', () => { ui.googleProfile.hidden = true; });
    ui.googleRetry.addEventListener('click', () => {
      if (retryCommentsLogout && root.BractwoComments) { void root.BractwoComments.logout(); return; }
      config = null; void prepare();
    });
    ui.googleCancel.addEventListener('click', () => reset({logout:true}));
    root.addEventListener('bractwo:comments-signing-out', event => {
      commentsSigningOut = true; retryCommentsLogout = false;
      if (verificationRequest) event.detail?.waitUntil(verificationRequest);
      googleApi()?.disableAutoSelect();
      reset({refresh:false}); setBusy(externalBusy);
    });
    root.addEventListener('bractwo:comments-signed-out', () => {
      commentsSigningOut = false; retryCommentsLogout = false;
      googleApi()?.disableAutoSelect();
      reset();
    });
    root.addEventListener('bractwo:comments-signout-failed', () => {
      commentsSigningOut = false; retryCommentsLogout = true;
      reset({refresh:false});
      status('Nie udało się wylogować poprzedniego konta. Spróbuj ponownie.', true);
      ui.googleRetry.hidden = false;
    });
    ui.googleProfile.addEventListener('submit', event => {
      event.preventDefault(); if (!allowed() || pending || externalBusy || atLimit()) return;
      try {
        const packet = profilePacket(ticket, 'create', ui.googleName.value, classId);
        ui.authError.textContent = '';
        status('Tworzenie postaci…');
        options.connect(packet);
      } catch (error) { status(error.message, true); }
    });
    if (root.ResizeObserver) new root.ResizeObserver(renderGoogleButton).observe(ui.googleSignIn);
    else root.addEventListener('resize', renderGoogleButton);
    if (eligible()) void prepare();
    else { status('Otwórz grę pod adresem jej serwera, aby zalogować się przez Google.'); ui.googleIntro.hidden = true; }
    return {
      setBusy,
      cancel: () => reset({refresh:false}),
      resume: () => { if (!challenge && !ticket && allowed()) void prepare(); },
      logout: () => reset({logout:true}),
      success: () => reset({refresh:false}),
      connectionError(message, code) {
        ui.authError.textContent = '';
        if (code === 'google_retry' || !ticket) {
          reset({refresh:false}); status(`${message} Wybierz ponownie konto Google.`, true);
        } else {
          status(message, true);
          if (!ui.googleProfile.hidden) ui.googleName.focus();
        }
      }
    };
  }
  const api = {mount, sameOriginServer, profilePacket};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.BractwoGoogleAuth = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
