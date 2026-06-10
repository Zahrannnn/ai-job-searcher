# Interview Prep — ServiceTitan (Web Developer, Web Team)

## About the company
- **ServiceTitan** — #1 software for home and commercial trades (HVAC, plumbing, electrical, roofing, landscaping, etc.)
- Four flagship marketing sites: **servicetitan.com**, **youraspire.com**, **convex.com**, **fieldroutes.com**
- The **Web Team** is responsible for these four sites — they sit on the pipeline generation side, not product engineering
- Compensation: $94,700 – $142,100 CAD for Canada; equity + bonus + benefits
- "Anywhere in the World" remote

## Role in one sentence
> Build, optimize, and maintain four high-traffic marketing websites with strong attention to accessibility, performance, and motion design — partnering with design, marketing, and QA.

## Why you, why ServiceTitan — 30-second pitch
> "I build marketing-grade web experiences on Next.js / TypeScript / Tailwind, and the Web Team role is exactly the kind of work I want to do at scale. At NedSwiss I built a high-performance multilingual marketing site with GSAP and Lenis, holding 60fps, and shipped a multilingual admin/staff CRM dashboard on the same Next.js codebase — so I'm comfortable owning the full web-team surface, not just landing pages. I prioritize accessibility (WCAG 2.1), SEO, and Core Web Vitals as defaults, and I use AI tools like Claude Code actively in my dev workflow. My recent stack is React/Next.js with limited production Vue, so I'd prioritize ramping on Vue and Contentful in the first two weeks — the underlying patterns transfer directly."

## Key talking points
1. **Marketing-site craft, not just product UI** — NedSwiss multilingual marketing site (GSAP / Lenis / Framer Motion), 60fps, i18n (next-intl), bundle optimization with Turbopack. This is the *exact* shape of the work.
2. **Accessibility and SEO as defaults** — semantic HTML, ARIA, WCAG 2.1, on-page SEO, structured content. You don't treat these as polish.
3. **Static-site generation and Core Web Vitals** — Next.js 15/16, SSG/SSR, image and bundle optimization, performance budgets.
4. **AI in the dev workflow** — Claude Code, Gemini, HuggingFace. You're already a power user.
5. **Cross-functional remote collaboration** — RICOH daily with multicultural design/product/marketing/QA across time zones.

## Gaps to acknowledge honestly
- **Vue.js** — no production experience. The role lists React *or* Vue. Acknowledge: "I would ramp on Vue in the first two weeks — the patterns transfer directly from React/Next."
- **Headless CMS (Contentful or similar)** — no direct production experience. Acknowledge: "I've shipped content-driven UIs and API integrations; Contentful or any headless CMS pattern is a short ramp."
- **Node/Express** — basic only. Acknowledge: "I use Node-adjacent tooling daily; Express I can pick up quickly."

**Frame gaps as "trainable in 2 weeks" not "I lack this."**

## Likely technical questions + how to answer

| Q | How to answer |
|---|---|
| "How do you balance performance, accessibility, and SEO on a marketing site?" | Walk through a concrete example: LCP <2.5s via image optimization and preloading, CLS <0.1 via explicit aspect ratios, semantic HTML + ARIA, alt text, focus management, structured data, sitemap/robots. |
| "Tell me about a marketing site you've shipped and what made it successful." | NedSwiss marketing site — multilingual, GSAP/Lenis/Framer Motion, 60fps across devices, i18n with next-intl, Turbopack. What was the engagement / conversion outcome (or what you would measure)? |
| "How do you debug a slow page?" | Lighthouse + WebPageTest + RUM (CrUX, Vercel Analytics). Look at LCP/INP/CLS, identify the bottleneck (image / JS / font / third-party), fix at the right layer. |
| "How would you integrate a headless CMS into a Next.js site?" | Contentful / Sanity as a content source, fetched at build (SSG) or per request (ISR/SSR), with TypeScript types generated from the schema, preview mode for editors. |
| "Tell me about a time you had to ship under a marketing deadline." | Use STAR — pick a real example, talk about scope cuts, what's "must-ship" vs "polish later", how you communicated tradeoffs. |
| "WCAG — how do you actually implement it?" | Walk through concrete: semantic landmarks, skip links, focus rings, ARIA only when needed, color contrast 4.5:1, keyboard nav for all interactive elements, screen reader testing (NVDA/VoiceOver), axe / Lighthouse audits. |

## Behavioral (STAR) — pick 2-3 to prepare
- **Cross-functional collaboration** — NedSwiss or RICOH with design + marketing + QA
- **Polish under deadline** — NedSwiss marketing site launch
- **AI-augmented delivery** — using Claude Code in your workflow, what you ship faster
- **Failure / rollback** — a real production incident and what you learned
- **Initiative / ownership** — when you saw a problem and fixed it before being asked

## Questions to ask them
- What's the split between "new builds" and "iteration/optimization" for the Web Team?
- Which of the four marketing sites is currently the highest-priority pipeline driver?
- How does the Web Team collaborate with Brand / Marketing on copy and design — what's the handoff?
- How is success measured for a Web Developer on this team — conversion lift, Core Web Vitals, time-to-publish?
- What CMS / content workflow do the editors use today, and is there a planned migration?
- How does the team approach AI tooling in the dev workflow today (Copilot, Claude Code, etc.)?
- Is there a roadmap toward more interactive / product-grade web experiences, or is the role firmly marketing?

## Red flags to watch for
- "Mostly maintenance / bugfix" (contradicts your growth interests)
- "No AI tooling allowed in the workflow" (contradicts your current practice)
- "Pixel-perfect only — no engineering decisions" (underutilizes your full-stack ability)
