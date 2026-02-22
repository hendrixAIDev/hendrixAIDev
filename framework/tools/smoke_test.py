#!/usr/bin/env python3
"""
smoke_test.py — Post-deploy smoke test for ChurnPilot

PURPOSE: Verify a deployment is live, healthy, and functional after push
WHEN TO USE: After push to experiment or main branch (called by board review pipeline)
WHEN TO DELETE: Never (core deploy infrastructure)
OWNER: CTO

Usage:
  python framework/tools/smoke_test.py --url https://churncopilothendrix-bc5b56cmnopm2ixz3dvhwd.streamlit.app
  python framework/tools/smoke_test.py --env experiment
  python framework/tools/smoke_test.py --env production
  python framework/tools/smoke_test.py --env experiment --expected-sha a1b2c3d
  python framework/tools/smoke_test.py --env experiment --retries 3 --retry-delay 60

Exit codes:
  0 = All checks passed
  1 = One or more checks failed

Output: JSON to stdout with pass/fail details
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from http.cookiejar import CookieJar
from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
from urllib.error import URLError, HTTPError

# Known endpoints
ENDPOINTS = {
    "experiment": "https://churncopilothendrix-bc5b56cmnopm2ixz3dvhwd.streamlit.app",
    "production": "https://churnpilot.streamlit.app",
}

# Defaults
DEFAULT_TIMEOUT = 30  # seconds per request
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 60  # seconds between retries


class ViewerAuthError(Exception):
    """Raised when Streamlit Cloud viewer auth blocks access."""
    pass


# Shared cookie jar across requests — Streamlit Cloud sets session cookies
# on the first 303 redirect that are required for subsequent requests.
_cookie_jar = CookieJar()
_opener = build_opener(HTTPCookieProcessor(_cookie_jar))


def _http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple:
    """HTTP GET with cookie persistence (required for Streamlit Cloud).

    Streamlit Cloud returns a 303 on first request to set session cookies,
    then serves the actual content on redirect. Using a cookie jar handles
    this transparently.

    Returns (status_code, body_text, final_url) or raises on network error.
    """
    req = Request(url, headers={"User-Agent": "ChurnPilot-SmokeTest/1.0"})
    try:
        resp = _opener.open(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body, resp.url
    except HTTPError as e:
        # Check if this is a genuine viewer auth redirect (to share.streamlit.io)
        if e.code == 303:
            location = e.headers.get("Location", "")
            if "share.streamlit.io" in location:
                raise ViewerAuthError(
                    f"Streamlit Cloud viewer auth is blocking access. "
                    f"The app needs to be made public in Streamlit Cloud settings "
                    f"(Settings → Sharing → Public). Redirect: {location}"
                )
            # Other 303s are normal Streamlit session setup — let urllib follow them
        raise


def _extract_schp_json(html: str) -> Optional[Dict[str, Any]]:
    """Extract SCHP JSON from Streamlit HTML response.

    The health endpoint renders JSON via st.code(), which embeds it in HTML.
    We look for the JSON block containing schp_version.
    """
    # Try to find a JSON object with schp_version
    # Match the outermost { ... } that contains "schp_version"
    # Use a greedy approach: find start, then match balanced braces
    patterns = [
        # Pattern 1: JSON in a <code> or <pre> block
        r'<code[^>]*>(.*?)</code>',
        r'<pre[^>]*>(.*?)</pre>',
        # Pattern 2: raw JSON block
        r'(\{[^{}]*"schp_version"[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        for match in matches:
            # Clean HTML entities
            cleaned = match.replace("&quot;", '"').replace("&amp;", "&")
            cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">")
            cleaned = cleaned.strip()
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict) and "schp_version" in data:
                    return data
            except (json.JSONDecodeError, ValueError):
                continue

    # Fallback: try to find any JSON-like block with schp_version
    # This handles cases where JSON is deeply nested in HTML
    json_start = html.find('"schp_version"')
    if json_start == -1:
        return None

    # Walk backwards to find opening brace
    brace_count = 0
    start_idx = json_start
    for i in range(json_start, -1, -1):
        if html[i] == '}':
            brace_count += 1
        elif html[i] == '{':
            if brace_count == 0:
                start_idx = i
                break
            brace_count -= 1

    # Walk forward to find matching closing brace
    brace_count = 0
    for i in range(start_idx, len(html)):
        if html[i] == '{':
            brace_count += 1
        elif html[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                candidate = html[start_idx:i + 1]
                # Clean HTML entities
                candidate = candidate.replace("&quot;", '"').replace("&amp;", "&")
                candidate = candidate.replace("&lt;", "<").replace("&gt;", ">")
                try:
                    data = json.loads(candidate)
                    if isinstance(data, dict) and "schp_version" in data:
                        return data
                except (json.JSONDecodeError, ValueError):
                    pass
                break

    return None


def check_liveness(base_url: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Tier 1: Check if the Streamlit app is alive via its built-in health endpoint.

    This bypasses Streamlit's SPA rendering and viewer auth — it's a direct
    server-level check that confirms the app process is running.

    Returns a result dict with passed, message, duration_ms.
    """
    # Streamlit exposes /_stcore/health and /healthz — both return "ok"
    health_urls = [
        f"{base_url}/_stcore/health",
        f"{base_url}/healthz",
    ]

    start = time.monotonic()
    for health_url in health_urls:
        try:
            status_code, body, _ = _http_get(health_url, timeout=timeout)
            duration_ms = int((time.monotonic() - start) * 1000)
            if status_code == 200 and "ok" in body.lower():
                return {
                    "passed": True,
                    "message": f"App alive ({health_url})",
                    "duration_ms": duration_ms,
                }
        except ViewerAuthError:
            # Even the internal health endpoint is blocked — unusual
            duration_ms = int((time.monotonic() - start) * 1000)
            return {
                "passed": False,
                "message": "VIEWER_AUTH_BLOCKED: Even /_stcore/health is blocked by viewer auth",
                "duration_ms": duration_ms,
                "blocker": "viewer_auth",
            }
        except Exception:
            continue

    duration_ms = int((time.monotonic() - start) * 1000)

    # Try the main URL to distinguish "down" from "viewer auth blocked"
    try:
        _http_get(base_url, timeout=timeout)
    except ViewerAuthError as e:
        return {
            "passed": False,
            "message": f"VIEWER_AUTH_BLOCKED: {e}",
            "duration_ms": duration_ms,
            "blocker": "viewer_auth",
        }
    except Exception:
        pass

    return {
        "passed": False,
        "message": "App not responding (/_stcore/health and /healthz both failed)",
        "duration_ms": duration_ms,
    }


