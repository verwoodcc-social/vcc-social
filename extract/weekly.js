// Run in Chrome on verwood.play-cricket.com/Matches?tab=WeeklyResult  (results)
// or verwood.play-cricket.com/Matches?tab=Weekly                         (fixtures).
// Returns JSON: {kind, matches:[...]} parsed from the "Last 7 Days" / "Next 7 Days" list.
(() => {
  const isResults = /WeeklyResult/.test(location.href);
  const txt = document.body.innerText.replace(/\t/g, '\n').split('\n').map(s => s.trim()).filter(Boolean);
  const start = txt.findIndex(l => /^(Results - Last 7 Days|Upcoming - Next 7 Days)$/.test(l));
  const end = txt.findIndex((l, i) => i > start && /^Search by Keyword$/.test(l));
  const L = txt.slice(start + 1, end < 0 ? undefined : end).filter(l => !/^(assignment|search|Form Guide|[WLDTCA]{3,6})$/.test(l));
  const dateRe = /^(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day \d{1,2} \w+ \d{4}$/;
  const teamRe = /^(.+?)\s?-\s?(.+)$/;
  const ids = [...document.querySelectorAll('a')].filter(a => /assignment/.test(a.textContent))
    .map(a => ((a.getAttribute('href') || '').match(/\d{6,}/) || [])[0]).filter((v, i, a) => v && a.indexOf(v) === i);
  const out = []; let date = null, i = 0;
  while (i < L.length) {
    if (dateRe.test(L[i])) { date = L[i]; i++; continue; }
    if (isResults) {
      // STATUS, home team, home score, [pts, "pts"], Vs, [pts, "pts"], away team, away score
      const status = L[i++]; const m = { date, status, sides: [] };
      for (let s = 0; s < 2; s++) {
        while (L[i] && /^(\d+|pts|Vs)$/.test(L[i])) i++;
        const t = (L[i++] || '').match(teamRe) || [];
        const score = L[i] && /\d+ ?\/ ?(\d+|All out)|^\d+$/.test(L[i]) && !teamRe.test(L[i]) ? L[i++] : '';
        // Pairs cricket (e.g. U9 Indoor) adds "Net Score N" under each score; the result is decided on it.
        const nm = L[i] && L[i].match(/^Net Score (-?\d+)$/); if (nm) i++;
        m.sides.push({ club: (t[1] || '').trim(), team: (t[2] || '').trim(), score, ...(nm ? { net: nm[1] } : {}) });
      }
      m.id = ids[out.length] || null; out.push(m);
    } else {
      // time, home team, Vs, away team
      if (!/^\d{1,2}:\d{2}$/.test(L[i])) { i++; continue; }
      const time = L[i++]; const h = (L[i++] || '').match(teamRe) || [];
      while (L[i] === 'Vs') i++;
      const a = (L[i++] || '').match(teamRe) || [];
      out.push({ date, time, sides: [{ club: (h[1]||'').trim(), team: (h[2]||'').trim() }, { club: (a[1]||'').trim(), team: (a[2]||'').trim() }] });
    }
  }
  return JSON.stringify({ kind: isResults ? 'results_raw' : 'fixtures_raw', scraped: new Date().toISOString(), matches: out });
})()
