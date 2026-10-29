// Run in Chrome on verwood.play-cricket.com/website/results/<id>
// Returns JSON with header lines plus each batting/bowling table in page order
// (innings 1 batting, innings 1 bowling, innings 2 batting, innings 2 bowling).
(() => {
  const s = document.body.innerText.replace(/\n{2,}/g, '\n');
  const i = s.search(/\d{1,2} [A-Z]+ \d{4} @/);
  const header = s.slice(i, i + 400).split('\n').map(x => x.trim()).filter(Boolean).slice(0, 16);
  const tables = [...document.querySelectorAll('table')]
    .filter(t => /BATTER|BOWLER/.test(t.innerText))
    .map(t => ({
      type: /BOWLER/.test(t.rows[0].innerText) ? 'bowling' : 'batting',
      rows: [...t.rows].slice(1).map(r => [...r.cells].map(c => c.innerText.replace(/\s+/g, ' ').trim()))
    }));
  // Innings order: the two club names listed straight after the SCORECARD / BALL BY BALL / STATISTICS tabs
  const lines = s.split('\n').map(x => x.trim()).filter(Boolean);
  const k = lines.findIndex(l => /^SCORECARD/.test(l));
  const innings_order = k < 0 ? [] : lines.slice(k + 1).filter(l => !/^(BALL BY BALL|STATISTICS)$/.test(l)).slice(0, 2);
  return JSON.stringify({ kind: 'scorecard_raw', id: (location.pathname.match(/\d+/) || [])[0], header, innings_order, tables });
})()
