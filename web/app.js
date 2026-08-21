/* Weather Diary frontend. Vanilla JS, no build step. Read-only: this page
   never triggers generation, it only reads what the unattended schedule
   already wrote. */

(function () {
  'use strict';

  var API = (window.WD_API_BASE || '').replace(/\/$/, '');
  var POLL_MS = 5 * 60 * 1000;

  function fmtTime(iso) {
    return (iso || '').replace('T', ' ').slice(0, 16) + ' UTC';
  }

  function renderEntry(e) {
    var el = document.createElement('article');
    el.className = 'entry';

    var art = document.createElement('div');
    art.className = 'art';
    art.innerHTML = e.svg || '';
    var svg = art.querySelector('svg');
    if (svg) { svg.removeAttribute('width'); svg.removeAttribute('height'); svg.style.display = 'block'; svg.style.width = '100%'; }
    el.appendChild(art);

    var body = document.createElement('div');
    body.className = 'body';

    var caption = document.createElement('p');
    if (e.caption) {
      caption.className = 'caption';
      caption.textContent = e.caption;
    } else {
      caption.className = 'caption missing';
      caption.textContent = 'The diary lost its words this time (' +
        (e.caption_error || 'unknown reason') + '). The sky still painted itself.';
    }
    body.appendChild(caption);

    var w = e.weather || {};
    var stats = document.createElement('p');
    stats.className = 'stats';
    stats.textContent = [
      w.city,
      w.temperature_c + '°C',
      w.cloud_cover_pct + '% cloud',
      w.wind_speed_kmh + ' km/h wind',
      w.precipitation_mm + ' mm rain'
    ].filter(Boolean).join(' · ');
    body.appendChild(stats);

    var stamp = document.createElement('p');
    stamp.className = 'stamp';
    stamp.textContent = fmtTime(e.generated_at) + ' · unattended';
    body.appendChild(stamp);

    el.appendChild(body);
    return el;
  }

  function render(entries) {
    var wrap = document.getElementById('gallery');
    wrap.innerHTML = '';
    if (!entries || !entries.length) {
      var p = document.createElement('p');
      p.className = 'empty-note';
      p.textContent = 'No entries yet. The first scheduled run will paint one on its own.';
      wrap.appendChild(p);
      return;
    }
    entries.forEach(function (e) { wrap.appendChild(renderEntry(e)); });
  }

  function refresh() {
    fetch(API + '/gallery')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) { render(data.entries); })
      .catch(function (err) {
        var wrap = document.getElementById('gallery');
        wrap.innerHTML = '';
        var p = document.createElement('p');
        p.className = 'loading-note';
        p.textContent = 'Could not reach the diary (' + err.message + '). Refresh in a moment.';
        wrap.appendChild(p);
      });
  }

  if (!API) {
    document.getElementById('gallery').innerHTML =
      '<p class="loading-note">No API configured. config.js is missing its base URL.</p>';
    return;
  }

  refresh();
  setInterval(refresh, POLL_MS);
})();
