# Framework: Role-Based Agent System

**Purpose:** Leverage community-built agent definitions with Hendrix/JJ-specific context overlays.

**Strategy:** Option B (Cached Reference + Overlay)
- Cache agent definitions from contains-studio/agents repo
- Add Hendrix/JJ context overlays for our specific needs
- Update cache when needed, not on every dispatch

**Last Updated:** 2026-02-14

---

## Overlay Hierarchy

**All roles use this pattern:**

```
base agent (cached/*.md)
    ↓
+ shared-overlay.md (BUILD & SERVE, tech stack, constraints) ← ALL ROLES
    ↓
+ role-specific overlay (if exists) ← Some roles only
    ↓
+ CONVENTIONS.md (documentation rules)
```

**`shared-overlay.md`** gives every role:
- BUILD & SERVE phase context (no monetization)
- Tech stack (Streamlit, Supabase, Python)
- Legal constraints (H1B, no payments)
- GitHub ticket workflow
- Team structure

**Role-specific overlays** (optional) add:
- `cto-overlay.md` - Board Review, team coordination
- `pm-overlay.md` - Sprint planning, prioritization
- `qa-overlay.md` - Test accounts, Keep Alive
- `frontend-overlay.md` - Streamlit specifics
- `market-overlay.md` - Research focus

---

## Directory Structure

```
framework/roles/
├── README.md (this file)
├── ROLE_MAPPINGS.md (which roles map to which agents)
├── cached/ (agent definitions from contains-studio)
│   ├── backend-architect.md
│   ├── frontend-developer.md
│   ├── sprint-prioritizer.md
│   ├── test-writer-fixer.md
│   ├── trend-researcher.md
│   ├── ai-engineer.md
│   ├── rapid-prototyper.md
│   ├── devops-automator.md
│   └── feedback-synthesizer.md
└── overlays/ (Hendrix/JJ context additions)
    ├── cto-overlay.md
    ├── pm-overlay.md
    ├── backend-overlay.md
    ├── frontend-overlay.md
    ├── qa-overlay.md
    ├── market-overlay.md
    ├── ai-overlay.md
    └── devops-overlay.md
```

---

## How It Works

### 1. Base Definitions (cached/)

Cached agent definitions from [contains-studio/agents](https://github.com/contains-studio/agents):
- Complete agent system prompts (~500+ words each)
- Activation criteria and examples
- Tool access specifications
- Domain expertise and best practices

**Source:** https://github.com/contains-studio/agents  
**Cache Date:** 2026-02-14  
**License:** MIT (assumed - verify if using commercially)

### 2. Context Overlays (overlays/)

Hendrix/JJ-specific additions that modify base agent behavior:
- BUILD & SERVE phase constraints (no monetization)
- H1B status protection requirements
- Tech stack specifics (Supabase, Streamlit, Python)
- Active project context (ChurnPilot, StatusPulse, etc.)
- Test account locations
- Additional tool access (browser, nodes, cron)

### 3. Spawning with Combined Context

When spawning a sub-agent in a role:

```python
# Load base definition
base = read("framework/roles/cached/backend-architect.md")

# Load overlay
overlay = read("framework/roles/overlays/cto-overlay.md")

# Combine and spawn
sessions_spawn(
    task=task,
    label="CTO",
    systemPrompt=base + "\n\n--- HENDRIX/JJ OVERLAY ---\n\n" + overlay
)
```

---

## Role Mappings

See `ROLE_MAPPINGS.md` for complete mapping of Hendrix/JJ roles to cached agents.

**Quick reference:**
- **CTO** → cto + cto-overlay (strategic coordinator)
- **Backend Engineer** → backend-architect + backend-overlay (implementation)
- **Frontend Engineer** → frontend-developer + frontend-overlay
- **QA Engineer** → test-writer-fixer + qa-overlay
- **Staff PM** → sprint-prioritizer + pm-overlay
- **Market Researcher** → trend-researcher + market-overlay
- **AI Engineer** → ai-engineer + ai-overlay
- **Rapid Prototyper** → rapid-prototyper (minimal overlay)
- **DevOps Engineer** → devops-automator + devops-overlay

**Role Hierarchy:**
```
CTO (strategic) → coordinates all engineering roles
  ├── Backend Engineer (hands-on backend work)
  ├── Frontend Engineer (hands-on frontend work)
  ├── QA Engineer (testing & quality)
  └── etc.
```

---

## Updating Cached Agents

When contains-studio updates their agents:

1. Re-fetch the agent definition
2. Save to `cached/[agent-name].md`
3. Update cache date in this README
4. Review overlays for conflicts
5. Test with existing tasks

**Command:**
```bash
curl https://raw.githubusercontent.com/contains-studio/agents/main/[category]/[agent].md \
  > framework/roles/cached/[agent].md
```

---

## Creating New Overlays

When adding Hendrix/JJ context to an agent:

1. Create `overlays/[role]-overlay.md`
2. Include ONLY our specific additions:
   - BUILD & SERVE phase context
   - Legal constraints (H1B)
   - Tech stack preferences
   - Project-specific info
   - Additional tools
3. Keep overlays focused (< 500 words)
4. Document WHY each constraint exists

**Template:**
```markdown
# [ROLE] Overlay - Hendrix/JJ Context

## Strategic Context

[BUILD & SERVE phase, H1B constraints, etc.]

## Tech Stack

[Specific technologies we use]

## Active Projects

[Links to project docs]

## Additional Tools

[Tools beyond base agent definition]

## Key Constraints

[Critical rules for this context]
```

---

## Benefits of This Approach

✅ **Leverage community expertise** - 500+ word prompts, battle-tested  
✅ **Maintain our context** - Overlays ensure BUILD & SERVE compliance  
✅ **Easy updates** - Refresh cache when contains-studio improves  
✅ **Minimal maintenance** - Only update overlays when our context changes  
✅ **Clear separation** - Base knowledge vs. Hendrix/JJ specifics  
✅ **Fallback ready** - If repo disappears, we have cached copies  

---

## Related Files

- **PROJECT_STRUCTURE.md** - File organization rules (mandatory reading)
- **AGENTS.md** - Agent behavior and session context
- **MEMORY.md** - Strategic decisions and active projects
- **projects/[project]/README.md** - Project-specific documentation

---

**Next Steps:**
1. Review ROLE_MAPPINGS.md for complete role definitions
2. Read overlays to understand Hendrix/JJ context
3. Use sessions_spawn with combined prompts when dispatching work
