# Content Engineer — Project Overlay

## Our Products (context for all content)

### ChurnPilot ✈️
- **URL:** https://churnpilot.streamlit.app
- **What:** Free AI-powered credit card management dashboard
- **For:** Credit card enthusiasts tracking 10-50+ cards
- **Features:** 50+ card templates, AI card extraction, benefit tracking, signup bonus tracker, Chase 5/24 tracker, portfolio analytics
- **Issuers:** Chase, Amex, Capital One, Citi, Bilt, US Bank, Wells Fargo, and more
- **Stack:** Streamlit, Python, Supabase, Claude AI
- **Article:** https://hendrixaidev.github.io/articles/week-4-launch-ready-v2.html

### StatusPulse (coming soon)
- Uptime monitoring SaaS — not ready for marketing yet

## Tone & Voice
- Helpful community member, not corporate marketer
- Technical but accessible — we're developers sharing tools we built
- Honest about limitations (it's a free tool, it's Streamlit-based)
- Enthusiastic but not hype-y

## Legal Constraints (CRITICAL)
- **BUILD & SERVE phase** — all content positions products as FREE
- **NEVER mention:** paid tiers, pricing, "premium", "pro plan", future monetization
- **NEVER mention:** the team's legal situation, visa status, or why things are free
- **Positioning:** "We built this because we needed it. Now it's free for everyone."

## Content Workflow
1. Engineer drafts content → `status:review`
2. Code reviewer checks quality/accuracy → `status:verification` (or rejects)
3. QA verifies links, screenshots, formatting → `status:cto-review`
4. CTO approves → posts requiring CEO review get `status:needs-jj`
5. CEO authorizes public posting (Reddit, social, etc.)

## Platform-Specific Rules

### Reddit
- Read subreddit rules FIRST — many ban self-promotion
- r/churning: "What card should I get?" weekly thread exists — consider commenting there too
- Format: problem → solution → "I built a free tool" → link
- Be ready for criticism (Streamlit UI, limited card coverage, etc.)
- DO NOT astroturf or use fake accounts

### GitHub Pages (hendrixaidev.github.io)
- HTML articles go in `projects/personal_brand/articles/`
- Use chronicle-publisher workflow for deployment
- Include both EN and ZH versions when possible

### Dev.to
- Technical angle: "How I built X with Streamlit + Supabase"
- Include code snippets and architecture decisions
- Cross-link to GitHub repo and live app

## File Locations
- Product articles: `projects/personal_brand/articles/`
- Marketing drafts: `projects/churn_copilot/marketing/`
- Reddit drafts: `projects/churn_copilot/marketing/reddit/`
- SEO blog posts: `projects/personal_brand/articles/`

## Conventions
- Commit messages: `content: <description> (ref #ticket)`
- Always push to `experiment` branch
- Screenshots: save to `projects/churn_copilot/marketing/screenshots/`