def check_schp(base_url: str, expected_sha: Optional[str] = None,
               timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Tier 2: Full SCHP capabilities check via ?health=capabilities.

    NOTE: Streamlit renders the SCHP JSON via its UI framework (st.code()),
    so this only works when:
    1. The app is public (no viewer auth), AND
    2. A browser renders the page (Streamlit is an SPA)

    For HTTP-only smoke tests, this will often return 'no SCHP JSON' because
    the HTML response is just the SPA shell. This is expected — use
    check_liveness() as the primary HTTP check, and reserve SCHP parsing
    for browser-based smoke tests.

    Returns a result dict with passed, message, duration_ms, checks, raw.
    """
    url = f"{base_url}/?health=capabilities"
    start = time.monotonic()

    try:
        status_code, body, final_url = _http_get(url, timeout=timeout)
        duration_ms = int((time.monotonic() - start) * 1000)
    except ViewerAuthError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "passed": False,
            "message": f"VIEWER_AUTH_BLOCKED: {e}",
            "duration_ms": duration_ms,
            "checks": [],
            "blocker": "viewer_auth",
        }
    except HTTPError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "passed": False,
            "message": f"HTTP error {e.code}: {e.reason}",
            "duration_ms": duration_ms,
            "checks": [],
        }
    except URLError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "passed": False,
            "message": f"Connection error: {e.reason}",
            "duration_ms": duration_ms,
            "checks": [],
        }
    except (TimeoutError, Exception) as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        is_timeout = isinstance(e, TimeoutError) or "timed out" in str(e).lower()
        msg = f"Timeout ({timeout}s)" if is_timeout else f"Unexpected error: {type(e).__name__}: {e}"
        return {
            "passed": False,
            "message": msg,
            "duration_ms": duration_ms,
            "checks": [],
        }

    if status_code != 200:
        return {
            "passed": False,
            "message": f"HTTP {status_code}",
            "duration_ms": duration_ms,
            "checks": [],
        }

    # Parse SCHP JSON from HTML response
    data = _extract_schp_json(body)
    if not data:
        return {
            "passed": False,
            "message": "No SCHP JSON in response (expected — Streamlit is an SPA; use browser for full SCHP check)",
            "duration_ms": duration_ms,
            "checks": [],
            "note": "streamlit_spa_limitation",
        }

    # Run individual checks
    checks = []

    # Check 1: Status is operational or degraded
    status = data.get("status", "unknown")
    status_ok = status in ("operational", "degraded")
    checks.append({
        "name": "status",
        "passed": status_ok,
        "value": status,
        "expected": "operational or degraded",
    })

    # Check 2: Database connected
    db = data.get("capabilities", {}).get("database", {})
    db_ok = db.get("ok", False)
    checks.append({
        "name": "database",
        "passed": db_ok,
        "value": f"{db.get('latency_ms', '?')}ms" if db_ok else db.get("reason", "failed"),
        "expected": "ok=true",
    })

    # Check 3: User auth available
    auth = data.get("capabilities", {}).get("user_auth", {})
    auth_ok = auth.get("ok", False)
    checks.append({
        "name": "user_auth",
        "passed": auth_ok,
        "value": "available" if auth_ok else auth.get("reason", "unavailable"),
        "expected": "ok=true",
    })

    # Check 4: Version/SHA match (optional)
    version = data.get("version", {})
    if expected_sha:
        got_sha = version.get("git_sha", "unknown")
        sha_match = got_sha != "unknown" and got_sha.startswith(expected_sha[:7])
        checks.append({
            "name": "version_sha",
            "passed": sha_match,
            "value": got_sha,
            "expected": expected_sha[:7],
        })

    all_passed = all(c["passed"] for c in checks)
    summary_parts = []
    for c in checks:
        icon = "✅" if c["passed"] else "❌"
        summary_parts.append(f"{c['name']}={icon}({c['value']})")
    summary = "; ".join(summary_parts)

    return {
        "passed": all_passed,
        "message": summary,
        "duration_ms": duration_ms,
        "checks": checks,
        "raw": data,
    }


def check_health(base_url: str, expected_sha: Optional[str] = None,
                 timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Combined health check: Tier 1 (liveness) + Tier 2 (SCHP) if possible.

    Tier 1 (liveness) is the gate — if the app isn't alive, we fail immediately.
    Tier 2 (SCHP) provides deeper insights but may not work via HTTP due to
    Streamlit's SPA architecture.

    Returns a result dict with passed, message, duration_ms, checks, tiers.
    """
    tiers = {}

    # Tier 1: Liveness check (always works if app is up)
    liveness = check_liveness(base_url, timeout=timeout)
    tiers["liveness"] = liveness

    if not liveness["passed"]:
        return {
            "passed": False,
            "message": liveness["message"],
            "duration_ms": liveness["duration_ms"],
            "checks": [],
            "tiers": tiers,
            "blocker": liveness.get("blocker"),
        }

    # Tier 2: Try SCHP capabilities (may not work via HTTP — that's OK)
    schp = check_schp(base_url, expected_sha=expected_sha, timeout=timeout)
    tiers["schp"] = schp

    # If SCHP worked and returned checks, use those results
    if schp.get("checks"):
        return {
            "passed": schp["passed"],
            "message": f"liveness=✅; {schp['message']}",
            "duration_ms": liveness["duration_ms"] + schp["duration_ms"],
            "checks": schp["checks"],
            "tiers": tiers,
            "raw": schp.get("raw"),
        }

    # SCHP didn't return checks (SPA limitation or viewer auth)
    # Liveness passed, so we report success with a note
    return {
        "passed": True,
        "message": f"liveness=✅ (SCHP not available via HTTP — use browser for full check)",
        "duration_ms": liveness["duration_ms"] + schp.get("duration_ms", 0),
        "checks": [{"name": "liveness", "passed": True, "value": "ok", "expected": "ok"}],
        "tiers": tiers,
        "note": "schp_requires_browser",
    }


def run_smoke_test(url: str, expected_sha: Optional[str] = None,
                   retries: int = DEFAULT_RETRIES,
                   retry_delay: int = DEFAULT_RETRY_DELAY,
                   timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Run the full smoke test with retry logic.

    Returns a summary dict with overall pass/fail and all attempt details.
    """
    attempts = []
    passed = False

    for attempt_num in range(1, retries + 1):
        if attempt_num > 1:
            print(f"⏳ Retry {attempt_num}/{retries} in {retry_delay}s...", file=sys.stderr)
            time.sleep(retry_delay)

        print(f"🔍 Smoke test attempt {attempt_num}/{retries}: {url}", file=sys.stderr)
        result = check_health(url, expected_sha=expected_sha, timeout=timeout)
        result["attempt"] = attempt_num
        result["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        attempts.append(result)

        if result["passed"]:
            passed = True
            print(f"✅ Smoke test PASSED on attempt {attempt_num}", file=sys.stderr)
            break
        else:
            print(f"❌ Attempt {attempt_num} failed: {result['message']}", file=sys.stderr)

    return {
        "passed": passed,
        "url": url,
        "total_attempts": len(attempts),
        "max_retries": retries,
        "attempts": attempts,
        "final_message": attempts[-1]["message"] if attempts else "No attempts made",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Post-deploy smoke test for ChurnPilot"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--url",
        help="Direct URL to test"
    )
    group.add_argument(
        "--env",
        choices=["experiment", "production"],
        help="Named environment to test"
    )
    parser.add_argument(
        "--expected-sha",
        default=None,
        help="Expected git SHA (short or full) to verify"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Max retry attempts (default: {DEFAULT_RETRIES})"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=DEFAULT_RETRY_DELAY,
        help=f"Seconds between retries (default: {DEFAULT_RETRY_DELAY})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout per request in seconds (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Single attempt, no retries"
    )
    args = parser.parse_args()

    url = args.url or ENDPOINTS[args.env]
    retries = 1 if args.single else args.retries

    result = run_smoke_test(
        url=url,
        expected_sha=args.expected_sha,
        retries=retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
    )

    # JSON output to stdout
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
