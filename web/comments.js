/* Public comments. Identity and moderation are always checked by the server. */
(function (root) {
  'use strict';
  const doc = root.document;
  const section = doc.getElementById('komentarze');
  if (!section) return;
  const list = doc.getElementById('commentsList');
  const form = doc.getElementById('commentForm');
  const character = doc.getElementById('commentCharacter');
  const body = doc.getElementById('commentBody');
  const submit = doc.getElementById('commentSubmit');
  const status = doc.getElementById('commentsStatus');
  const prompt = doc.getElementById('commentsLoginPrompt');
  const noCharacter = doc.getElementById('commentsNoCharacter');
  const more = doc.getElementById('commentsMore');
  const logoutButton = doc.getElementById('commentsLogout');
  const count = doc.getElementById('commentCount');
  let session = {authenticated:false, characters:[]};
  let cursor = null, loading = false, posting = false, revision = 0, sessionRevision = 0;
  let logoutPending = null, pendingMutation = null, identityRevision = 0;
  const dateFormat = new Intl.DateTimeFormat('pl-PL', {dateStyle:'medium', timeStyle:'short'});

  function message(text, error = false) {
    status.textContent = text;
    status.classList.toggle('comments-error', error);
  }
  async function request(path, method = 'GET', payload) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(path, {
        method, credentials:'same-origin', cache:'no-store', redirect:'error', signal:controller.signal,
        ...(method === 'GET' ? {} : {headers:{'Content-Type':'application/json', 'X-Bractwo-Comments':'1'}}),
        ...(payload === undefined ? {} : {body:JSON.stringify(payload)})
      });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) {
        const error = new Error(data?.message || 'Nie udało się zapisać zmiany. Spróbuj ponownie.');
        error.status = response.status;
        throw error;
      }
      return data;
    } catch (error) {
      if (error.name === 'AbortError' || error instanceof TypeError || error instanceof SyntaxError) {
        throw new Error('Nie można połączyć się z komentarzami. Spróbuj ponownie.');
      }
      throw error;
    } finally { clearTimeout(timer); }
  }
  function updateForm() {
    const characters = session.characters || [];
    form.hidden = !session.authenticated || !characters.length;
    prompt.hidden = !!session.authenticated;
    noCharacter.hidden = !session.authenticated || !!characters.length;
    logoutButton.hidden = !session.authenticated;
    for (const input of form.elements) input.disabled = posting || !!logoutPending;
    for (const button of list.querySelectorAll('.comment-delete')) button.disabled = posting || !!logoutPending || !session.authenticated;
    logoutButton.disabled = !!logoutPending;
  }
  async function refreshSession() {
    if (logoutPending) return;
    const serial = ++sessionRevision;
    try {
      const data = await request('/api/comments/session');
      if (serial !== sessionRevision) return;
      session = data;
      const selected = character.value;
      character.replaceChildren();
      for (const item of data.characters || []) {
        const option = doc.createElement('option');
        option.value = String(item.id); option.textContent = item.name;
        character.append(option);
      }
      if ([...character.options].some(option => option.value === selected)) character.value = selected;
      updateForm();
    } catch (error) {
      if (serial === sessionRevision) { session = {authenticated:false, characters:[]}; updateForm(); message(error.message, true); }
    }
  }
  function renderItem(item) {
    const li = doc.createElement('li'); li.className = 'comment-item'; li.dataset.commentId = String(item.id);
    const article = doc.createElement('article');
    const header = doc.createElement('header');
    const author = doc.createElement('strong'); author.textContent = item.author;
    const time = doc.createElement('time');
    const date = new Date(item.created_at);
    if (Number.isFinite(date.getTime())) { time.dateTime = date.toISOString(); time.textContent = dateFormat.format(date); }
    const text = doc.createElement('p'); text.className = 'comment-body'; text.textContent = item.body;
    header.append(author, time); article.append(header, text);
    if (item.can_delete) {
      const button = doc.createElement('button'); button.type = 'button'; button.className = 'comment-delete';
      button.textContent = 'Usuń swój komentarz';
      button.addEventListener('click', async () => {
        if (posting || logoutPending || !session.authenticated) return;
        if (!root.confirm('Usunąć ten komentarz?')) return;
        const identity = identityRevision;
        posting = true; updateForm();
        try {
          pendingMutation = request('/api/comments/' + encodeURIComponent(item.id), 'DELETE');
          await pendingMutation;
          if (identity !== identityRevision) return;
          const loaded = await loadComments(false);
          if (identity !== identityRevision) return;
          message(loaded ? 'Komentarz został usunięty.' : 'Komentarz został usunięty, ale nie udało się odświeżyć listy. Użyj przycisku „Odśwież komentarze”.', !loaded);
          doc.getElementById('commentsRefresh').focus();
        } catch (error) {
          if (identity !== identityRevision) return;
          message(error.message, true);
          if (error.status === 401) await refreshSession();
        } finally { pendingMutation = null; posting = false; updateForm(); }
      });
      article.append(button);
    }
    li.append(article); return li;
  }
  async function loadComments(append = false) {
    if (append && (loading || !cursor)) return false;
    const serial = ++revision;
    loading = true; more.disabled = true; list.setAttribute('aria-busy', 'true');
    try {
      const data = await request('/api/comments' + (append ? '?cursor=' + encodeURIComponent(cursor) : ''));
      if (serial !== revision) return false;
      if (!append) list.replaceChildren();
      const ids = new Set([...list.querySelectorAll('[data-comment-id]')].map(item => item.dataset.commentId));
      for (const item of data.items) if (!ids.has(String(item.id))) {
        list.append(renderItem(item)); ids.add(String(item.id));
      }
      if (!list.children.length) {
        const empty = doc.createElement('li'); empty.className = 'comments-empty';
        empty.textContent = 'Brak komentarzy. Podziel się pierwszym wrażeniem z gry.'; list.append(empty);
      }
      cursor = data.next_cursor; more.hidden = !cursor;
      updateForm();
      return true;
    } catch (error) { if (serial === revision) message(error.message, true); return false; }
    finally {
      if (serial === revision) { loading = false; more.disabled = false; list.removeAttribute('aria-busy'); }
    }
  }
  function logout() {
    if (logoutPending) return logoutPending;
    ++identityRevision; ++sessionRevision; ++revision;
    // Discard responses from the old account and serialize cookie-changing
    // requests, so a late Google verification cannot undo the sign-out.
    loading = false; more.disabled = false; list.removeAttribute('aria-busy');
    const waits = [];
    if (pendingMutation) waits.push(pendingMutation);
    logoutPending = Promise.resolve().then(async () => {
      root.dispatchEvent(new CustomEvent('bractwo:comments-signing-out', {detail:{waitUntil:promise => waits.push(promise)}}));
      try {
        await Promise.allSettled(waits);
        await request('/api/comments/logout', 'POST', {});
        ++sessionRevision;
        session = {authenticated:false, characters:[]}; character.replaceChildren(); body.value = '';
        count.textContent = '0 / 1000'; updateForm();
        const loaded = await loadComments(false);
        message(loaded ? 'Wylogowano.' : 'Wylogowano. Nie udało się odświeżyć komentarzy.', !loaded);
        root.dispatchEvent(new CustomEvent('bractwo:comments-signed-out'));
        return true;
      } catch (error) {
        message(error.message, true);
        root.dispatchEvent(new CustomEvent('bractwo:comments-signout-failed'));
        return false;
      } finally { logoutPending = null; updateForm(); }
    });
    updateForm();
    return logoutPending;
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (posting || logoutPending || !session.authenticated) return;
    const text = body.value.trim();
    if (text.length < 3 || text.length > 1000) { message('Komentarz musi mieć od 3 do 1000 znaków.', true); body.focus(); return; }
    const identity = identityRevision;
    posting = true; updateForm(); message('Zapisywanie komentarza…');
    try {
      pendingMutation = request('/api/comments', 'POST', {character_id:character.value, body:text});
      await pendingMutation;
      if (identity !== identityRevision) return;
      body.value = ''; count.textContent = '0 / 1000';
      const loaded = await loadComments(false);
      if (identity !== identityRevision) return;
      message(loaded ? 'Twój komentarz został dodany.' : 'Twój komentarz został dodany, ale nie udało się odświeżyć listy. Użyj przycisku „Odśwież komentarze”.', !loaded);
    } catch (error) { if (identity === identityRevision) { message(error.message, true); if (error.status === 401) await refreshSession(); } }
    finally { pendingMutation = null; posting = false; updateForm(); }
  });
  body.addEventListener('input', () => { count.textContent = body.value.length + ' / 1000'; });
  more.addEventListener('click', () => void loadComments(true));
  doc.getElementById('commentsRefresh').addEventListener('click', async () => {
    message(''); await refreshSession(); await loadComments(false);
  });
  logoutButton.addEventListener('click', () => void logout());
  root.addEventListener('bractwo:account-verified', async () => {
    if (logoutPending) return;
    ++identityRevision;
    await refreshSession(); await loadComments(false);
  });
  // Refresh the session after returning from a different game tab.
  doc.addEventListener('visibilitychange', async () => {
    if (!doc.hidden && !logoutPending) { await refreshSession(); await loadComments(false); }
  });
  root.BractwoComments = {logout, refresh:refreshSession};
  void refreshSession();
  if ('IntersectionObserver' in root) {
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { observer.disconnect(); void loadComments(false); }
    }, {rootMargin:'200px'});
    observer.observe(section);
  } else void loadComments(false);
})(globalThis);
