import { mkdir, writeFile } from 'node:fs/promises';
import { generateSnakeAnimation } from 'generate-snake-animation';

const login = process.env.GITHUB_USER;
const token = process.env.GITHUB_TOKEN;
if (!login || !token) throw new Error('GITHUB_USER and GITHUB_TOKEN are required');

// Keep the exact GitHub response used by the snake so its dates and
// contribution levels match GitHub's native calendar.
const nativeFetch = globalThis.fetch;
globalThis.fetch = async (input, options) => {
  const response = await nativeFetch(input, options);
  if (String(input) === 'https://api.github.com/graphql') {
    const payload = await response.clone().json();
    if (!response.ok || payload.errors?.length || !payload.data?.user?.contributionsCollection?.contributionCalendar?.weeks?.length) {
      throw new Error('GitHub did not return a usable contribution calendar');
    }
    await writeFile('.contribution-calendar.json', JSON.stringify(payload), 'utf8');
  }
  return response;
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
const [svg] = await generateSnakeAnimation(source, [output]);
if (typeof svg !== 'string' || !svg.includes('class="s s0"')) {
  throw new Error('Snake generation failed');
}
await writeFile('assets/contribution-snake.svg', svg, 'utf8');
console.log('Generated the current contribution snake');
