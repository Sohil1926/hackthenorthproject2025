import { execFile } from 'node:child_process';
import Anthropic from '@anthropic-ai/sdk';
import { promisify } from 'node:util';
const asyncExecFile = promisify(execFile);
export function preselectCandidates(bank, jdKeys, topN = 20) {
    const jdset = new Set(jdKeys.map(s => s.toLowerCase()));
    const scores = [];
    Object.values(bank).forEach(arr => {
        arr.forEach(b => {
            let s = 0;
            if (b.tags.some(t => jdset.has(t.toLowerCase())))
                s++;
            if (/\d/.test(b.text))
                s++;
            if (b.text.length <= 160)
                s++;
            if (s > 0)
                scores.push({ s, len: b.text.length, b });
        });
    });
    if (!scores.length) {
        Object.values(bank).forEach(arr => arr.forEach(b => scores.push({ s: 1, len: b.text.length, b })));
    }
    scores.sort((a, b) => b.s - a.s || a.len - b.len);
    const out = [];
    const seen = new Set();
    for (const sc of scores) {
        if (seen.has(sc.b.id))
            continue;
        seen.add(sc.b.id);
        out.push(sc.b);
        if (out.length >= topN)
            break;
    }
    return out;
}
export async function alignWithClaude(jd, role, company, profile, candidates, model) {
    const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const system = `You are a strict, high-integrity resume tailoring assistant.
- NEVER fabricate.
- You may ONLY select bullets from the provided "candidates" by ID.
- Keep it concise & one page.
Return ONLY JSON with keys: skills_line, add_bullets, remove_bullets, reorder, notes.`;
    const payload = {
        job_posting: jd, role, company,
        profile: { must_include: profile.must_include || [], hard_limits: profile.hard_limits || {} },
        candidates: candidates.map(c => ({ id: c.id, text: c.text })),
        instructions: "Select ONLY from candidates; no new content; output JSON only."
    };
    const resp = await anthropic.messages.create({
        model,
        system,
        messages: [{ role: "user", content: [{ type: "text", text: JSON.stringify(payload) }] }],
        max_tokens: 1000,
        temperature: 0
    });
    const text = (resp.content ?? [])
        .map((c) => c.type === "text" ? c.text : "")
        .join("\n")
        .trim();
    const jsonStr = extractJSON(text);
    try {
        return JSON.parse(jsonStr);
    }
    catch (e) {
        throw new Error("Claude did not return valid JSON. Raw: " + text);
    }
}
export async function coverLetterWithClaude(jd, role, company, profile, model) {
    const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const system = `You are a precise cover letter assistant. Write a concise, targeted cover letter in 3-5 short paragraphs.
- No fabrication beyond the provided profile and job posting.
- Focus on relevant experience and skills.
- Avoid repeating the resume; highlight alignment and motivation.
Return ONLY JSON with keys: contact_line (optional), paragraphs (array), notes (optional).`;
    const payload = {
        job_posting: jd, role, company,
        profile: {
            name: profile.name,
            email: profile.email,
            website: profile.website,
            links: profile.links || [],
            must_include: profile.must_include || []
        },
        instructions: "Write 3-5 paragraphs. Keep each paragraph under 120 words. Output JSON only."
    };
    const resp = await anthropic.messages.create({
        model,
        system,
        messages: [{ role: "user", content: [{ type: "text", text: JSON.stringify(payload) }] }],
        max_tokens: 1000,
        temperature: 0
    });
    const text = (resp.content ?? [])
        .map((c) => c.type === "text" ? c.text : "")
        .join("\n")
        .trim();
    const jsonStr = extractJSON(text);
    try {
        const obj = JSON.parse(jsonStr);
        if (!Array.isArray(obj.paragraphs))
            throw new Error('paragraphs missing');
        return obj;
    }
    catch (e) {
        throw new Error("Claude did not return valid JSON for cover letter. Raw: " + text);
    }
}
function extractJSON(s) {
    const start = s.indexOf("{");
    const end = s.lastIndexOf("}");
    if (start >= 0 && end > start)
        return s.slice(start, end + 1);
    throw new Error("No JSON object found in response.");
}
