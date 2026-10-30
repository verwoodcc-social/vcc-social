// Run in Chrome on verwood.play-cricket.com/website/results/<id>
// Returns JSON with header lines plus each batting/bowling table in page order
// (innings 1 batting, innings 1 bowling, innings 2 batting, innings 2 bowling).
// Handles both page layouts:
//  - classic scorecards: HTML <table>s with BATTER / BOWLER headers
//  - app-scored matches (e.g. Indoor): the "SCORECARD" tab (#iasScorecard) built from
//    div "SmartTable"s, one innings at a time behind per-team tabs. These are clicked
//    through in turn. Batting rows are reshaped to Name | How out | "" | R | B | 4s | 6s | SR.
// The result is also kept in window.__sc so it can be read in slices
// (window.__sc.slice(0, 800), window.__sc.slice(800), ...) if the tool output is truncated.
await (async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const s = document.body.innerText.replace(/\n{2,}/g, '\n');
  const i = s.search(/\d{1,2} [A-Z]+ \d{4} @/);
  const header = s.slice(i, i + 400).split('\n').map(x => x.trim()).filter(Boolean).slice(0, 16);
  let tables = [...document.querySelectorAll('table')]
    .filter(t => /BATTER|BOWLER/.test(t.innerText))
    .map(t => ({
      type: /BOWLER/.test(t.rows[0].innerText) ? 'bowling' : 'batting',
      rows: [...t.rows].slice(1).map(r => [...r.cells].map(c => c.innerText.replace(/\s+/g, ' ').trim()))
    }));
  // Innings order: the two club names listed straight after the SCORECARD / BALL BY BALL / STATISTICS tabs
  const lines = s.split('\n').map(x => x.trim()).filter(Boolean);
  const k = lines.findIndex(l => /^SCORECARD/.test(l));
  let innings_order = k < 0 ? [] : lines.slice(k + 1).filter(l => !/^(BALL BY BALL|STATISTICS)$/.test(l)).slice(0, 2);
  let layout = 'table';

  const ias = document.getElementById('iasScorecard');
  if (!tables.length && ias) {
    layout = 'ias';
    const tab = document.getElementById('iasScorecardtab-tab');
    if (tab) { tab.click(); await wait(1500); }
    for (let n = 0; n < 20 && !ias.querySelector('[class*=SmartTableStyle__TableContainer]'); n++) await wait(500);
    const periods = [...ias.querySelectorAll('[class*=PeriodTabs__TabItem]')];
    innings_order = periods.map(p => p.innerText.trim());
    const grab = () => [...ias.querySelectorAll('[class*=SmartTableStyle__TableContainer]')].map(c => {
      const head = (c.querySelector('[class*=TableHeaderContainer]') || c).innerText;
      const type = /BOWLER/.test(head) ? 'bowling' : 'batting';
      const rows = [...c.querySelectorAll('[class*=SmartTableStyle__TableRow-]')].map(r => {
        const cells = [...r.children].map(x => x.innerText.trim());
        if (type === 'batting') {
          const [name, ...how] = (cells[0] || '').split('\n');
          return [name.trim(), how.join(' ').replace(/\s+/g, ' ').trim(), '', ...cells.slice(1)];
        }
        return cells.map(x => x.replace(/\s+/g, ' '));
      });
      return { type, rows };
    });
    if (!periods.length) tables = grab();
    for (const p of periods) {
      (p.querySelector('a,button,span') || p).click();
      await wait(2000);
      tables.push(...grab());
    }
  }
  window.__sc = JSON.stringify({ kind: 'scorecard_raw', id: (location.pathname.match(/\d+/) || [])[0], layout, header, innings_order, tables });
  return window.__sc;
})()
