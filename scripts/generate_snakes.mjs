import { mkdir, writeFile } from 'node:fs/promises';
import { generateSnakeAnimation } from 'generate-snake-animation';

const login = process.env.GITHUB_USER;
const token = process.env.GITHUB_TOKEN;
if (!login || !token) throw new Error('GITHUB_USER and GITHUB_TOKEN are required');

// The published generator fetches the rolling calendar. Scope its own GitHub
// GraphQL request to an individual year when rendering a historical calendar.
const nativeFetch = globalThis.fetch;
let requestedYear = null;
globalThis.fetch = (input, options) => {
  if (requestedYear === null || String(input) !== 'https://api.github.com/graphql') {
    return nativeFetch(input, options);
  }
  const payload = JSON.parse(options.body);
  const marker = 'contributionsCollection {';
  if (payload.query.split(marker).length !== 2) {
    throw new Error('The snake generator changed its GitHub calendar query');
  }
  const year = requestedYear;
  payload.query = payload.query.replace(
    marker,
    `contributionsCollection(from: "${year}-01-01T00:00:00Z", to: "${year}-12-31T23:59:59Z") {`,
  );
  return nativeFetch(input, { ...options, body: JSON.stringify(payload) });
};

const source = { platform: 'github', username: login, githubToken: token };
const output = {
  format: 'svg',
  drawOptions: {
    colorDots: ['#161b22', '#01311f', '#034525', '#0f6d31', '#00c647'],
    colorEmpty: '#161b22',
    colorDotBorder: '#1b1f230a',
    colorSnake: 'purple',
    sizeCell: 16,
    sizeDot: 12,
    sizeDotBorderRadius: 2,
  },
  animationOptions: { stepDurationMs: 100, frameByStep: 1 },
};

await mkdir('assets', { recursive: true });
for (const year of [null, ...Array.from({ length: new Date().getUTCFullYear() - 2024 }, (_, i) => 2024 + i)]) {
  requestedYear = year;
  const [svg] = await generateSnakeAnimation(source, [output]);
  if (typeof svg !== 'string' || !svg.includes('class="s s0"')) {
    throw new Error(`Snake generation failed for ${year ?? 'current year'}`);
  }
  const path = year === null ? 'assets/contribution-snake.svg' : `assets/contribution-snake-${year}.svg`;
  await writeFile(path, svg, 'utf8');
  console.log(`Generated ${path} from ${year ?? 'the rolling year'} calendar`);
}
