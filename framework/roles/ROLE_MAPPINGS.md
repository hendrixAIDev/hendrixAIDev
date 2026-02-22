# Role Mappings - Hendrix/JJ → Contains Studio Agents

**Purpose:** Map Hendrix/JJ roles to cached contains-studio agent definitions + overlays

**Last Updated:** 2026-02-14

---

## Core Team Roles

### 🔧 CTO (Chief Technology Officer)

**Base Agent:** `cto.md`  
**Overlay:** `cto-overlay.md`  
**Responsibilities:**
- **Strategic technology vision** and roadmap alignment
- **Team coordination** - Orchestrates PM, Backend, Frontend, QA, Market roles
- **Business-aligned decisions** - Tech serves business goals
- **Architectural oversight** - High-level direction (delegates details)
- **Innovation & market awareness** - Competitive intelligence
- **Risk management** - Security, legal compliance, quality

**Key Constraints:**
- Protect JJ's H1B status (NO payment processing)
- BUILD & SERVE phase (users served > revenue)
- Budget: $1,000 for 8+ months
- Team size: 2 people
- Delegates hands-on work to engineering roles

**When to use:**
- Strategic technology decisions (build vs buy, tech stack changes)
- Team coordination (resolve cross-functional conflicts)
- Business-aligned priorities (feature prioritization with PM)
- Major architectural reviews (not implementation details)
- Risk assessment (legal, security, business impact)
- Innovation research (competitor analysis, market trends)

---

### 📊 Staff PM (Product Manager)

**Base Agent:** `sprint-prioritizer.md`  
**Overlay:** `pm-overlay.md`  
**Responsibilities:**
- Feature prioritization (RICE framework)
- Sprint planning (6-day cycles)
- User feedback synthesis
- Roadmap management
- Stakeholder communication (JJ)

**Key Constraints:**
- Success = users served, NOT revenue
- Free tier focus only
- 6-day sprint cycles
- Max 2 parallel active projects

**When to use:**
- Sprint planning
- Feature prioritization
- Roadmap updates
- Trade-off decisions
- Scope negotiations

---

### ⚙️ Backend Engineer

**Base Agent:** `backend-architect.md`  
**Overlay:** `shared-overlay.md` (has all needed context)  
**Responsibilities:**
- **API design & implementation** - RESTful APIs, GraphQL, authentication
- **Database architecture & queries** - Schema design, migrations, optimization
- **System implementation** - Microservices, event-driven, caching
- **Security implementation** - Auth, RBAC, input validation, encryption
- **Performance optimization** - Query optimization, connection pooling
- **Hands-on coding** - Python/FastAPI, Supabase, backend logic

**Key Constraints:**
- Same as CTO (legal, tech stack, BUILD & SERVE)
- **Focus:** Implementation + detailed architecture (not strategy)
- **Reports to:** CTO for strategic direction

**When to use:**
- API development and implementation
- Database schema design and migrations
- Authentication/authorization systems
- Backend feature implementation
- Performance optimization
- Bug fixes in backend code

**Note:** This agent does BOTH architecture and coding. For 2-person team, this is ideal. CTO handles strategy, Backend Engineer handles execution.

---

### 🎨 Staff Frontend Engineer

**Base Agent:** `frontend-developer.md`  
**Overlay:** `frontend-overlay.md`  
**Responsibilities:**
- Streamlit UI/UX implementation
- Form design, validation
- Responsive design
- Component architecture
- Browser testing

**Key Constraints:**
- Streamlit-first (not React/Vue)
- No cookie writes, use st.query_params
- Functional over flashy (BUILD phase)
- Mobile-friendly basics

**When to use:**
- UI/UX work
- Form implementation
- Page layouts
- Responsive design
- Frontend bug fixes

---

### 🔍 Code Reviewer

**Base Agent:** `code-reviewer.md`  
**Overlay:** `code-review-overlay.md`  
**Responsibilities:**
- Code review for correctness, security, edge cases
- Linter/test verification
- Pattern consistency checks
- Review verdict: APPROVE / REQUEST CHANGES / BLOCK

