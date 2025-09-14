import { promises as fs } from 'fs';
import * as path from 'path';
import Mustache from 'mustache';
import { TPL } from './data.js';
import { latexEscape } from './utils.js';
function renderList(items) {
    if (!items || items.length === 0)
        return '';
    return `\\begin{itemize}[leftmargin=*]
${items.map(item => `  \\item ${latexEscape(item)}`).join('\n')}
\\end{itemize}`;
}
export async function renderLaTeX(header, skillsLine, bullets, education, projects) {
    const template = await fs.readFile(path.join(TPL, 'base.tmpl.tex'), 'utf8');
    const data = {
        HEADER: header,
        SKILLS_LINE: skillsLine ? `\\skillline{ ${latexEscape(skillsLine)} }` : '',
        BULLETS: bullets && bullets.length > 0 ? bullets.map(bullet => ({
            text: latexEscape(bullet)
        })) : [],
        EDUCATION: education ? `\\section*{Education}\n${latexEscape(education)}` : '',
        PROJECTS: projects && projects.length > 0 ? projects.map(project => ({
            text: latexEscape(project)
        })) : []
    };
    // Render the template with the data
    const result = Mustache.render(template, data);
    return result;
}
export async function renderCoverLetterLaTeX(header, contactLine, paragraphs) {
    const template = await fs.readFile(path.join(TPL, 'cover.tmpl.tex'), 'utf8');
    const data = {
        HEADER: header,
        CONTACT: contactLine ? latexEscape(contactLine) : '',
        PARAGRAPHS: (paragraphs || []).map(p => latexEscape(p))
    };
    const result = Mustache.render(template, data);
    return result;
}
