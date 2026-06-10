# Interview Prep — Maqsam (Software Engineer)

## About the company
- **Maqsam** — leading Arabic AI-powered Contact Center Solution in MENA
- Parent: **Labotic OÜ** (Estonia, founded 2019)
- 80+ team members, ex-Google / Amazon / Expedia / Verizon Wireless
- Products: Customer Service Software, AI Agent, APIs, integrations
- Industries served: Retail, Transportation, Education, Banking, Real Estate, Healthcare, Hospitality, BPOs, Government, SMBs, Enterprise
- Phone numbers: +966 (KSA), +971 (UAE), +962 (Jordan)

## Why you, why Maqsam — 30-second pitch
> "I'm a Software Engineer with production experience in AI-integrated web apps and multilingual SaaS dashboards. I'm a native Arabic speaker, and I maintain Turjuman, an open-source Arabic AI document translation platform — so the language and the AI focus that define Maqsam's edge are mine. At RICOH Europe, I shipped an Arabic NLP keyword-extraction interface inside an enterprise document pipeline. At NedSwiss, I built a multilingual CRM dashboard that's structurally similar to contact-center operations surfaces. I want to bring that combination — Arabic-first AI + SaaS dashboard craft — to Maqsam."

## Key talking points
1. **Arabic AI is your edge** — Turjuman (your open-source Arabic AI translation platform) + the RICOH Arabic NLP work is a *unique* portfolio fit. Most candidates will not have shipped Arabic AI features in production.
2. **CRM/contact-center surface experience** — NedSwiss multilingual admin/staff CRM dashboard is a near-direct analog. Highlight: data tables, chart analytics, role-based navigation, i18n.
3. **AI tooling fluency** — Gemini, HuggingFace Transformers, VAPI voice AI, Label Studio. Mention you actively use Claude Code in your dev workflow.
4. **MENA + European cross-cultural fluency** — RICOH (European corporate), Maqsam (MENA AI) — you can bridge both worlds.
5. **Full-stack capability** — even though the role is "backend SWE", your Python/FastAPI/Prisma/PostgreSQL work means you can move fluidly across the stack.

## Likely technical questions + how to answer

| Q | How to answer |
|---|---|
| "How would you design an Arabic-first contact center UI?" | RTL-aware component library, server-rendered with Next.js i18n (next-intl), accessible (WCAG 2.1), responsive, real-time updates via WebSocket or SignalR. Reference your RICOH Arabic NLP work. |
| "How do you integrate an LLM into a production web app?" | Discuss Gemini integration patterns: prompt templating, response validation, fallback handling, latency budgets, server-side proxying to keep API keys out of client bundle. |
| "Tell me about a time you debugged a complex issue." | Use STAR: pick the real-time tailgating detection work at RICOH — MJPEG streaming, race conditions in the canvas/frame pipeline, how you traced it via browser devtools and React profiler. |
| "How do you ship features in a fast-growing SaaS?" | Feature flags, phased rollouts, monitoring/observability, close loop with product/QA/design, document decisions in ADRs. |
| "What's your experience with CRM or contact-center products?" | NedSwiss CRM dashboard — features, scale, role-based access, data tables at scale, chart libraries. Be specific about what you owned end-to-end. |
| "How would you handle Arabic NLP failures?" | Discuss tokenization issues, dialect variance (MSA vs Egyptian vs Gulf), diacritics, code-switching. Reference your Turjuman work and the RICOH Arabic NLP pipeline. |

## Behavioral (STAR) — pick 2-3 to prepare
- **Leadership** — GDSC Frontend Leader (50+ students, ran workshops, mentored on React/Next)
- **Cross-functional collaboration** — RICOH multicultural European teams
- **AI-augmented delivery** — using Claude Code + Gemini + HuggingFace in real workflows
- **Conflict / disagreement** — design vs engineering tradeoffs at NedSwiss
- **Failure** — a real production bug you shipped and how you fixed it

## Questions to ask them
- What's the current team structure for the Web/Product engineering org, and where does this role sit?
- How is the Arabic NLP capability built — is it proprietary, or does it wrap a foundation model?
- What's the deployment story for the contact center platform (cloud region, latency requirements)?
- How does the team approach RTL and Arabic UX specifically?
- What does success look like in the first 90 days for this role?
- How does Maqsam balance speed of shipping with code quality as the team scales?

## Red flags to watch for
- "Pure backend only — no UI" (would mismatch your strength)
- "No Arabic-speaking engineers on the team" (risk for an Arabic AI product)
- "Just maintain legacy code" (contradicts your growth interests)
