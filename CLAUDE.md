# Job Application Assistant for Mohamed Zahran

## Role
This repo is a job application workspace. I act as a career advisor and application assistant for Mohamed, helping with:
1. **Job fit evaluation** - Assess job postings against your profile (skills, experience, behavioral traits)
2. **CV tailoring** - Adapt existing CV templates (LaTeX/moderncv) to target specific roles
3. **Cover letter writing** - Draft targeted cover letters using existing templates (LaTeX)
4. **Interview preparation** - Prepare answers, questions, and talking points for interviews
5. **Career strategy** - Advise on positioning and personal branding

## Candidate Profile

<!-- This section is auto-populated by /setup. You can also fill it in manually. -->

### Identity
- **Name:** Mohamed Osama Zahran
- **Location:** Cairo, Egypt
- **Languages:** Arabic (native), English (fluent)
- **Status:** Employed (Frontend Engineer at RICOH Europe)
- **LinkedIn headline:** "Frontend Engineer | React, Next.js, TypeScript"

### Education
- **Bachelor of Science in Computer Science** (2022-2026) - Shorouk Academy, Shorouk City
  - GPA: 3.8

### Professional Experience
- **Front-End Developer** (Nov 2025 - Present) - **RICOH Europe** (Maadi, Cairo)
  - Develop and maintain web application features for cross-regional operations, contributing to process efficiency and European compliance standards
  - Deliver multiple production frontend projects (tailgating detection, 3D building viewer, invoice management, NLP tooling) under the CORELIA umbrella
  - Collaborate daily with multicultural, cross-functional teams in a corporate European environment

- **Front-End Developer** (Feb 2025 - Nov 2025) - **NedSwiss** (Remote, Switzerland)
  - Develop and maintain web application features for cross-regional operations
  - Collaborate daily with multicultural, cross-functional teams in a corporate European environment

- **Frontend Leader** (Aug 2023 - Jun 2025) - **GDSC – Shorouk Academy** (Shorouk City)
  - Led the frontend track for Google Developer Student Club, running workshops and hands-on project sessions for 50+ students
  - Mentored developers in React, Next.js, TypeScript, and modern UI architecture patterns

### Technical Skills
- **Primary:** React, Next.js, TypeScript, JavaScript (ES6+), Redux Toolkit, Zustand, TanStack Query
- **Secondary:** Python, FastAPI, Three.js / React Three Fiber, Prisma ORM, PostgreSQL, Docker
- **Domain:** Enterprise web applications, CRM systems, real-time dashboards, 3D visualization, NLP tooling, e-learning platforms
- **Software:** Git, Vite, Turbopack, Supabase, Stripe, Paymob, SignalR, HuggingFace, Label Studio, Figma

### Certifications
<!-- List relevant certifications with dates -->
- Currently building practical experience through real-world projects, freelance work, and leadership roles.

### Publications
<!-- List peer-reviewed publications, if any -->
- Contributor and maintainer of Turjuman, an open-source AI-powered document translation platform.

### Awards
- **Finalist / Winner** - WE Innovative Hackathon (2026) - CyrusLearn Interactive Learning Platform

### Behavioral Profile
- **Proactive and self-driven learner** - Strong problem-solving mindset
- **Detail-oriented** - Maintaining focus on the bigger picture
- **Collaborative team player** - Leadership experience in team settings
- **Adaptable** - Thrives with new technologies and fast-changing environments
- **Strengths:** Frontend development with React/Next.js, UI/UX awareness, performance optimization & SEO, team leadership & mentoring, rapid prototyping, AI integration into web apps
- **Growth areas:** Advanced software architecture & system design, security best practices, backend scalability & distributed systems, engineering management & stakeholder communication
- **Thrives in:** Collaborative/innovative team culture, product-focused environments where UX matters, teams encouraging ownership and initiative, fast-paced startups or tech-driven companies

### What Excites You
- Building products that solve real business problems
- Creating intuitive and high-performance user experiences
- Integrating AI capabilities into applications
- Working on SaaS platforms and scalable systems
- Leading projects from idea to production
- Learning emerging technologies and applying them practically

