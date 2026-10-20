import hashlib
import os
import subprocess
import sys
from pathlib import Path

lab = Path(__file__).resolve().parent
data = lab / "data"
files = ["bugs.csv", "runbook.txt", "contacts-wiki.txt", "contacts-oncall.txt"]
header, *rest = (data / "bugs.csv").read_text().splitlines()
rows = [r.split(",") for r in rest]
blockers = [r for r in rows if r[2] == "open" and r[3] == "1"]
mods = [r[1] for r in blockers]
users = [r[4] for r in blockers]
book = (data / "runbook.txt").read_text().splitlines()
tally = {m: mods.count(m) for m in set(mods)}
want_pairs = sorted(((n, m) for m, n in tally.items()), key=lambda p: (-p[0], p[1]))

def rule_after(tag):
    i = next(i for i, l in enumerate(book) if l.startswith("RELEASE HOLD RULE") and tag in l)
    return book[i + 1]

active, archived, draft = rule_after("(ACTIVE)"), rule_after("v3.7"), rule_after("DRAFT")

def contacts(name):
    return {l.split(":")[0]: l.split(":")[1:] for l in (data / name).read_text().splitlines()}

oncall, wiki = contacts("contacts-oncall.txt"), contacts("contacts-wiki.txt")

def diff_of(x, y):
    return subprocess.run(["diff", str(data / x), str(data / y)], capture_output=True, text=True).stdout

want_fwd, want_rev = diff_of("contacts-wiki.txt", "contacts-oncall.txt"), diff_of("contacts-oncall.txt", "contacts-wiki.txt")

def text(a, rel):
    p = a / rel
    return p.read_text() if p.is_file() else None

def lines(a, rel):
    t = text(a, rel)
    return None if t is None else t.splitlines()

def column(a, rel, want, label):
    got = lines(a, rel)
    if got is None: return f"{rel} missing"
    if got == want: return None
    if sorted(got) == sorted(want): return f"{rel} has the right values in the wrong order: cut keeps file order, was it sorted?"
    return f"{rel} does not hold the {label} column of work/blockers.csv"

def c_evidence(a):
    bad = []
    for f in files:
        p = a / "evidence" / f
        if not p.is_file(): bad.append(f"evidence/{f} is missing")
        elif hashlib.sha256(p.read_bytes()).digest() != hashlib.sha256((data / f).read_bytes()).digest(): bad.append(f"evidence/{f} was changed: edit copies in work/ only")
    return bad

def c_history(a):
    bad = []
    got = lines(a, "work/header.txt")
    if got is None: bad.append("work/header.txt missing: recall the head command and add > work/header.txt")
    elif got != [header]: bad.append("work/header.txt should hold only the header line")
    h = lines(a, ".lab_history")
    if h is None: return bad + ["no .lab_history: run source .labrc in the attempt folder first"]
    if "history 10" not in [l.strip() for l in h]: bad.append("history 10 was never run")
    if not any(l.startswith("history |") and "grep" in l for l in h): bad.append("no history | grep command found")
    return bad

def c_less(a):
    h = lines(a, ".lab_history")
    if h is None: return ["no .lab_history: run source .labrc in the attempt folder first"]
    return [] if any(l.split()[:1] == ["less"] and "runbook.txt" in l for l in h) else ["less evidence/runbook.txt was never run"]

def c_nano(a):
    bad = []
    h = lines(a, "work/handover.txt")
    if h is None or len(h) < 2: bad.append("work/handover.txt is missing or too short")
    else:
        if h[0] != "Release: v3.8": bad.append("handover.txt line 1 should read Release: v3.8")
        if not h[1].startswith("Prepared by:") or not h[1][12:].strip(): bad.append("handover.txt line 2 needs your name after Prepared by:")
    raw = text(a, "work/rule.txt")
    got = None if raw is None else raw.splitlines()
    if raw is None: bad.append("work/rule.txt missing: create it with nano")
    elif got == [archived]: bad.append("rule.txt holds the ARCHIVED v3.7 rule: use the ACTIVE heading")
    elif got == [draft]: bad.append("rule.txt holds the DRAFT rule: use the ACTIVE heading")
    elif got == [active] and not raw.endswith("\n"): bad.append("rule.txt must end with a newline: press Enter on the last line")
    elif got != [active]: bad.append("rule.txt must hold only the sentence under the ACTIVE heading, copied exactly")
    hist = lines(a, ".lab_history")
    if hist is not None and not any(l.split()[:1] == ["nano"] for l in hist): bad.append("nano was never run")
    return bad

def c_cut(a):
    bad = []
    b = lines(a, "work/blockers.csv")
    want = [",".join(r) for r in blockers]
    if b is None: bad.append("work/blockers.csv missing")
    elif b != want: bad.append(f"work/blockers.csv has {len(b)} rows, expected {len(want)}: re-read the ACTIVE rule" if len(b) != len(want) else "work/blockers.csv rows differ from the ACTIVE rule")
    bad += [m for m in [column(a, "work/blocker-modules.txt", mods, "module"), column(a, "work/blocker-users.txt", users, "users")] if m]
    return bad

