const $ = (id) => document.getElementById(id);
const tooltip = $('tooltip');
let snakeTimer;

function flatten(weeks) {
  return weeks.flat().sort((a, b) => a.date.localeCompare(b.date));
}

function streaks(days) {
  let run = 0;
  let longest = 0;
  for (const day of days) {
    run = day.count > 0 ? run + 1 : 0;
    longest = Math.max(longest, run);
  }
  if (run === 0 && days.at(-1)?.count === 0) {
    for (let i = days.length - 2; i >= 0 && days[i].count > 0; i--) run++;
  }
  return { current: run, longest };
}

function showTooltip(day, x, y) {
  const count = day.count;
  tooltip.textContent = `${count} contribution${count === 1 ? '' : 's'} on ${new Date(day.date + 'T12:00:00Z').toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })}`;
  tooltip.hidden = false;
  tooltip.style.left = `${Math.min(x + 12, innerWidth - tooltip.offsetWidth - 12)}px`;
  tooltip.style.top = `${Math.max(8, y - tooltip.offsetHeight - 8)}px`;
}

function renderCalendar(weeks) {
  const grid = $('calendar');
  grid.replaceChildren();
  grid.style.setProperty('--weeks', weeks.length);
  const empty = new Map();
  let previousMonth = '';
  for (let w = 0; w < weeks.length; w++) {
    const lastDay = weeks[w].at(-1);
    if (lastDay) {
      const parsed = new Date(lastDay.date + 'T12:00:00Z');
      const monthKey = `${parsed.getUTCFullYear()}-${parsed.getUTCMonth()}`;
      if (monthKey !== previousMonth) {
        const month = document.createElement('span');
        month.className = 'month';
        month.textContent = parsed.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' });
        month.style.gridColumn = String(w + 2);
        grid.append(month);
        previousMonth = monthKey;
      }
    }
    for (const day of weeks[w]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `day level-${day.level}`;
      button.style.gridColumn = String(w + 2);
      button.style.gridRow = String(day.weekday + 2);
      button.setAttribute('aria-label', `${day.date}: ${day.count} contribution${day.count === 1 ? '' : 's'}`);
      button.addEventListener('pointerenter', (event) => showTooltip(day, event.clientX, event.clientY));
      button.addEventListener('pointermove', (event) => showTooltip(day, event.clientX, event.clientY));
      button.addEventListener('pointerleave', () => { tooltip.hidden = true; });
      button.addEventListener('focus', () => { const rect = button.getBoundingClientRect(); showTooltip(day, rect.left, rect.top); });
      button.addEventListener('blur', () => { tooltip.hidden = true; });
      grid.append(button);
      if (day.level === 0) empty.set(`${w},${day.weekday}`, button);
    }
  }
  for (const [row, label] of [[1, 'Mon'], [3, 'Wed'], [5, 'Fri']]) {
    const day = document.createElement('span');
    day.className = 'weekday';
    day.style.gridRow = String(row + 2);
    day.textContent = label;
    grid.append(day);
  }
  animateSnake(grid, empty);
}

function routeThroughEmptyDays(empty) {
  const visited = new Set();
  let best = [];
  const keys = [...empty.keys()];
  for (const start of keys) {
    if (visited.has(start)) continue;
    const component = [];
    const queue = [start];
    visited.add(start);
    for (let head = 0; head < queue.length; head++) {
      const key = queue[head];
      component.push(key);
      const [x, y] = key.split(',').map(Number);
      for (const neighbor of [`${x + 1},${y}`, `${x},${y + 1}`, `${x - 1},${y}`, `${x},${y - 1}`]) {
        if (empty.has(neighbor) && !visited.has(neighbor)) { visited.add(neighbor); queue.push(neighbor); }
      }
    }
    if (component.length > best.length) best = component;
  }
  if (best.length < 4) return [];
  const allowed = new Set(best);
  const walked = new Set();
  const route = [];
  function visit(key) {
    walked.add(key);
    route.push(empty.get(key));
    const [x, y] = key.split(',').map(Number);
    for (const neighbor of [`${x + 1},${y}`, `${x},${y + 1}`, `${x - 1},${y}`, `${x},${y - 1}`]) {
      if (allowed.has(neighbor) && !walked.has(neighbor)) {
        visit(neighbor);
        route.push(empty.get(key));
      }
    }
  }
  visit(best[0]);
  return route;
}

function animateSnake(grid, empty) {
  if (snakeTimer) clearInterval(snakeTimer);
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const route = routeThroughEmptyDays(empty);
  if (route.length < 4) return;
  const parts = Array.from({ length: 4 }, (_, index) => {
    const segment = document.createElement('span');
    segment.className = `snake-part${index === 0 ? ' head' : ''}`;
    grid.append(segment);
    return segment;
  });
  let step = 3;
  function move() {
    parts.forEach((part, index) => {
      const cell = route[(step - index + route.length) % route.length];
      part.style.left = `${cell.offsetLeft}px`;
      part.style.top = `${cell.offsetTop}px`;
      part.style.opacity = String(1 - index * 0.13);
    });
    step = (step + 1) % route.length;
  }
  move();
  snakeTimer = setInterval(move, 180);
  addEventListener('resize', move, { passive: true });
}

function renderLanguages(languages, total) {
  const container = $('languages');
  container.replaceChildren();
  for (const item of languages) {
    const percent = total ? item.bytes / total * 100 : 0;
    const row = document.createElement('div');
    row.className = 'language';
    const name = document.createElement('span'); name.className = 'language-name'; name.textContent = item.name;
    const bar = document.createElement('span'); bar.className = 'bar';
    const fill = document.createElement('span'); fill.className = 'bar-fill'; fill.style.width = `${percent}%`; bar.append(fill);
    const number = document.createElement('span'); number.className = 'percent'; number.textContent = `${percent.toFixed(1)}%`;
    row.append(name, bar, number);
    container.append(row);
  }
  if (!languages.length) container.textContent = 'No public language data yet.';
}

async function load() {
  try {
    const response = await fetch('./activity.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data.weeks) || !data.weeks.length) throw new Error('No contribution weeks');
    const { current, longest } = streaks(flatten(data.weeks));
    $('total').textContent = data.total.toLocaleString();
    $('current-streak').textContent = `${current} ${current === 1 ? 'day' : 'days'}`;
    $('longest-streak').textContent = `${longest} ${longest === 1 ? 'day' : 'days'}`;
    $('commits').textContent = data.commits.toLocaleString();
    $('repositories').textContent = data.repositoryCount.toLocaleString();
    $('stars').textContent = data.stars.toLocaleString();
    renderCalendar(data.weeks);
    renderLanguages(data.languages, data.languageBytesTotal);
    $('status').textContent = 'Contribution counts come directly from GitHub. The automated refresh runs every hour.';
  } catch (error) {
    $('status').textContent = 'GitHub activity is temporarily unavailable. Open the original contribution graph above for the latest data.';
    console.error('Unable to load GitHub activity:', error);
  }
}

load();
setInterval(load, 15 * 60 * 1000);
