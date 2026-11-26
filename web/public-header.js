(() => {
  'use strict';
  const counters = [...document.querySelectorAll('[data-character-count]')];
  if (!counters.length) return;
  const language = document.documentElement.lang;
  const labels = {
    en: ['character created', 'characters created'],
    es: ['personaje creado', 'personajes creados'],
    'pt-BR': ['personagem criado', 'personagens criados'],
  }[language];
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  fetch('/api/public-stats', { credentials: 'omit', signal: controller.signal })
    .then(response => {
      if (!response.ok) throw new Error('Public statistics unavailable');
      return response.json();
    })
    .then(({ characters_created: count }) => {
      if (!Number.isSafeInteger(count) || count < 0) return;
      const lastDigit = count % 10, lastTwo = count % 100;
      const label = labels ? labels[count === 1 ? 0 : 1]
        : count === 1 ? 'stworzona postać'
        : lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14)
          ? 'stworzone postacie' : 'stworzonych postaci';
      for (const counter of counters) {
        counter.querySelector('[data-character-count-value]').textContent = new Intl.NumberFormat(labels ? language : 'pl-PL').format(count);
        counter.querySelector('[data-character-count-label]').textContent = label;
        counter.hidden = false;
      }
    })
    .catch(() => { /* A missing number is preferable to an invented total. */ })
    .finally(() => clearTimeout(timeout));
})();
