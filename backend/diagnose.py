from __future__ import annotations

import asyncio
import json
import traceback
from datetime import datetime

import httpx

from app.celery_app import celery_app
from app.config import settings
from app.core.classifier import classify_commit
from app.core.fingerprint import compute_fingerprint
from app.core.github_client import GitHubClient
from app.models.github import RepoInfo
from app.tasks.analyze import _run_analysis_async


def section(name: str) -> None:
    print("\n" + "=" * 60)
    print(f"SECTION: {name}")
    print("=" * 60)


def check_celery_registration() -> bool:
    section("Celery Task Registration")
    registered = celery_app.tasks.keys()
    analyze_registered = "app.tasks.analyze.run_analysis" in registered
    print(f"Task registered: {analyze_registered}")
    if not analyze_registered:
        print("CRITICAL: app.tasks.analyze.run_analysis not in registered tasks")
        print("All registered tasks:", list(registered))

    try:
        insp = celery_app.control.inspect(timeout=3)
        ping = insp.ping() if insp else None
        print(f"Workers online: {ping}")

        active = insp.active() if insp else None
        print(f"Active tasks: {active}")

        registered_on_worker = insp.registered() if insp else None
        print(f"Tasks on worker: {registered_on_worker}")
    except Exception as exc:  # noqa: BLE001
        print(f"Celery inspect FAILED: {exc}")
        return False

    return analyze_registered


async def test_github() -> bool:
    section("GitHub Client Test")
    token = settings.GITHUB_API_TOKEN or None
    client = GitHubClient(token=token)
    github_ok = False

    # Test 1: probe endpoint
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as c:
            headers = {"Accept": "application/vnd.github+json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            r = await c.get(
                "https://api.github.com/users/torvalds",
                headers=headers,
            )
            print(f"GitHub probe: {r.status_code}")
            print(f"Rate limit remaining: {r.headers.get('X-RateLimit-Remaining')}")
            print(f"Rate limit reset: {r.headers.get('X-RateLimit-Reset')}")
            github_ok = r.status_code < 500
    except Exception as exc:  # noqa: BLE001
        print(f"GitHub probe FAILED: {exc}")
        await client.close()
        return False

    # Test 2: fetch repos
    repos: list[RepoInfo] = []
    try:
        print("\nFetching repos for torvalds...")
        repos = await client.fetch_repos("torvalds", include_private=False)
        print(f"Repos fetched: {len(repos)}")
        if repos:
            print(f"First repo: {repos[0].full_name}")
        github_ok = github_ok and True
    except Exception as exc:  # noqa: BLE001
        print(f"fetch_repos FAILED: {exc}")
        traceback.print_exc()
        await client.close()
        return False

    # Test 3: fetch commits from first repo
    if repos:
        try:
            print(f"\nFetching commits from {repos[0].full_name}...")
            commits = await client.fetch_commits(repos[0].full_name, max_count=5)
            print(f"Commits fetched: {len(commits)}")
            if commits:
                print(f"First commit: {commits[0].sha[:8]} - {commits[0].message[:50]}")
        except Exception as exc:  # noqa: BLE001
            print(f"fetch_commits FAILED: {exc}")
            traceback.print_exc()
            await client.close()
            return False

    await client.close()
    return github_ok


def test_classifier() -> bool:
    section("Classifier Test")
    try:
        record = classify_commit(
            sha="abc123",
            message="feat: add new radar chart component",
            diff="+ def render_chart():\n+     pass\n",
            repo="test-repo",
            date=datetime.utcnow(),
            lines_added=10,
            lines_deleted=2,
        )
        print(f"Classifier OK: label={record.label}, confidence={record.confidence}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Classifier FAILED: {exc}")
        traceback.print_exc()
        return False


def test_fingerprint() -> bool:
    section("Fingerprint Test")
    try:
        records = [
            classify_commit(
                "abc1",
                "feat: add feature",
                "+ def new():\n+     pass",
                "repo",
                datetime.utcnow(),
                10,
                0,
            ),
            classify_commit(
                "abc2",
                "fix: fix bug",
                "- old_code\n+ new_code",
                "repo",
                datetime.utcnow(),
                1,
                1,
            ),
            classify_commit(
                "abc3",
                "refactor: clean up",
                "- verbose\n+ clean",
                "repo",
                datetime.utcnow(),
                2,
                5,
            ),
        ]
        repos = [
            RepoInfo(
                name="test",
                full_name="user/test",
                language="Python",
                stargazers_count=0,
                pushed_at=datetime.utcnow().isoformat(),
            )
        ]
        fp = compute_fingerprint("testuser", records, repos, ["Python"])
        print("Fingerprint OK:")
        print(f"  axes: {fp.axes.model_dump()}")
        print(f"  style_evolution: {fp.style_evolution}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Fingerprint FAILED: {exc}")
        traceback.print_exc()
        return False


