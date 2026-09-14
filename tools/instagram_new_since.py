#!/usr/bin/env python3
"""
Detector for the weekly Instagram sync routine (see CLAUDE.md).

Fetches the most-recent @mrqfears posts via Instagram's public logged-out web
endpoint (no login, no cookies, no Keychain), then lists the ones that are NEW
relative to instagram-ledger.json: dated after `reviewed_through` and not already
recorded. Prints a human summary; add --json for machine-readable output the
routine can act on.

    python3 tools/instagram_new_since.py
    python3 tools/instagram_new_since.py --json

Login-free and gentle (a single request), so it is safe to run unattended on a
schedule. It only reads; it never writes the ledger or the site. Instagram
returns roughly the 12 most-recent posts this way, which is plenty for a weekly
"what's new" check.

Exit codes: 0 success, 2 Instagram refused the request (rate-limited), 3 the
host could not be reached at all (no network, or an egress policy that does not
allow it). A blocked run is reported in one line, never as a traceback, so the
weekly routine can tell "nothing new" apart from "could not look".
"""

import argparse
import datetime as dt
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

API_HOST = "i.instagram.com"
APP_ID = "936619743392459"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def fetch_recent(user):
    url = (f"https://{API_HOST}/api/v1/users/web_profile_info/?username="
           + urllib.parse.quote(user))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "X-IG-App-ID": APP_ID,
        "Referer": "https://www.instagram.com/", "Accept": "*/*"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return data["data"]["user"]


def unreachable_reason(err):
    """Explain a connection failure, naming an egress block when that is what it is."""
    text = str(getattr(err, "reason", err) or err)
    if "Tunnel connection failed" in text and ("403" in text or "407" in text):
        return (f"Could not reach {API_HOST}: the outbound proxy on this machine "
                f"refused the tunnel ({text.strip()}), so the host is not permitted "
                f"by this environment's network policy. Detection cannot run here. "
                f"Allow {API_HOST} and www.instagram.com for this environment, or "
                f"run the detector where egress is open. Do not route around the "
                f"proxy.")
    return (f"Could not reach {API_HOST}: {text}. Detection did not run, so this "
            f"is not the same as finding no new posts.")


def fail(args, status, message, code):
    """Report a detection failure once, in whichever form the caller asked for."""
    if args.json:
        print(json.dumps({"user": args.user, "status": status,
                          "new_count": None, "error": message}, indent=2))
    print(message, file=sys.stderr)
    sys.exit(code)


def post_kind(node):
    t = node.get("__typename")
    return {"GraphImage": "photo", "GraphVideo": "video",
            "GraphSidecar": "carousel"}.get(t, "post")


def best_image(node):
    res = node.get("display_resources") or []
    if res:
        return max(res, key=lambda r: r.get("config_width", 0)).get("src")
    return node.get("display_url")


def main():
    ap = argparse.ArgumentParser(description="List new @mrqfears posts since the ledger.")
    ap.add_argument("--user", default="mrqfears")
    ap.add_argument("--ledger", default="instagram-ledger.json")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()

    ledger = {}
    if os.path.exists(args.ledger):
        ledger = json.load(open(args.ledger))
    cutoff = ledger.get("reviewed_through") or "0000-00-00"
    known = {e.get("shortcode") for e in
             (ledger.get("incorporated", []) + ledger.get("skipped", []))}

    try:
        user = fetch_recent(args.user)
    except urllib.error.HTTPError as e:
        fail(args, "refused",
             f"Instagram returned HTTP {e.code} for the anonymous endpoint "
             f"(likely rate-limited). Try again later.", 2)
    except OSError as e:
        fail(args, "unreachable", unreachable_reason(e), 3)

    edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
    new = []
    for e in edges:
        n = e["node"]
        code = n.get("shortcode")
        ts = n.get("taken_at_timestamp")
        date = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if ts else None
        if code in known:
            continue
        if date and date <= cutoff:
            continue
        capedges = n.get("edge_media_to_caption", {}).get("edges", [])
        caption = capedges[0]["node"]["text"] if capedges else ""
        new.append({
            "shortcode": code,
            "date": date,
            "kind": post_kind(n),
            "permalink": f"https://www.instagram.com/p/{code}/",
            "image": best_image(n),
            "caption": caption,
        })

    if args.json:
        print(json.dumps({"user": args.user, "reviewed_through": cutoff,
                          "new_count": len(new), "new": new}, indent=2))
        return

    print(f"@{args.user}: {len(new)} new post(s) since {cutoff}\n")
    for p in new:
        cap = " ".join((p["caption"] or "").split())
        if len(cap) > 160:
            cap = cap[:160] + "..."
        print(f"- [{p['date']}] {p['kind']:<8} {p['permalink']}")
        print(f"    {cap or '(no caption)'}")
    if not new:
        print("(nothing new -- routine would stop here this week.)")


if __name__ == "__main__":
    main()
