import "dotenv/config";
import { Stagehand } from "@browserbasehq/stagehand";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { z } from "zod";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
function log(s) { console.log(`[Runner] ${s}`); }
async function run(cmd, args, cwd) {
    log(`$ ${cmd} ${args.join(" ")}${cwd ? `  (cwd: ${cwd})` : ""}`);
    await new Promise((resolve, reject) => {
        const p = spawn(cmd, args, { stdio: "inherit", cwd });
        p.on("close", (code) => code === 0 ? resolve() : reject(new Error(`${cmd} exited ${code}`)));
    });
}
async function newestFile(dir, extensions) {
    try {
        const names = await fsp.readdir(dir);
        const filtered = names.filter(n => extensions.some(ext => n.toLowerCase().endsWith(ext.toLowerCase())));
        if (!filtered.length)
            return null;
        const stats = await Promise.all(filtered.map(async (f) => ({ name: f, mtime: (await fsp.stat(path.join(dir, f))).mtime.getTime() })));
        stats.sort((a, b) => b.mtime - a.mtime);
        return path.join(dir, stats[0].name);
    }
    catch {
        return null;
    }
}
async function generateDocs() {
    const role = process.env.ROLE || "SWE";
    const company = process.env.COMPANY || "Company";
    const jdPath = process.env.JD_PATH || path.join(__dirname, "resume-editor", "test_jd.txt");
    const model = process.env.ANTHROPIC_MODEL || "claude-3-5-sonnet-latest";
    const reDir = path.resolve(__dirname, "resume-editor");
    await run(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], reDir);
    await run(process.platform === "win32" ? "node.exe" : "node", ["dist/cli.js", "gen", "--jd-file", jdPath, "--role", role, "--company", company, "--anthropic-model", model], reDir);
    await run(process.platform === "win32" ? "node.exe" : "node", ["dist/cli.js", "gen-cover", "--jd-file", jdPath, "--role", role, "--company", company, "--anthropic-model", model], reDir);
    const outDir = path.join(reDir, "out", "artifacts");
    const names = await fsp.readdir(outDir);
    const texFiles = names
        .filter(n => n.toLowerCase().endsWith('.tex'))
        .map(n => path.join(outDir, n));
    const latestPDF = await newestFile(outDir, [".pdf"]); // available after you run "node dist/cli.js pdf"
    const stylesPath = path.join(outDir, "styles.tex");
    return { outDir, texFiles, latestPDF, stylesPath };
}
async function uploadToOverleaf(page, files) {
    await page.goto("https://www.overleaf.com/login");
    if (!process.env.OVERLEAF_EMAIL || !process.env.OVERLEAF_PASSWORD) {
        throw new Error("Set OVERLEAF_EMAIL and OVERLEAF_PASSWORD in .env to proceed with Overleaf automation.");
    }
    // Attempt a direct login using labeled fields
    try {
        await page.getByLabel(/email/i).fill(process.env.OVERLEAF_EMAIL);
        await page.getByLabel(/password/i).fill(process.env.OVERLEAF_PASSWORD);
        await page.getByRole("button", { name: /log in|sign in/i }).click();
    }
    catch {
        // Fallback to agent if selectors change
        const agent = page.stagehand.agent({ instructions: "You control the current page." });
        await agent.execute("Log in to Overleaf using the credentials from environment variables.");
    }
    // Navigate to projects page and create a blank project (UI may change; robust selectors recommended)
    await page.goto("https://www.overleaf.com/project");
    // Open upload dialog or file tree upload button
    // We try multiple strategies to reach a file input
    const tryOpenUpload = async () => {
        try {
            await page.getByRole("button", { name: /upload/i }).click({ timeout: 5000 });
            return true;
        }
        catch { }
        try {
            await page.getByText(/upload/i).click({ timeout: 5000 });
            return true;
        }
        catch { }
        return false;
    };
    await tryOpenUpload();
    // Find any file input and set files via payload (works in remote browsers)
    for (const file of files) {
        const input = page.locator('input[type="file"]');
        await input.setInputFiles({ name: file.name, mimeType: file.mimeType, buffer: file.buffer });
    }
}
async function main() {
    // 1) Generate resume + cover letter TeX locally
    const { outDir, texFiles, latestPDF, stylesPath } = await generateDocs();
    if (!texFiles || texFiles.length === 0)
        throw new Error("No TeX output found. Ensure generation succeeded.");
    // Prepare file payloads
    const files = [...texFiles, stylesPath].filter(Boolean).map(p => ({
        name: path.basename(p),
        mimeType: p.endsWith('.tex') ? 'text/x-tex' : 'application/octet-stream',
        buffer: fs.readFileSync(p)
    }));
    // 2) Start Stagehand in BROWSERBASE and upload to Overleaf
    const stagehand = new Stagehand({ env: "BROWSERBASE" });
    await stagehand.init();
    log(`Session: https://browserbase.com/sessions/${stagehand.browserbaseSessionID}`);
    const page = stagehand.page;
    await uploadToOverleaf(page, files);
    // WaterlooWorks flow (manual login required)
    await page.goto("https://waterlooworks.uwaterloo.ca/myAccount/dashboard.htm");
    console.log("\n🔐 MANUAL LOGIN REQUIRED");
    console.log("Please complete your login/authentication steps in the browser.");
    console.log("Once you're logged in and ready, press Enter in this terminal to continue...");
    await new Promise((resolve) => {
        process.stdin.once('data', () => {
            console.log("✅ Resuming automation...\n");
            resolve();
        });
    });
    const actResult = await page.act("Click the 'Co-op Jobs' button.");
    console.log(`Act result:\n`, actResult);
    const actResult2 = await page.act("Click the 'View Full-Cycle Service Job Board' button.");
    console.log(`Act result:\n`, actResult2);
    const actResult3 = await page.act("Scroll down to find the 'My Jobs' section, then click on the 'ShortList' text.");
    console.log(`Act result:\n`, actResult3);
    const actResult4 = await page.act("Click on the first job title text link (not the shadow DOM element) in the job title column to open the job details popup.");
    console.log(`Act result:\n`, actResult4);
    const jobDetails = await page.extract({
        instruction: "Extract all job information from the popup overlay including company name, position title, job description, requirements, skills, salary, location, and any other relevant details",
        schema: z.object({
            companyName: z.string().describe("The name of the company"),
            positionTitle: z.string().describe("The job position title"),
            jobDescription: z.string().describe("The main job description"),
            requirements: z.string().describe("Job requirements and qualifications"),
            skills: z.string().describe("Required or preferred skills"),
            salary: z.string().optional().describe("Salary or compensation information if available"),
            location: z.string().optional().describe("Job location if available"),
            additionalInfo: z.string().optional().describe("Any other relevant information like benefits, work type, etc.")
        })
    });
    console.log("\n📋 JOB DETAILS EXTRACTED:");
    console.log("================================");
    console.log(`Company: ${jobDetails.companyName}`);
    console.log(`Position: ${jobDetails.positionTitle}`);
    console.log(`Description: ${jobDetails.jobDescription}`);
    console.log(`Requirements: ${jobDetails.requirements}`);
    console.log(`Skills: ${jobDetails.skills}`);
    if (jobDetails.salary)
        console.log(`Salary: ${jobDetails.salary}`);
    if (jobDetails.location)
        console.log(`Location: ${jobDetails.location}`);
    if (jobDetails.additionalInfo)
        console.log(`Additional Info: ${jobDetails.additionalInfo}`);
    console.log("================================\n");
    log("Upload flow executed. Verify files in Overleaf project.");
    await stagehand.close();
}
main().catch((err) => {
    console.error(err);
    process.exit(1);
});
