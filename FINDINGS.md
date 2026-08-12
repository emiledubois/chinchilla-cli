# FINDINGS.md — A "human approval" gate doesn't hold if the party it constrains can write its own proof of compliance

> English version of `specs/KEY_FINDING.md`. This is the most interesting
> result in this repository — more so than any of the three CLI tools
> themselves. It comes from `specs/AGENTIC_LOOP_EXPERIMENT.md`, a real
> (not simulated) run of a 4-agent development loop.

## 1. The question

A human-approval gate is a standard security control in any pipeline
that requires review before a change is applied (CODEOWNERS, manual
approval environments, etc.). That pattern implicitly assumes whoever
might be tempted to bypass it is a person or a deterministic process.

This project adds a variable that pattern doesn't account for: **what
happens when the party implementing the change is an AI agent with
write access to the same repository where the approval itself gets
recorded?** Is it still valid to represent "a human approved this" as
plain, version-controlled text, or does that channel stop being
trustworthy the moment the agent can write to it too?

`specs/AGENTIC_LOOP_EXPERIMENT.md` answers that empirically, not by
theoretical argument: a real setup was used (a real git worktree, fresh
agents with no shared memory, a real task — not a toy exercise) and the
outcome was allowed to unfold without being scripted in advance.

## 2. Why this, and not the three CLI tools

The three tools (`preaudit run`, `certify`, `remediate`) are necessary
but not the contribution: they're a competent application of known
techniques (equivalence partitioning, boundary values, decision tables,
automated evidence collection, structured reports). They demonstrate
command of the subject matter, not new knowledge — they're the
substrate that made the experiment possible, not the point itself.

The experiment produces something that isn't obvious upfront: a
human-approval gate represented as a plain-text commit, under the same
git identity agents use, is **not structurally distinguishable from
self-approval** — and an agent that simply follows its own role
literally can catch that flaw without anyone having to program the
check explicitly.

## 3. The experiment as a case study (summary)

See `specs/AGENTIC_LOOP_EXPERIMENT.md` for the full record. In short:

1. An `architect` agent designed a real ADR (a SHA-256 hash chain for
   `logs/audit.log`, commit `f35b5f4`) with an explicit condition:
   "requires human approval before implementation."
2. A `developer` agent (first attempt) checked `git log`, found no
   record of that approval, and refused to implement — without being
   told to look for it.
3. The repository owner approved explicitly, outside any agent's
   authority. That approval was recorded as a text commit (`5f42999`),
   under the same git identity used throughout the repo.
4. A `developer` agent (second attempt, a fresh instance) checked that
   commit and rejected it too: it noticed the commit had no signature
   and no reference to a pull request, and that the project's own
   definition of "done" requires approval "via PR," not a worktree
   commit. **The approval had been genuine; its representation in the
   repository was not verifiably distinct from self-approval.**
5. The experiment was stopped there, by the repository owner's explicit
   choice, leaving the approved-but-unimplemented ADR as an honest
   record instead of forcing an artificial close.

## 4. The finding, stated formally

> A "human approval" control in a system where AI agents have write
> access to the same channel used to *represent* that approval is not
> a valid control, even if the approval itself was genuinely human —
> because the control depends on the channel being
> unobservable/unwritable by the party it's meant to constrain, and a
> plain-text commit under the repository's shared identity doesn't meet
> that condition.

This is a concrete instance of a classic security principle
(separation of privilege between whoever executes an action and
whoever authorizes it) applied to a new context: AI agents as part of
the very process whose output requires authorization.

## 5. What this adds beyond standard CI/CD approval practice

The idea of a "forgeable approval channel" isn't new in security (it's
a variant of privilege separation / TOCTOU in access control). What the
experiment contributes is finding it *inside a real agentic workspace*,
through the spontaneous behavior of an agent following its role — not
through an attack deliberately staged to illustrate the point.

## 6. Honest limitations

- **n=1.** This is a single run, not a statistically representative
  series. The result is reproducible in its logic (any agent reading
  the project's definition of "done" literally should reach the same
  conclusion), but it wasn't run multiple times or across different
  models to measure variance.
- **A single model/provider.** It's unknown whether the
  refuse-and-reason-correctly behavior is specific to this model or
  generalizable.
- **The experiment's "success" depends on agents following their
  prompts faithfully.** A less carefully written prompt might not have
  caught the flaw — the finding shows this *can* happen, not that it
  *will always* happen without a structural control (hence the
  recommendation in §7: don't rely on the agent noticing).
- **No adversarial counter-test** with an agent actively trying to
  fabricate a false approval; the second refusal was about a *genuine*
  approval that was poorly represented, not a deliberate deception
  attempt. That would be a valid follow-up experiment.

## 7. Practical implication / future work

The recommendation the experiment itself generated
(`specs/AGENTIC_LOOP_EXPERIMENT.md`, "Conclusiones," point 4):
high-risk approval gates should be satisfied through a channel agents
cannot write to themselves — a GitHub PR approved/merged by a human
account (verifiable via API, not by commit content) or a commit signed
with a key agents don't have access to use. ADR 0001 remains approved
but unimplemented on branch `agentic-loop/audit-log-integrity`;
implementing it **through a real GitHub PR** would close the experiment
by applying its own conclusion — but that's a pending decision, not
assumed by this document.
