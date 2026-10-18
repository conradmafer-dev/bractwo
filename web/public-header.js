(() => {
  'use strict';
  const counters = [...document.querySelectorAll('[data-character-count]')];
  if (!counters.length) return;
  const english = document.documentElement.lang.toLowerCase().startsWith('en');
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
      const label = english ? (count === 1 ? 'character created' : 'characters created')
        : count === 1 ? 'stworzona postać'
        : lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14)
          ? 'stworzone postacie' : 'stworzonych postaci';
      for (const counter of counters) {
        counter.querySelector('[data-character-count-value]').textContent = new Intl.NumberFormat(english ? 'en' : 'pl-PL').format(count);
        counter.querySelector('[data-character-count-label]').textContent = label;
        counter.hidden = false;
      }
    })
    .catch(() => { /* A missing number is preferable to an invented total. */ })
    .finally(() => clearTimeout(timeout));
})();
