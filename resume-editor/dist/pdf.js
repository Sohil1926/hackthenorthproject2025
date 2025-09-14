import path from 'path';
import fs from 'fs/promises';
import { spawn } from 'node:child_process';
import { OUT } from './data.js';
async function findExecutable(executables) {
    const { exec } = await import('node:child_process');
    const { promisify } = await import('node:util');
    const execAsync = promisify(exec);
    for (const exe of executables) {
        try {
            await execAsync(`where ${exe}`);
            return exe;
        }
        catch (e) {
            // Try next executable
        }
    }
    return null;
}
export async function ensureLaTeX() {
    const latexEngines = ['pdflatex', 'xelatex', 'lualatex'];
    const engine = await findExecutable(latexEngines);
    if (!engine) {
        throw new Error('No LaTeX installation found. Please install a LaTeX distribution like MiKTeX or TeX Live.\n' +
            'MiKTeX: https://miktex.org/download\n' +
            'TeX Live: https://www.tug.org/texlive/');
    }
    return engine;
}
export async function compileLatestPDF() {
    const engine = await ensureLaTeX();
    const texFiles = (await fs.readdir(OUT)).filter(n => n.endsWith('.tex'));
    if (!texFiles.length) {
        throw new Error('No .tex files found in out/artifacts. Generate a resume first with: node dist/cli.js gen ...');
    }
    // Sort by modification time
    const stats = await Promise.all(texFiles.map(async (file) => ({
        file,
        mtime: (await fs.stat(path.join(OUT, file))).mtime.getTime(),
    })));
    stats.sort((a, b) => b.mtime - a.mtime);
    const latestTex = stats[0].file;
    const texPath = path.join(OUT, latestTex);
    console.log(`Compiling ${latestTex} with ${engine}...`);
    // Run LaTeX engine twice to ensure references are resolved
    for (let i = 0; i < 2; i++) {
        await new Promise((resolve, reject) => {
            const p = spawn(engine, ['-interaction=nonstopmode', '-output-directory', OUT, texPath], {
                stdio: 'inherit'
            });
            p.on('close', (code) => {
                if (code === 0) {
                    resolve();
                }
                else if (i === 1) {
                    // Only fail on the second run if there are still errors
                    reject(new Error(`${engine} failed with exit code ${code}`));
                }
                else {
                    resolve();
                }
            });
        });
    }
    console.log(`PDF compiled into: ${OUT}`);
}
export async function openLatestPDF() {
    const pdfs = (await fs.readdir(OUT)).filter(n => n.endsWith('.pdf'));
    if (!pdfs.length)
        throw new Error('no .pdf in out/artifacts');
    const p = path.join(OUT, pdfs[pdfs.length - 1]);
    const opener = process.platform === 'darwin' ? 'open' : process.platform === 'linux' ? 'xdg-open' : '';
    if (!opener) {
        console.log('Open manually:', p);
        return;
    }
    await new Promise((resolve) => {
        const cp = spawn(opener, [p], { stdio: 'ignore' });
        cp.on('exit', () => resolve());
    });
}
