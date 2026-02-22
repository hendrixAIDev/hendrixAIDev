# GitHub Issue Screenshot Upload - How To

**Created:** 2026-02-16  
**Context:** Investigating how to programmatically attach screenshots to GitHub issues

---

## TL;DR

**❌ What doesn't work:**
- `gh` CLI has no file upload command
- Browser automation hits native file dialogs (can't automate)

**✅ What works:**
- **Manual:** Drag-and-drop in GitHub web interface
- **Manual:** Paste image directly in comment box (Cmd+V)
- **Semi-automated:** Upload to image host → link in markdown

---

## Investigation Results

### gh CLI Limitations

```bash
gh issue create --help  # No --attach or --file flag
gh issue comment --help # Only --body and --body-file (text only)
```

**Verdict:** The GitHub CLI (`gh`) does **not support file uploads**. It only handles text content.

### Browser Automation Limitations

Attempted workflow:
1. ✅ Open issue page in browser
2. ✅ Click "Paste, drop, or click to add files" button
3. ❌ **Native file picker dialog opens** - browser automation can't interact with OS-level dialogs

**Technical detail:**
```javascript
browser.upload(inputRef="e407", paths=["..."])
// Error: Node is not an HTMLInputElement (it's a button)
```

The button triggers a native file picker, which is outside the browser's DOM and inaccessible to CDP (Chrome DevTools Protocol).

---

## Working Approaches

### Option 1: Manual Drag-and-Drop (Recommended for now)

**Steps:**
1. Open issue in browser: `https://github.com/owner/repo/issues/N`
2. Click in comment box
3. Drag image file from Finder → drop in comment box
4. Image uploads automatically, shows as markdown: `![filename](https://...)`
5. Click "Comment"

**Pros:**
- Fast (2-3 seconds)
- Reliable
- No intermediate steps

**Cons:**
- Requires human interaction

---

### Option 2: Paste from Clipboard

**Steps:**
1. Copy image to clipboard (Cmd+C in Preview/Finder)
2. Open issue comment box
3. Paste (Cmd+V)
4. Image uploads automatically

**Pros:**
- Fastest method
- Works from any image source

**Cons:**
- Requires human interaction
- Clipboard management can be tricky

---

### Option 3: Image Hosting + Markdown Link

**Workflow:**
1. Upload image to hosting service (imgur, imgbb, etc.)
2. Get direct image URL
3. Add to GitHub issue via `gh`:
   ```bash
   gh issue comment <issue> --body "Screenshot: ![desc](https://imgur.com/abc123.png)"
   ```

**Pros:**
- Fully automatable
- No browser needed

**Cons:**
- Requires external service
- Extra step
- Image might expire (depending on host)

---

## Recommended Workflow for OpenClaw

### When Creating Issues with Screenshots

**Step 1: Create issue via CLI**
```bash
gh issue create --repo owner/repo \
  --title "Issue title" \
  --body "Issue description" \
  --label "bug,priority:medium"
```

**Step 2: Note screenshot location in comment**
```bash
gh issue comment <issue-number> --body "Screenshot available at: [local-path] or [Slack #channel]"
```

**Step 3: Manual upload (human step)**
- Ask JJ to:
  1. Open the issue URL
  2. Drag-and-drop the screenshot from the specified location
  3. Comment confirms upload

**Alternative: Use message tool**
Send screenshot via Slack/Discord, then reference it:
```bash
gh issue comment <issue> --body "Screenshot posted in Slack #jj-hendrix [timestamp]"
```

---

## Future Automation Options

### Potential Solutions (not yet implemented):

1. **GitHub API Asset Upload**
   - GitHub has an "asset upload" API for releases
   - Unclear if this works for issue comments
   - Needs investigation

2. **Headless Browser with File Dialog Automation**
   - Use tools like `xdotool` (Linux) or AppleScript (macOS)
   - Automate the OS-level file picker
   - Complex, platform-specific

3. **Self-hosted Image CDN**
   - Run our own image hosting
   - Fully controlled, no expiration
   - Requires infrastructure

4. **GitHub Gists**
   - Upload image to secret gist
   - Link in issue
   - Uses GitHub's infrastructure

---

## Security Note

The browser `upload` action requires files to be in `/tmp/openclaw/uploads` directory. Files outside this directory are blocked for security.

**Example:**
```bash
# Copy to uploads dir first
mkdir -p /tmp/openclaw/uploads
cp /path/to/screenshot.png /tmp/openclaw/uploads/

# Then upload via browser
browser.upload(paths=["/tmp/openclaw/uploads/screenshot.png"])
```

---

## Current Best Practice

**For now:** Create issues via CLI, note where screenshots are available, and request manual upload via web interface.

**Workflow:**
1. `gh issue create` → get issue number
2. Send screenshot via Slack with issue link
3. JJ drags screenshot from Slack → GitHub issue

This hybrid approach balances automation (CLI) with practicality (manual image upload).

---

**Related:**
- GitHub CLI docs: https://cli.github.com/manual/
- GitHub API: https://docs.github.com/en/rest
- Browser automation: `framework/board-review/SUBAGENT_BROWSER_PROFILE.md`