class FakeTask:
    """Mimics the Celery task self object."""

    def update_state(self, state, meta):
        print(f"  PROGRESS: {meta.get('progress', 0)}% - {meta.get('message', '')}")

    def retry(self, countdown=0, exc=None):
        print(f"  RETRY requested: countdown={countdown}, exc={exc}")
        raise exc or Exception("Retry requested")


async def test_direct() -> bool:
    section("Direct Task Test (no Celery)")
    print("Running _run_analysis_async directly...")
    try:
        fake_task = FakeTask()
        fallback_token = settings.GITHUB_API_TOKEN or None
        result = await _run_analysis_async(fake_task, "torvalds", fallback_token, False)
        print("SUCCESS:", list(result.keys()))
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED at: {exc}")
        traceback.print_exc()
        return False


async def run_diagnostics() -> bool:
    section("End-to-End API Test")
    base = "http://localhost:8000"
    final_state = None

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        # Health check
        try:
            r = await client.get(f"{base}/health")
            print("HEALTH:", json.dumps(r.json(), indent=2))
        except Exception as exc:  # noqa: BLE001
            print(f"HEALTH FAILED: {exc}")
            return False

        # Submit a job
        try:
            r = await client.post(
                f"{base}/api/analyze",
                json={"username": "torvalds", "include_private": False},
            )
            print(f"\nANALYZE STATUS: {r.status_code}")
            print("ANALYZE RESPONSE:", json.dumps(r.json(), indent=2))

            if r.status_code != 200:
                print("ERROR: analyze endpoint failed - check profile.py")
                return False

            job_id = r.json().get("job_id")
            if not job_id:
                print("ERROR: no job_id in response")
                return False

            if job_id == "cached" and r.json().get("status") == "SUCCESS":
                print("Cached analysis returned SUCCESS immediately")
                return True

            print(f"\nJob ID: {job_id}")
        except Exception as exc:  # noqa: BLE001
            print(f"ANALYZE FAILED: {exc}")
            return False

        # Poll status 10 times
        print("\nPolling status every 3 seconds...")
        for i in range(10):
            await asyncio.sleep(3)
            try:
                r = await client.get(f"{base}/api/status/{job_id}")
                data = r.json()
                state = data.get("status", "UNKNOWN")
                pct = data.get("progress_pct", 0)
                msg = data.get("message", "")
                print(f"  [{i + 1}] {state} {pct}% - {msg}")
                final_state = state
                if state in ("SUCCESS", "FAILURE"):
                    break
            except Exception as exc:  # noqa: BLE001
                print(f"  [{i + 1}] POLL ERROR: {exc}")

        print(f"\nFinal state after 30s: {final_state}")

        if final_state == "SUCCESS":
            r = await client.get(f"{base}/api/result/{job_id}")
            print("RESULT:", json.dumps(r.json(), indent=2)[:500])
            return True
        if final_state == "PENDING":
            print("STUCK: task never moved from PENDING")
            print("This means Celery worker is not picking up the task")
            return False
        if final_state == "RETRY":
            print("RETRYING: task hit an error and is retrying")
            print("Check the Celery worker terminal for the error")
            return False

    return final_state in ("SUCCESS",)


async def main() -> None:
    task_registered = check_celery_registration()
    github_ok = await test_github()
    classifier_ok = test_classifier()
    fingerprint_ok = test_fingerprint()
    direct_ok = await test_direct()
    e2e_ok = await run_diagnostics()

    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Celery task registered: {task_registered}")
    print(f"GitHub API reachable:   {github_ok}")
    print(f"Classifier working:     {classifier_ok}")
    print(f"Fingerprint working:    {fingerprint_ok}")
    print(f"Direct task test:       {direct_ok}")
    print(f"End-to-end API test:    {e2e_ok}")

    failed = [
        k
        for k, v in {
            "celery": task_registered,
            "github": github_ok,
            "classifier": classifier_ok,
            "fingerprint": fingerprint_ok,
            "direct_task": direct_ok,
            "e2e_api": e2e_ok,
        }.items()
        if not v
    ]

    if not failed:
        print("\nAll checks passed - pipeline is working end to end")
    else:
        print(f"\nFailed checks: {failed}")
        print("Fix the failed checks above in order - each one depends on the previous")


if __name__ == "__main__":
    asyncio.run(main())