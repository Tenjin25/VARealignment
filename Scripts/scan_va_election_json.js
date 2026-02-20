// Script to scan va_county_aggregated_results.json and extract insights for research findings
// Run with: node scan_va_election_json.js

const fs = require('fs');
const path = require('path');

const DATA_PATH = path.join(__dirname, 'Data', 'va_county_aggregated_results.json');

function loadElectionData() {
  const raw = fs.readFileSync(DATA_PATH, 'utf8');
  return JSON.parse(raw);
}

function getMargin(dem, rep) {
  const total = dem + rep;
  if (total === 0) return 0;
  return ((dem - rep) / total) * 100;
}

function scanTrends(electionData) {
  const results = [];
  const byYear = electionData.results_by_year || {};
  const years = Object.keys(byYear).sort();
  const keyRaces = ['president', 'governor', 'us_senate'];

  // 1. Find counties with largest Dem and Rep margins in recent years
  const lastYear = years[years.length - 1];
  const prevYear = years[years.length - 2];
  if (!lastYear || !prevYear) return results;

  keyRaces.forEach(race => {
    const last = byYear[lastYear][race] || {};
    const prev = byYear[prevYear][race] || {};
    let maxDem = { county: '', margin: -Infinity };
    let maxRep = { county: '', margin: Infinity };
    let biggestSwing = { county: '', swing: 0 };
    Object.keys(last).forEach(county => {
      const l = last[county];
      const p = prev[county] || {};
      const marginLast = getMargin(l.dem_votes || 0, l.rep_votes || 0);
      const marginPrev = getMargin(p.dem_votes || 0, p.rep_votes || 0);
      if (marginLast > maxDem.margin) maxDem = { county, margin: marginLast };
      if (marginLast < maxRep.margin) maxRep = { county, margin: marginLast };
      const swing = marginLast - marginPrev;
      if (Math.abs(swing) > Math.abs(biggestSwing.swing)) biggestSwing = { county, swing };
    });
    results.push({
      race,
      year: lastYear,
      maxDem,
      maxRep,
      biggestSwing
    });
  });

  // 2. Statewide margin trend for each race
  keyRaces.forEach(race => {
    const margins = years.map(year => {
      const raceData = byYear[year][race] || {};
      let dem = 0, rep = 0;
      Object.values(raceData).forEach(row => {
        dem += row.dem_votes || 0;
        rep += row.rep_votes || 0;
      });
      return { year, margin: getMargin(dem, rep) };
    });
    results.push({ race, statewideMargins: margins });
  });

  // 3. Counties that flipped party between last two cycles
  keyRaces.forEach(race => {
    const last = byYear[lastYear][race] || {};
    const prev = byYear[prevYear][race] || {};
    const flips = [];
    Object.keys(last).forEach(county => {
      const l = last[county];
      const p = prev[county] || {};
      const marginLast = getMargin(l.dem_votes || 0, l.rep_votes || 0);
      const marginPrev = getMargin(p.dem_votes || 0, p.rep_votes || 0);
      if ((marginLast > 0 && marginPrev < 0) || (marginLast < 0 && marginPrev > 0)) {
        flips.push({ county, from: marginPrev > 0 ? 'Dem' : 'Rep', to: marginLast > 0 ? 'Dem' : 'Rep' });
      }
    });
    if (flips.length) results.push({ race, year: lastYear, flips });
  });

  return results;
}

function main() {
  const data = loadElectionData();
  const insights = scanTrends(data);
  console.log(JSON.stringify(insights, null, 2));
}

main();
