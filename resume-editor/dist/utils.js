import fs from 'fs/promises';
export async function readText(path) {
    return fs.readFile(path, 'utf8');
}
export function uniqLower(arr) {
    const seen = new Set();
    const out = [];
    for (const s of arr) {
        const k = s.toLowerCase().trim();
        if (!k || seen.has(k))
            continue;
        seen.add(k);
        out.push(k);
    }
    return out;
}
export function latexEscape(s) {
    s = s.replace(/\\/g, '\\textbackslash{}');
    const map = {
        '&': '\\&', '%': '\\%', '$': '\\$', '#': '\\#',
        '_': '\\_', '{': '\\{', '}': '\\}', '~': '\\textasciitilde{}',
        '^': '\\^{}'
    };
    return Object.entries(map).reduce((str, [k, v]) => str.split(k).join(v), s);
}
export function approxLineCount(tex) {
    let lines = 0;
    for (const ln of tex.split('\n')) {
        const t = ln.trim();
        if (!t)
            continue;
        lines += 1 + Math.floor(t.length / 90);
    }
    return lines;
}
export async function newestFile(paths, names) {
    let newest = null;
    for (const dir of paths) {
        for (const name of names) {
            const filePath = `${dir}/${name}`;
            try {
                const stats = await fs.stat(filePath);
                if (!newest || stats.mtime > newest.mtime) {
                    newest = { name: filePath, mtime: stats.mtime };
                }
            }
            catch (error) {
                // File doesn't exist or can't be accessed
                continue;
            }
        }
    }
    return newest?.name ?? null;
}
