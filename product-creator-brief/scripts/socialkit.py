#!/usr/bin/env python3
"""Bounded Instagram reference collection. Python 3 standard library only."""
import argparse
import contextlib
import datetime
import fcntl
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.socialkit.dev"
USER_AGENT = "ProductCreatorBrief/2.0.0 (SocialKit API client)"
QUALITIES = ("240p", "360p", "480p", "720p", "1080p")


class APIError(Exception):
    def __init__(self, code, status=0):
        self.code, self.status = code, status
        super().__init__(f"{code} (HTTP {status})" if status else code)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


@contextlib.contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise APIError("collection_already_running")
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def key_path(value=None):
    return Path(value or os.environ.get("SOCIALKIT_KEY_FILE") or "work/private/socialkit.json").expanduser()


def load_key(value=None):
    key = os.environ.get("SOCIALKIT_API_KEY", "").strip()
    if not key:
        path = key_path(value)
        if not path.is_file():
            raise APIError("key_missing: run configure first")
        if path.stat().st_mode & 0o077:
            raise APIError("key_file_permissions: chmod 600 on the key file")
        key = json.loads(path.read_text()).get("api_key", "").strip()
    if not key or "\n" in key or "\r" in key:
        raise APIError("invalid_local_key")
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the API key to a redirected host.