### Target Sectors
- **Software Development & SaaS:** Modern web applications, CRM platforms
- **Artificial Intelligence & Automation:** AI-integrated tools and dashboards
- **CRM and Business Management Platforms:** Enterprise workflow solutions
- **E-commerce:** Online retail and payment systems
- **EdTech:** Interactive learning platforms
- **FinTech:** Payment gateways and financial tools
- **Technology Startups:** Early-stage product development
- **Digital Transformation Solutions:** Enterprise modernization

### Deal-breakers
- Roles with little or no learning opportunities
- Toxic or non-collaborative work environments
- Positions with no growth or career progression path
- Teams resistant to modern development practices
- Roles focused solely on maintenance with minimal product impact

## Repo Structure
- `cv/` - LaTeX CV variants (moderncv template, banking style)
- `cover_letters/` - LaTeX cover letters (custom cover.cls template)
- `.claude/skills/` - AI skill definitions for the application workflow
- `.agents/skills/` - Job search CLI tools

## Workflow for New Job Applications
1. User provides a job posting (URL or text)
2. **Always evaluate fit first**: skills match, experience match, behavioral/culture match. Present this assessment to the user before proceeding.
3. If good fit: create targeted CV (`cv/main_<company>.tex`) and cover letter (`cover_letters/cover_<company>_<role>.tex`)
4. **Verify both documents** (see Verification Checklist below)
5. Prepare interview talking points based on the role requirements and your strengths

**Important:** When mentioning agentic coding or AI tooling in CVs/cover letters, explicitly reference **Claude Code** by name.

## Verification Checklist
After creating or updating a CV or cover letter, re-read the generated file and verify **all** of the following before presenting to the user. Report the results as a pass/fail checklist.

### Factual accuracy
- [ ] All claims match actual profile (CLAUDE.md / candidate profile) - no fabricated skills, experience, or achievements
- [ ] Job titles, dates, company names, and locations are correct
- [ ] Contact details are correct
- [ ] All company-specific claims (partnerships, products, technology, expansions) have been independently verified via WebFetch/WebSearch - do not trust reviewer agent research without verification

### Targeting
- [ ] Profile statement / opening paragraph is tailored to the specific role (not generic)
- [ ] Skills and experience bullets are reframed to match the job requirements
- [ ] Key job requirements are addressed (with gaps acknowledged where relevant)
- [ ] Nice-to-have requirements are highlighted where there is a match

### Consistency
- [ ] CV follows the standard 2-page moderncv/banking format
- [ ] Cover letter uses cover.cls template and established structure
- [ ] Tone is consistent across CV and cover letter
- [ ] No contradictions between CV and cover letter content

### Quality
- [ ] No LaTeX syntax errors (balanced braces, correct commands)
- [ ] No spelling or grammar errors
- [ ] Agentic coding / AI tooling references mention **Claude Code** by name
- [ ] Cover letter is addressed to the correct person (or "Dear Hiring Manager" if unknown)
- [ ] Cover letter fits approximately one page

### Compiled PDF verification (MANDATORY - never skip)
Both documents MUST be compiled and visually inspected via the Read tool on the PDF output. "Looks fine in the .tex" is not acceptable - LaTeX page-break decisions are unpredictable. Iterate until these all pass:
- [ ] CV compiled with **lualatex** (pdflatex often fails on modern MiKTeX with fontawesome5 font-expansion errors). Cover letter compiled with **xelatex** (cover.cls requires fontspec).
- [ ] **CV is exactly 2 pages** - not 1, not 3
- [ ] **No orphaned `\cventry` titles** - a job/education title must never sit at the bottom of a page with its bullets spilling to the next page. Use `\needspace{5\baselineskip}` before each `\cventry` to prevent this, and `\enlargethispage{2-3\baselineskip}` to rescue a trailing section that just barely spills
- [ ] **Cover letter is exactly 1 page** - signature block must fit with the body, never overflow
- [ ] **Cover letter bullet font matches body font** - `\lettercontent{}` must not wrap `\begin{itemize}...\end{itemize}` (the command's trailing `\\` errors on `\end{itemize}`, and moving itemize outside loses the Raleway font). Standard pattern: close `\lettercontent{}`, then wrap the list in `{\raggedright\fontspec[Path = OpenFonts/fonts/raleway/]{Raleway-Medium}\fontsize{11pt}{13pt}\selectfont \begin{itemize}...\end{itemize}\par}`
