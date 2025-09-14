import path from 'path';
import fs from 'fs/promises';
import dotenv from 'dotenv';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import { loadBulletBank, loadProfile, loadSkillsMap, OUT, TPL } from './data.js';
import { extractKeywords, isRemote } from './jd.js';
import { preselectCandidates, alignWithClaude, coverLetterWithClaude } from './align.js';
import { renderLaTeX, renderCoverLetterLaTeX } from './render.js';
import { compileLatestPDF, openLatestPDF } from './pdf.js';
import { latexEscape } from './utils.js';
function sanitize(s) {
    return s.replaceAll('/', '-').trim();
}
// Ensure env is loaded even if .env is in project root
try {
    // Try resume-editor/.env
    dotenv.config({ path: path.resolve(process.cwd(), '.env') });
    // Try project root ../.env
    dotenv.config({ path: path.resolve(process.cwd(), '..', '.env') });
}
catch { }
async function gen(jdFile, role, company, model) {
    const jd = jdFile === '-' ? await new Promise(r => {
        let d = '';
        process.stdin.on('data', c => d += c);
        process.stdin.on('end', () => r(d));
    }) : await fs.readFile(jdFile, 'utf8');
    const bank = await loadBulletBank();
    const sm = await loadSkillsMap();
    const profile = await loadProfile();
    const jdKeys = extractKeywords(jd, sm);
    const candidates = preselectCandidates(bank, jdKeys, 20);
    let selIDs = [];
    let notes = [];
    if (!process.env.ANTHROPIC_API_KEY) {
        console.error('ANTHROPIC_API_KEY not set; falling back to deterministic selection.');
    }
    else {
        try {
            const out = await alignWithClaude(jd, role, company, profile, candidates, model);
            notes = out.notes || [];
            selIDs = (out.reorder && out.reorder.length ? out.reorder : out.add_bullets) || [];
        }
        catch (e) {
            console.error('Claude error, fallback:', e.message || e);
        }
    }
    const id2text = new Map(candidates.map(c => [c.id, c.text]));
    let finalBullets = selIDs.map(id => id2text.get(id)).filter(Boolean);
    if (!finalBullets.length)
        finalBullets = candidates.slice(0, 8).map(c => c.text);
    const bulk = finalBullets.join(' ').toLowerCase();
    const finalSkills = Object.keys(sm).filter(k => bulk.includes(k.toLowerCase()));
    if (isRemote(jd))
        finalSkills.push('remote');
    // Handle projects from either projects or projects_block
    const projectsText = profile.projects || profile.projects_block || '';
    const projects = projectsText.split('\n').filter(p => p.trim().length > 0);
    // Handle education from either education or education_block
    const education = profile.education || profile.education_block || '';
    // Build header with available information
    const headerParts = [
        profile.name,
        profile.email,
        profile.website,
        ...(profile.links || [])
    ].filter((v) => typeof v === 'string' && v.length > 0)
        .map(latexEscape)
        .join(' \\ ');
    const tex = await renderLaTeX(headerParts, finalSkills.join(' · '), finalBullets, education, projects);
    // Line budget
    const maxLines = profile.hard_limits?.max_lines ?? 60;
    const texLimited = (() => {
        const count = (t) => t.split('\n').reduce((acc, ln) => acc + (ln.trim() ? 1 + Math.floor(ln.trim().length / 90) : 0), 0);
        if (count(tex) <= maxLines)
            return tex;
        const parts = tex.split('\\item ');
        while (parts.length > 1) {
            parts.pop();
            const t = parts.join('\\item ');
            if (count(t) <= maxLines)
                return t;
        }
        return tex;
    })();
    const base = `${sanitize(profile.name)} - ${sanitize(company)} - W25`;
    await fs.mkdir(OUT, { recursive: true });
    await fs.writeFile(path.join(OUT, base + '.tex'), texLimited, 'utf8');
    await fs.copyFile(path.join(TPL, 'styles.tex'), path.join(OUT, 'styles.tex'));
    await fs.writeFile(path.join(OUT, base + '.json'), JSON.stringify({ company, role, coverage: 0 }), 'utf8');
    console.log(`Generated: out/artifacts/${base}.tex`);
    console.log(`Next: node dist/cli.js pdf`);
}
async function genCover(jdFile, role, company, model) {
    const jd = jdFile === '-' ? await new Promise(r => {
        let d = '';
        process.stdin.on('data', c => d += c);
        process.stdin.on('end', () => r(d));
    }) : await fs.readFile(jdFile, 'utf8');
    const profile = await loadProfile();
    let paragraphs = [];
    let contact = '';
    if (!process.env.ANTHROPIC_API_KEY) {
        console.error('ANTHROPIC_API_KEY not set; generating a minimal cover letter.');
        paragraphs = [
            `Dear Hiring Team at ${company},`,
            `I am excited to apply for the ${role} role. My background and projects align closely with your needs.`,
            `Thank you for your time and consideration.`,
            `Sincerely,`,
            `${profile.name}`
        ];
    }
    else {
        try {
            const out = await coverLetterWithClaude(jd, role, company, profile, model);
            paragraphs = out.paragraphs || [];
            contact = out.contact_line || '';
        }
        catch (e) {
            console.error('Claude error for cover letter, fallback:', e.message || e);
            paragraphs = [
                `Dear Hiring Team at ${company},`,
                `I am excited to apply for the ${role} role.`,
                `Sincerely,`,
                `${profile.name}`
            ];
        }
    }
    const headerParts = [profile.name].filter(Boolean).join(' \\ ');
    const contactLine = contact || [profile.email, profile.website, ...(profile.links || [])]
        .filter((v) => typeof v === 'string' && v.length > 0)
        .map(latexEscape)
        .join(' \\ ');
    const tex = await renderCoverLetterLaTeX(headerParts, contactLine, paragraphs);
    const base = `${sanitize(profile.name)} - ${sanitize(company)} - W25 - Cover Letter`;
    await fs.mkdir(OUT, { recursive: true });
    await fs.writeFile(path.join(OUT, base + '.tex'), tex, 'utf8');
    await fs.copyFile(path.join(TPL, 'styles.tex'), path.join(OUT, 'styles.tex'));
    console.log(`Generated: out/artifacts/${base}.tex`);
}
async function main() {
    const argv = await yargs(hideBin(process.argv))
        .command('gen', 'Generate TeX from JD', y => y
        .option('jd-file', { type: 'string', demandOption: true, desc: "Path to JD .txt ('-' for stdin)" })
        .option('role', { type: 'string', default: 'SWE' })
        .option('company', { type: 'string', default: 'Company' })
        .option('anthropic-model', { type: 'string', default: 'claude-3-5-sonnet-latest' }), async (args) => {
        await gen(String(args['jd-file']), String(args.role), String(args.company), String(args['anthropic-model']));
    })
        .command('gen-cover', 'Generate Cover Letter TeX from JD', y => y
        .option('jd-file', { type: 'string', demandOption: true, desc: "Path to JD .txt ('-' for stdin)" })
        .option('role', { type: 'string', default: 'SWE' })
        .option('company', { type: 'string', default: 'Company' })
        .option('anthropic-model', { type: 'string', default: 'claude-3-5-sonnet-latest' }), async (args) => {
        await genCover(String(args['jd-file']), String(args.role), String(args.company), String(args['anthropic-model']));
    })
        .command('gen-both', 'Generate Resume and Cover Letter TeX from JD', y => y
        .option('jd-file', { type: 'string', demandOption: true, desc: "Path to JD .txt ('-' for stdin)" })
        .option('role', { type: 'string', default: 'SWE' })
        .option('company', { type: 'string', default: 'Company' })
        .option('anthropic-model', { type: 'string', default: 'claude-3-5-sonnet-latest' }), async (args) => {
        await gen(String(args['jd-file']), String(args.role), String(args.company), String(args['anthropic-model']));
        await genCover(String(args['jd-file']), String(args.role), String(args.company), String(args['anthropic-model']));
    })
        .command('pdf', 'Compile latest PDF', y => y, async () => { await compileLatestPDF(); })
        .command('open', 'Open latest PDF', y => y, async () => { await openLatestPDF(); })
        .demandCommand(1)
        .strict()
        .help()
        .argv;
}
main().catch(err => { console.error(err); process.exit(1); });
