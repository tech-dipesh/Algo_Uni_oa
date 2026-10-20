import random
from pathlib import Path

out = Path(__file__).resolve().parent.parent / "lab" / "data"
out.mkdir(parents=True, exist_ok=True)
rng = random.Random(38)
modules = ["auth", "billing", "export", "notify", "onboarding", "profile", "reports", "search", "sync"]
owners = ["mira", "kofi", "lena", "ravi", "yuki", "omar"]
block_modules = ["billing", "auth", "sync", "billing", "billing", "notify", "auth", "reports", "sync", "billing", "auth", "billing", "sync", "notify", "auth"]
block_users = [9, 45, 1500, 120, 87, 310, 2750, 64, 18, 980, 4200, 7, 560, 33, 1210]
slots = set(rng.sample(range(150), 15))
blockers = iter(zip(block_modules, block_users))

def other():
    status = rng.choices(["open", "fixed", "deferred"], [4, 5, 2])[0]
    sev = rng.choices([1, 2, 3, 4], [2, 4, 5, 3])[0]
    return [rng.choice(modules), status, 2 if status == "open" and sev == 1 else sev, rng.randint(1, 8999), rng.choice(owners)]

def row(i):
    if i not in slots: return other()
    mod, users = next(blockers)
    return [mod, "open", 1, users, rng.choice(owners)]

bugs = ["id,module,status,severity,users,owner"] + [f"BUG-{1001 + i}," + ",".join(map(str, row(i))) for i in range(150)]
(out / "bugs.csv").write_text("\n".join(bugs) + "\n")

runbook = """HARBOR RELEASE RUNBOOK
Owner: platform team
Last reviewed: 2026-10-05

CONTENTS
  1. Branch and tag
  2. Build checks
  3. HOLD RULE sections (one per release)
  4. Rollback
  5. Communication
  6. Database migrations
  7. Smoke tests
  8. After the release

Only the HOLD RULE section marked ACTIVE applies to the current release.
The others are kept for the audit trail and must not be used.

1. BRANCH AND TAG
Cut the release branch from main after the last merge of the sprint.
Name it release/<version>, for example release/3.8.
Tag the final commit v<version> once the hold rule is clear.
Do not cherry-pick onto a tagged commit; make a new patch version.
Merge commits only. Squashing on release branches hides authorship.
The branch cut happens on Tuesday morning, before standup.
Anyone merging after the cut needs the release manager to approve it.
Version numbers follow major.minor; hotfixes add a third number.

2. BUILD CHECKS
CI must be green on three jobs: lint, unit, integration.
A flaky integration job may be re-run once; log the re-run in the channel.
A second failure is treated as a real failure.
Bundle size budget is 480 KB gzipped for the web client.
The mobile build must install on the two oldest supported devices.
Dependency updates are frozen after the cut except security fixes.
Build artifacts are kept for 30 days, then deleted by the storage policy.
Never rebuild a tagged commit on a different machine image.

3. HOLD RULE SECTIONS
Each release gets its own hold rule. The release board approves it in writing.
A rule is ACTIVE only after approval. A draft never overrides an approved rule.
When a new release starts, the previous rule is marked ARCHIVED.

RELEASE HOLD RULE - v3.6 (ARCHIVED)
A bug blocks release 3.6 when its severity is 1.
Approved by: release board, 2026-06-12
Superseded: 2026-08-20
Note: status was ignored in this version, so fixed bugs were still counted.
That is why the 3.7 rule added a status check.

RELEASE HOLD RULE - v3.7 (ARCHIVED)
A bug blocks release 3.7 when its status is open and its severity is 1 or 2.
Approved by: release board, 2026-08-20
Superseded: 2026-10-02
Note: severity 2 holds caused two late slips, so the board narrowed it for 3.8.

RELEASE HOLD RULE - v3.8 (DRAFT, NOT APPROVED)
A bug blocks release 3.8 when its status is open.
Proposed by: QA lead, 2026-09-28
Rejected: 2026-10-02, too broad, it would hold the release for cosmetic bugs.
Kept for reference only.

RELEASE HOLD RULE - v3.8 (ACTIVE)
A bug blocks release 3.8 when its status is open and its severity is 1.
Approved by: release board, 2026-10-02
Data: bugs.csv, tracker export of 2026-10-16.
Columns: id, module, status, severity, users, owner. Severity 1 is the worst.
Report each blocked module once, with its blocker count, most blockers first.
Escalate each blocked module to its current on-call contact, not the wiki page.
Also report the largest number of users hit by a single blocker.
Deferred bugs do not block, even at severity 1.

4. ROLLBACK
Rollback is a revert of the release merge, never a force push.
Decide within 30 minutes of the first error spike; after that, fix forward.
The on-call engineer for the failing module runs the revert.
Feature flags are switched off before reverting code.
Record the revert commit in the release ticket.
Run the smoke tests again after the revert, same as after a deploy.

5. COMMUNICATION
Post in #release at branch cut, at hold decision, and at tag.
Use the hold template: version, blockers, owners, next check time.
Customer notes are written by support from the approved release notes only.
Never announce a date before the hold rule is clear.
Status page updates need the incident commander's approval.
Keep updates short: what changed, who owns it, when the next update comes.

6. DATABASE MIGRATIONS
Migrations run before the new code is deployed and must be backward compatible.
Destructive changes (drop column, drop table) ship one release later.
Every migration has a tested down script on a copy of production data.
Long migrations (over 5 minutes) need a maintenance window and a note in #release.
Row counts are compared before and after.
Never edit a migration that has already run in any shared environment.

7. SMOKE TESTS
Run the smoke suite against staging, then against production after deploy.
Minimum paths: sign up, log in, create a habit, sync from a second device, export.
A smoke failure on production triggers the rollback decision, not a debate.
Screenshots of each path go in the release ticket.
Run time target is under 12 minutes.
New features add one path each; remove paths only with release board approval.

8. AFTER THE RELEASE
Close the release ticket after 48 hours without a severity 1 report.
Move deferred bugs to the next sprint with a new owner.
Update the on-call contact list if ownership changed.
Write down anything this runbook got wrong, then fix this file.

-- end of runbook, revision 14 --
"""
(out / "runbook.txt").write_text(runbook)

wiki = ["auth:mira.okafor:#sec-auth", "billing:tomas.reyes:#pay-ops", "export:lena.haas:#data-out", "legacy-api:sam.cole:#old-api", "notify:kofi.mensah:#msg-eng", "onboarding:ines.duarte:#growth", "profile:ravi.nair:#accounts", "search:yuki.sato:#find", "sync:omar.farid:#sync-core"]
oncall = ["auth:mira.okafor:#sec-auth", "billing:priya.iyer:#pay-ops", "export:lena.haas:#data-out", "notify:kofi.mensah:#msg-eng", "onboarding:ines.duarte:#growth", "profile:ravi.nair:#accounts", "reports:hana.lind:#insights", "search:yuki.sato:#find", "sync:omar.farid:#sync-core"]
(out / "contacts-wiki.txt").write_text("\n".join(wiki) + "\n")
(out / "contacts-oncall.txt").write_text("\n".join(oncall) + "\n")
(out / "handover.template").write_text("Release: v3.7\nPrepared by:\nRule:\nBlockers:\nEscalate (most blockers first):\nLargest blocker reach:\n")
