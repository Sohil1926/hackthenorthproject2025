import { uniqLower } from './utils.js';
export function extractKeywords(jd, sm) {
    const jdl = jd.toLowerCase();
    const ks = [];
    for (const [canon, syns] of Object.entries(sm)) {
        for (const s of syns) {
            if (!s)
                continue;
            if (jdl.includes(s.toLowerCase())) {
                ks.push(canon);
                break;
            }
        }
    }
    return uniqLower(ks);
}
export function isRemote(jd) {
    jd = jd.toLowerCase();
    return jd.includes('remote') || jd.includes('hybrid');
}
