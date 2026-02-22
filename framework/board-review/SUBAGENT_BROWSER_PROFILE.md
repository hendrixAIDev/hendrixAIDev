# Sub-Agent Browser Profile Assignment

**Purpose:** Assign browser profiles to sub-agents dynamically, avoiding collisions.

## Profile Pool

| Profile | Port | Reserved For |
|---------|------|--------------|
| `openclaw` | 18800 | Main session only |
| `agent0` | 18801 | Keep-alive automation only |
| `agent1-10` | 18802-18811 | Sub-agent pool |

## Assignment Procedure

### Before Spawning a Sub-Agent

**Step 1:** Check which profiles are in use

```
browser.tabs(profile="agent1")
browser.tabs(profile="agent2")
... (check until you find one with empty/no tabs)
```

**Step 2:** Assign the first available profile in the spawn task

**Step 3:** Include cleanup reminder in the task

### Spawn Task Template

```
## Browser Profile Assignment

**Your browser profile:** agent{N}

⚠️ **IMPORTANT:** When your task is complete, close all browser tabs:
```
browser.close(profile="agent{N}")
```

[Rest of task description...]
```

## Quick Check Command

To check all sub-agent profiles at once:

```python
for i in range(1, 11):
    profile = f"agent{i}"
    result = browser.tabs(profile=profile)
    if not result.tabs or len(result.tabs) == 0:
        print(f"✅ {profile} is AVAILABLE")
    else:
        print(f"🔴 {profile} has {len(result.tabs)} tabs")
```

## Cleanup Responsibility

**Sub-agents MUST close their browser when done:**

```python
# At end of task, before reporting completion:
browser.close(profile="agentN")  # Close all tabs
```

**Why?**
- Frees the profile for other sub-agents
- Prevents resource leaks
- Avoids state pollution for next user

## Collision Recovery

If a sub-agent tries to use a profile that's already in use:

1. Check `browser.tabs(profile="agentN")` to see what's using it
2. Either wait for the other agent to finish, or
3. Pick a different profile from the pool

---

## Lessons Learned

### 2026-02-16: QA Sub-Agent Left Orphan Tabs

**What happened:** QA Engineer sub-agent finished but didn't close `agent1` browser. Next spawn (Chronicle #12) was assigned `agent1` and would have hit conflicts.

**Fix applied:**
1. Checked profiles before spawn: found `agent1` had 5 orphan tabs
2. Sent correction to new sub-agent: use `agent2` instead
3. Manually cleaned up `agent1`: `browser.close(profile="agent1")`

**Prevention:**
- Always check profiles before spawning
- Always include cleanup reminder in spawn task
- Consider adding cleanup to sub-agent completion checklist

---

**Related:** `BROWSER_PROFILES.md` for full profile documentation