def c_sort(a):
    bad = []
    m = lines(a, "work/modules-sorted.txt")
    if m is None: bad.append("work/modules-sorted.txt missing")
    elif m != sorted(mods): bad.append("work/modules-sorted.txt is not the sorted module list")
    u = lines(a, "work/users-high-first.txt")
    if u is None: bad.append("work/users-high-first.txt missing")
    elif u != sorted(users, key=int, reverse=True):
        if u == sorted(users, reverse=True): bad.append("users-high-first.txt is in text order: add -n so 4200 comes before 980")
        elif u == sorted(users, key=int): bad.append("users-high-first.txt is lowest first: add -r")
        else: bad.append("users-high-first.txt is not the sorted users column")
    return bad

def c_uniq(a):
    bad = []
    b = lines(a, "work/blocked-modules.txt")
    if b is None: bad.append("work/blocked-modules.txt missing")
    elif b != sorted(set(mods)): bad.append("blocked-modules.txt must list each module once" + (": sort before uniq" if len(b) > len(tally) else ""))
    c = lines(a, "work/blocker-counts.txt")
    if c is None: return bad + ["work/blocker-counts.txt missing"]
    parts = [l.split() for l in c]
    pairs = [(int(p[0]), p[1]) for p in parts if len(p) == 2 and p[0].isdigit()]
    if len(pairs) != len(c): bad.append("blocker-counts.txt should be uniq -c output: count then module")
    elif pairs == want_pairs: pass
    elif len(pairs) > len(tally): bad.append("blocker-counts.txt: uniq ran on unsorted input, sort before uniq -c")
    elif sorted(pairs, key=lambda p: p[1]) == sorted(want_pairs, key=lambda p: p[1]): bad.append("blocker-counts.txt counts are right but not biggest first: pipe through sort -nr")
    else: bad.append("blocker-counts.txt counts do not match the blockers")
    return bad

def c_diff(a):
    bad = []
    t = text(a, "work/contacts.diff")
    if t is None: bad.append("work/contacts.diff missing")
    elif t == want_fwd: pass
    elif t == want_rev: bad.append("contacts.diff has the input order reversed: old file first, new file second")
    elif not t: bad.append("contacts.diff is empty: those two files differ, check the file names")
    else: bad.append("contacts.diff is not diff of contacts-wiki.txt then contacts-oncall.txt")
    c = lines(a, "work/contacts.txt")
    new, old = (data / "contacts-oncall.txt").read_text().splitlines(), (data / "contacts-wiki.txt").read_text().splitlines()
    if c is None: bad.append("work/contacts.txt missing")
    elif c == old: bad.append("work/contacts.txt is still the wiki copy: edit it in nano until diff against contacts-oncall.txt prints nothing")
    elif c != new: bad.append("work/contacts.txt still differs: run diff work/contacts.txt evidence/contacts-oncall.txt")
    return bad

def c_final(a):
    h = lines(a, "work/handover.txt")
    if h is None: return ["work/handover.txt missing"]
    esc = [f"{n} {m} {oncall[m][0]} {oncall[m][1]}" for n, m in want_pairs]
    want = ["Release: v3.8", None, f"Rule: {active}", f"Blockers: {len(blockers)}", "Escalate (most blockers first):", *esc, f"Largest blocker reach: {max(map(int, users))}"]
    got = [" ".join(l.split()) for l in h]
    if len(got) != len(want): return [f"handover.txt should have {len(want)} lines, it has {len(got)}"]
    bad = []
    for i, (g, w) in enumerate(zip(got, want), 1):
        if w is None:
            if not g.startswith("Prepared by:") or len(g.split()) < 3: bad.append("handover.txt line 2 needs your name")
        elif g != w and 6 <= i < 6 + len(esc):
            gt, wt = g.split(), w.split()
            why = "count" if gt[:1] != wt[:1] else "module order, biggest first" if gt[1:2] != wt[1:2] else "contact or channel, is it the stale wiki entry?"
            bad.append(f"handover.txt line {i}: check the {why}")
        elif g != w: bad.append(f"handover.txt line {i} does not match: check {w.split(':')[0]}")
    return bad

checks = [("0", "evidence", c_evidence), ("1", "history", c_history), ("2", "less", c_less), ("3", "nano", c_nano), ("4", "cut", c_cut), ("5", "sort", c_sort), ("6", "uniq", c_uniq), ("7", "diff", c_diff), ("8", "final", c_final)]

def find_attempt(args):
    given = [x for x in args if not x.isdigit()]
    if given: return Path(given[0]).resolve()
    if os.environ.get("LAB_ATTEMPT"): return Path(os.environ["LAB_ATTEMPT"])
    if (Path.cwd() / "ATTEMPT").exists(): return Path.cwd()
    found = sorted((lab.parent / "attempts").glob("attempt-*"), key=lambda p: int(p.name[8:]))
    return found[-1] if found else None

def main():
    args = sys.argv[1:]
    a = find_attempt(args)
    if not a or not a.is_dir():
        print("no attempt found, run: python3 lab/start.py")
        return 2
    pick = [x for x in args if x.isdigit()]
    todo = [c for c in checks if not pick or c[0] in pick]
    print(a.name)
    fails = 0
    for num, name, fn in todo:
        bad = fn(a)
        print(f"[{num}] {'FAIL' if bad else 'PASS'} {name}")
        for b in bad[:3]: print(f"    {b}")
        fails += bool(bad)
    print(f"{len(todo) - fails}/{len(todo)} passed")
    return int(fails > 0)

sys.exit(main())
