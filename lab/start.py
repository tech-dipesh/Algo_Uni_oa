import shutil
from pathlib import Path

lab = Path(__file__).resolve().parent
data = lab / "data"
attempts = lab.parent / "attempts"
attempts.mkdir(exist_ok=True)
old = sorted(int(p.name[8:]) for p in attempts.glob("attempt-*") if p.name[8:].isdigit())
path = attempts / f"attempt-{max(old, default=0) + 1}"
(path / "evidence").mkdir(parents=True)
(path / "work").mkdir()
for name in ["bugs.csv", "runbook.txt", "contacts-wiki.txt", "contacts-oncall.txt"]:
    shutil.copy(data / name, path / "evidence" / name)
    (path / "evidence" / name).chmod(0o444)
shutil.copy(data / "handover.template", path / "work" / "handover.txt")
(path / "ATTEMPT").write_text(path.name + "\n")
rc = f"""export LAB_HOME="{lab.parent}"
export LAB_ATTEMPT="$PWD"
export HISTFILE="$PWD/.lab_history"
export HISTSIZE=5000
export HISTFILESIZE=5000
unset HISTCONTROL
shopt -s histappend
PROMPT_COMMAND='history -a'
PS1='lab$ '
alias check='python3 "$LAB_HOME/lab/check.py"'
history -c
"""
(path / ".labrc").write_text(rc)
kept = ", ".join(f"attempt-{n}" for n in old)
print(f"{path.name} created" + (f" (kept: {kept})" if old else ""))
print(f"cd {path} && source .labrc")