class Client:
    def __init__(self, key):
        self.key = key
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, path, params=None, body=None):
        if not path.startswith("/") or path.startswith("//"):
            raise APIError("invalid_api_path")
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"x-access-key": self.key, "Accept": "application/json", "User-Agent": USER_AGENT}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=payload, headers=headers)
        try:
            with self.opener.open(req, timeout=45) as response:
                raw = response.read(2 * 1024 * 1024)
        except urllib.error.HTTPError as exc:
            try:
                info = json.loads(exc.read(65536))
                code = info.get("code") or info.get("errorCode") or info.get("error_code")
                if not code and isinstance(info.get("error"), dict):
                    code = info["error"].get("code")
            except (ValueError, TypeError, AttributeError):
                code = None
            # Raw responses and request objects may contain credentials: never log them.
            code = code if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", code) else "http_error"
            if self.key in code:
                code = "http_error"
            raise APIError(code, exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise APIError("network_error") from None
        try:
            info = json.loads(raw)
        except ValueError:
            raise APIError("invalid_json_response") from None
        if not isinstance(info, dict) or info.get("success") is not True:
            raise APIError("api_unsuccessful")
        return info.get("data", {})

    def credits(self):
        data = self.request("/credits")
        remaining = data.get("totalRemaining")
        if isinstance(remaining, bool) or not isinstance(remaining, (int, float)):
            raise APIError("credits_schema_changed")
        return remaining


def identity(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ("instagram.com", "www.instagram.com", "m.instagram.com"):
        raise APIError("expected_https_instagram_video_url")
    if parsed.username or parsed.password:
        raise APIError("invalid_source_url")
    parts = parsed.path.strip("/").split("/")
    for pos, part in enumerate(parts[:-1]):
        if part in ("reel", "reels", "p", "tv") and re.fullmatch(r"[A-Za-z0-9_-]+", parts[pos + 1]):
            return parts[pos + 1]
    raise APIError("expected_instagram_reel_or_post_url")


def search(client, query, out, refresh=False):
    query = query.strip()
    if not 1 <= len(query) <= 100:
        raise APIError("query_length_must_be_1_to_100")
    out = Path(out)
    with lock(out.with_suffix(out.suffix + ".lock")):
        if out.exists() and not refresh:
            cached = json.loads(out.read_text())
            if cached.get("requested_query") != query:
                raise APIError("cache_query_mismatch: use another output filename")
            return cached
        if client.credits() < 1:
            raise APIError("insufficient_credits")
        data = client.request("/instagram/reels-search", params={"query": query, "page": 1})
        if not isinstance(data.get("items"), list):
            raise APIError("search_schema_changed")
        result = {"requested_query": query, "fetched_at": now(), "endpoint": "/instagram/reels-search",
                  "scope": "one anonymous batch, at most 12; not a topic census", "items": []}
        seen = set()
        for item in data["items"][:12]:
            try:
                code = identity(item.get("url", ""))
            except (APIError, ValueError, TypeError):
                continue
            if code in seen:
                continue
            seen.add(code)
            # Search zero likes/comments can be placeholders. Keep them explicitly unknown.
            result["items"].append({"shortcode": code, "url": item["url"],
                "caption": item.get("caption"), "author": (item.get("author") or {}).get("username"),
                "views": item.get("views"), "likes": item.get("likes") or None,
                "comments": item.get("comments") or None, "duration_seconds": item.get("duration") or None,
                "posted_timestamp": item.get("timestamp"), "metrics_note": "search snapshot; zero likes/comments treated as unknown"})
        save(out, result)
        return result


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_file(url, path):
    if urllib.parse.urlsplit(url).scheme != "https":
        raise APIError("invalid_download_url")
    path = Path(path)
    tmp = path.with_suffix(".part")
    try:
        # Separate unauthenticated request: API credentials never go to the file host.
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=45) as response, tmp.open("wb") as handle:
            size = 0
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                size += len(chunk)
                if size > 200 * 1024 * 1024:
                    raise APIError("local_file_size_limit_200MB")
                handle.write(chunk)
        with tmp.open("rb") as handle:
            head = handle.read(64)
        if b"ftyp" not in head or tmp.stat().st_size < 32:
            raise APIError("download_not_mp4")
        tmp.replace(path)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise APIError("file_transfer_error") from None
    finally:
        tmp.unlink(missing_ok=True)


def download(client, urls, out_dir, max_count=3, quality="480p", max_duration=120,
             max_credits=6, poll_seconds=5, wait_seconds=180, fetch=fetch_file,
             clock=time.monotonic, sleep=time.sleep):
    if max_count < 1 or max_duration < 1 or max_credits < 1 or poll_seconds < 1 or wait_seconds < 1:
        raise APIError("limits_must_be_positive")
    if quality not in QUALITIES:
        raise APIError("invalid_quality")
    unique = {}
    for url in urls:
        unique.setdefault(identity(url), url)  # Original source URL is retained for API requests.
    if not unique or len(unique) > max_count:
        raise APIError("select_between_1_and_max_count_urls")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    limits = {"max_count": max_count, "quality": quality, "max_duration": max_duration, "max_credits": max_credits}
    reservation = math.ceil(max_duration / 60) * (4 if quality in ("720p", "1080p") else 1)
    with lock(out_dir / ".collection.lock"):
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
            "created_at": now(), "limits": limits, "entries": {}}
        if manifest["limits"] != limits:
            raise APIError("batch_limits_changed: resume with original limits; use a new directory for a new batch")
        entries = manifest["entries"]
        if len(set(entries) | set(unique)) > max_count:
            raise APIError("batch_total_exceeds_max_count")
        for code, url in unique.items():
            entry = entries.get(code)
            path = out_dir / (code + ".mp4")
            if entry and entry["state"] == "downloaded" and path.is_file() and file_hash(path) == entry.get("sha256"):
                continue
            if entry and entry["state"] in ("submitting", "submission_unknown", "failed"):
                continue  # Never silently create another potentially billed job.
            if not entry:
                committed = sum(e.get("reservation", 0) for e in entries.values())
                if committed + reservation > max_credits:
                    raise APIError("batch_credit_cap_reached")
                if client.credits() < reservation:
                    raise APIError("insufficient_credits")
                entry = {"source_url": url, "shortcode": code, "created_at": now(), "state": "submitting",
                         "reservation": reservation, "quality": quality, "max_duration": max_duration}
                entries[code] = entry
                save(manifest_path, manifest)
                try:
                    job = client.request("/v2/instagram/download", body={"url": url, "format": "mp4",
                        "quality": quality, "max_duration": max_duration})
                    job_id = job.get("jobId")
                    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", job_id):
                        raise APIError("missing_job_id")
                except APIError as exc:
                    entry["state"] = "failed" if 400 <= exc.status < 500 else "submission_unknown"
                    if entry["state"] == "failed":
                        entry["reservation"] = 0
                    entry["error_code"] = exc.code
                    save(manifest_path, manifest)
                    raise
                entry.update(job_id=job_id, state="pending")
                save(manifest_path, manifest)
            deadline = clock() + wait_seconds
            while True:
                try:
                    data = client.request("/v2/downloads/" + entry["job_id"])
                except APIError as exc:
                    entry["last_poll_error"] = exc.code
                    save(manifest_path, manifest)
                    raise  # Same job can be resumed; no automatic submission retry.
                state = data.get("status")
                if state == "failed":
                    error_code = data.get("errorCode", "job_failed")
                    if not isinstance(error_code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", error_code):
                        error_code = "job_failed"
                    entry.update(state="failed", error_code=error_code, retryable=data.get("retryable"), reservation=0)
                    save(manifest_path, manifest)
                    break
                if state == "ready":
                    entry.update(state="ready", duration_seconds=data.get("durationSeconds"),
                                 credits_cost=data.get("creditsCost"), billed=data.get("billed"))
                    entry.pop("last_poll_error", None)
                    save(manifest_path, manifest)  # Do not persist the signed download URL.
                    try:
                        fetch(data.get("downloadUrl", ""), path)
                    except APIError as exc:
                        entry["file_error"] = exc.code
                        save(manifest_path, manifest)
                        raise
                    entry.update(state="downloaded", local_file=path.name, sha256=file_hash(path), downloaded_at=now())
                    entry.pop("file_error", None)
                    save(manifest_path, manifest)
                    break
                if state not in ("queued", "processing"):
                    raise APIError("unknown_job_status")
                entry["state"] = "pending"
                save(manifest_path, manifest)
                if clock() >= deadline:
                    entry["last_poll_error"] = "poll_timeout"
                    save(manifest_path, manifest)
                    break
                sleep(min(poll_seconds, max(0, deadline - clock())))
        return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", help="Local protected JSON; default work/private/socialkit.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("configure", help="Enter key privately; no API call")
    sub.add_parser("check", help="Verify authentication and balance; no collection")
    query = sub.add_parser("search")
    query.add_argument("--query", required=True)
    query.add_argument("--out", required=True)
    query.add_argument("--refresh", action="store_true", help="Make a new paid search despite local cache")
    dl = sub.add_parser("download")
    dl.add_argument("--urls-file", required=True, help="One original Instagram URL per line")
    dl.add_argument("--out-dir", required=True)
    dl.add_argument("--max-count", type=int, default=3)
    dl.add_argument("--quality", choices=QUALITIES, default="480p")
    dl.add_argument("--max-duration", type=int, default=120)
    dl.add_argument("--max-credits", type=int, default=6, help="Download budget only; searches have separate cost")
    dl.add_argument("--wait-seconds", type=int, default=180)
    args = parser.parse_args()
    try:
        if args.command == "configure":
            if not sys.stdin.isatty():
                raise APIError("configure_requires_private_interactive_terminal")
            path = key_path(args.key_file)
            key = getpass.getpass("SocialKit Access Key（输入不显示）: ").strip()
            if not key or "\n" in key or "\r" in key:
                raise APIError("invalid_local_key")
            new_parent = not path.parent.exists()
            path.parent.mkdir(parents=True, exist_ok=True)
            if new_parent:
                os.chmod(path.parent, 0o700)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags, 0o600)
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w") as handle:
                json.dump({"api_key": key}, handle)
                handle.write("\n")
            print("Key 已保存到本地私有文件；未发起 API 调用。")
            return 0
        client = Client(load_key(args.key_file))
        if args.command == "check":
            client.request("/test")
            print(json.dumps({"authentication": "ok", "remaining_credits": client.credits()}))
        elif args.command == "search":
            result = search(client, args.query, args.out, args.refresh)
            print(json.dumps({"result_file": args.out, "count": len(result["items"])}))
        elif args.command == "download":
            urls = [line.strip() for line in Path(args.urls_file).read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
            result = download(client, urls, args.out_dir, args.max_count, args.quality, args.max_duration,
                              args.max_credits, wait_seconds=args.wait_seconds)
            counts = {}
            for entry in result["entries"].values():
                counts[entry["state"]] = counts.get(entry["state"], 0) + 1
            print(json.dumps({"manifest": str(Path(args.out_dir) / "manifest.json"), "states": counts}))
            return 0 if all(e["state"] == "downloaded" for e in result["entries"].values()) else 2
        return 0
    except APIError as exc:
        print("SocialKit: " + str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print("SocialKit: local_io_or_schema_error; inspect local files and API documentation", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
