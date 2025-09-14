import fs from 'fs/promises';
import path from 'path';
import YAML from 'yaml';
// Handle Windows paths in import.meta.url
const __filename = new URL(import.meta.url).pathname
    .replace(/^\/([A-Z]:\/)/, '$1') // Remove leading slash in Windows paths
    .replace(/%20/g, ' '); // Handle URL-encoded spaces
const BASE = path.resolve(path.dirname(__filename), '..');
export const DATA = path.join(BASE, 'data');
export const TPL = path.join(BASE, 'templates');
export const OUT = path.join(BASE, 'out', 'artifacts');
export async function loadBulletBank() {
    const raw = await fs.readFile(path.join(DATA, 'bullet_bank.json'), 'utf8');
    const obj = JSON.parse(raw);
    const bank = {};
    for (const [k, arr] of Object.entries(obj)) {
        bank[k] = arr.map(b => ({ id: b['id'], text: b['text'], tags: b['tags'] || [] }));
    }
    return bank;
}
export async function loadSkillsMap() {
    const raw = await fs.readFile(path.join(DATA, 'skills_map.yaml'), 'utf8');
    return YAML.parse(raw);
}
export async function loadProfile() {
    const raw = await fs.readFile(path.join(DATA, 'profile.yaml'), 'utf8');
    const p = YAML.parse(raw);
    if (!p.hard_limits)
        p.hard_limits = {};
    if (!p.hard_limits.max_lines)
        p.hard_limits.max_lines = 60;
    return p;
}