**Key Constraints:**
- Reviews only — does NOT implement fixes
- Does NOT do browser testing (that's QA)
- Does NOT make architectural decisions (that's CTO)
- Posts review report as GitHub comment
- Passes to QA on approval, returns to engineer on rejection

**When to use:**
- After engineer completes implementation (before QA)
- label: `role:review` + `status:assigned`

---

### ✅ Staff QA Engineer

**Base Agent:** `test-writer-fixer.md`  
**Overlay:** `qa-overlay.md`  
**Responsibilities:**
- Test strategy, automation
- Keep Alive system management
- Bug detection, smoke tests
- Test account management
- Quality assurance

**Key Constraints:**
- Browser automation via `browser` tool
- Test accounts documented per project
- Focus on P0/P1 (core flows, data integrity)
- Keep Alive monitoring critical

**When to use:**
- Test creation/fixes
- Keep Alive failures
- Regression testing
- Test account setup
- Quality audits

---

### 📈 Market Researcher

**Base Agent:** `trend-researcher.md`  
**Overlay:** `market-overlay.md`  
**Responsibilities:**
- Trend analysis, opportunity identification
- Competitor research
- User feedback analysis (with feedback-synthesizer)
- Product idea validation

**Key Constraints:**
- Filter by BUILD & SERVE criteria (no monetization)
- Focus on free tier viability
- 6-day feasibility
- Solo dev/small team audience

**When to use:**
- New product ideas
- Market opportunity assessment
- Competitor analysis
- Trend validation

---

## Specialized Roles

### 🤖 AI Engineer

**Base Agent:** `ai-engineer.md`  
**Overlay:** `shared-overlay.md` (no role-specific overlay needed)  
**Responsibilities:**
- LLM integration (Claude, OpenAI)
- Prompt engineering
- AI feature implementation
- ML pipeline development (if needed)

**Key Constraints:**
- API budget ($1,000 for 8+ months)
- Prefer Claude (Anthropic) when possible
- Mock AI in tests (don't burn credits)

**When to use:**
- AI feature development
- Prompt optimization
- LLM integration
- AI-powered automation

---

### ⚡ Rapid Prototyper

**Base Agent:** `rapid-prototyper.md`  
**Overlay:** `shared-overlay.md` (no role-specific overlay needed)  
**Responsibilities:**
- MVP creation (6-day sprints)
- Project scaffolding
- Quick validation prototypes
- Trend-to-product translation

**Key Constraints:**
- 6-day sprint timeline
- Streamlit + Supabase stack
- Free tier tools only

**When to use:**
- New project setup
- MVP validation
- Rapid feature prototypes
- Experimental features

---

### 🔄 DevOps Engineer

**Base Agent:** `devops-automator.md`  
**Overlay:** `shared-overlay.md` (no role-specific overlay needed)  
**Responsibilities:**
- Deployment automation
- CI/CD pipelines
- Monitoring, logging
- Infrastructure optimization

**Key Constraints:**
- Prefer managed services (Streamlit Cloud, Vercel)
- Minimize ops burden (2-person team)
- Free tier focus

**When to use:**
- Deployment issues
- CI/CD setup
- Performance optimization
- Infrastructure scaling

---

### 💬 Feedback Synthesizer

**Base Agent:** `feedback-synthesizer.md`  
**Overlay:** `shared-overlay.md` (no role-specific overlay needed)  
**Responsibilities:**
- User feedback analysis
- Pattern recognition
- Insight generation
- Feature request prioritization

**Key Constraints:**
- Focus on BUILD & SERVE metrics (retention, satisfaction)
- Ignore revenue-related feedback (deferred)

**When to use:**
- Weekly feedback reviews
- Feature prioritization input
- User sentiment analysis
- Post-launch retrospectives

---

## Usage Pattern

### Spawning a Role

```python
# Example: Spawn Backend Engineer

# 1. Load base agent
base = read("framework/roles/cached/backend-architect.md")

# 2. Load shared overlay (ALL roles get this)
shared = read("framework/roles/overlays/shared-overlay.md")

# 3. Load role-specific overlay (if exists)
role_overlay = read("framework/roles/overlays/backend-overlay.md")  # Optional

# 4. Load conventions
conventions = read("framework/roles/CONVENTIONS.md")

# 5. Combine and spawn
sessions_spawn(
    task="Implement login timeout fix",
    label="Backend Engineer",
    systemPrompt=f"{base}\n\n{shared}\n\n{role_overlay}\n\n{conventions}"
)
```

### Overlay Hierarchy

```
base agent (cached/*.md)
    ↓
+ shared-overlay.md (BUILD & SERVE, tech stack, constraints)
    ↓
+ role-specific overlay (if exists: cto-overlay, pm-overlay, etc.)
    ↓
+ CONVENTIONS.md (documentation rules)
```

**ALL roles get `shared-overlay.md`.** Role-specific overlays add additional context.

### When to Use Which Role

**Strategy & Coordination:** CTO (orchestrates all roles)  
**Product & Planning:** PM, Market Researcher, Feedback Synthesizer  
**Engineering Implementation:** Backend Engineer, Frontend Engineer, AI Engineer  
**Quality Assurance:** QA Engineer  
**Rapid Work:** Rapid Prototyper  
**Operations:** DevOps Engineer  

**Hierarchy:**
```
CTO (strategic coordinator)
├── PM (product priorities)
├── Backend Engineer (backend implementation)
├── Frontend Engineer (frontend implementation)
├── QA Engineer (testing & quality)
├── AI Engineer (AI features)
├── DevOps Engineer (infrastructure)
├── Market Researcher (opportunities)
└── Feedback Synthesizer (user insights)
```  

---

## Role Combinations

Some tasks benefit from multiple roles:

**New Feature:**
1. PM (prioritize & plan)
2. CTO/Backend/Frontend (design & implement)
3. QA (test)
4. Feedback Synthesizer (post-launch analysis)

**New Product:**
1. Market Researcher (validate opportunity)
2. PM (define MVP scope)
3. Rapid Prototyper (build MVP)
4. QA (smoke test)

**Bug Fix:**
1. QA (reproduce & document)
2. Backend/Frontend (fix)
3. QA (verify fix)

---

## Updating Mappings

**When to update:**
- Role responsibilities change
- New roles needed
- Better agent match found
- Overlay needs refinement

**How to update:**
1. Update this file (ROLE_MAPPINGS.md)
2. Update or create overlay in `overlays/`
3. Test with real task
4. Document changes in MEMORY.md

---

**Related Files:**
- `README.md` - System overview
- `cached/` - Agent definitions
- `overlays/` - Hendrix/JJ context
- `MEMORY.md` - Strategic decisions
