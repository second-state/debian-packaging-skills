# Dynamic decision contract

The skill must generate decisions from current evidence. Never hard-code a release version, Debian suite, branch, user, fork or risk result in this contract or in a harness adapter.

## Decision objects

The assistant emits a decision object to the host; the user does not write JSON. A host may render it as buttons, a form, a chat question or an API response.

```json
{
  "id": "debian-target-version",
  "question": "Which candidate should be prepared for Debian?",
  "context": {
    "debian_version": "<observed>",
    "canonical_base": "<observed commit>",
    "upstream_source": "<observed source>",
    "checked_at": "<timestamp>"
  },
  "options": [
    {
      "id": "<upstream-version>",
      "label": "<version> (<Recommended|maintenance|feature|blocked>)",
      "description": "<evidence-based reason>",
      "action": "prepare|analyze-only|stop",
      "risk": "<short risk summary>",
      "evidence": ["<local or authoritative reference>"]
    }
  ],
  "recommended": "<option id or null>",
  "requires_owner": true,
  "scope": "local_preparation_only"
}
```

Required invariants:

- Candidate options come from the current upstream stable release list and the current Debian/canonical package state. Exclude prereleases unless the owner explicitly requests them.
- Each option has a distinct observed version. Do not use a directory name, stale report or prior conversation as the version source.
- The recommendation is evidence-based and may be `null`. A blocked candidate can be shown with `action: analyze-only`, never silently prepared as a publishable candidate.
- The decision object records source references and the observed timestamp. If the source state changes before preparation, invalidate the decision and regenerate it.
- Choosing an option authorizes only the declared scope, normally local preparation. It never authorizes push, MR, email, bug, upload or publication.
- A custom user answer must be normalized into the same object and checked against the current candidate list; an unavailable or ambiguous version stops for clarification.
- The response binds `id`, selected option, candidate version, canonical base and scope. Do not reuse a response for a different version, base, repository or publication action.

## Other decisions

Use the same dynamic object for:

- contributor identity: candidates and sources are detected at runtime; profile login is not a Debian email or upload authority;
- workspace action: new isolated workspace is the default, with resume/cleanup only as explicit choices after inventory;
- material packaging trade-offs: present evidence and `prepare|analyze-only|stop` actions;
- publication: show the exact account, fork, source branch/ref, target project/branch, title, body and evidence digest. This decision requires fresh owner approval for the exact external effect unless existing approval scope demonstrably covers the unchanged action.

## Host adapter behavior

The host receives the object and renders it without changing labels, descriptions, actions, risk or scope. If structured UI is unavailable, render the same content in concise English or the conversation language. Never invent an option or select the recommended option silently when `requires_owner` is true. Cancellation pauses the workflow with no mutation beyond already authorized local work.

A model/delegated response can resolve ordinary implementation choices within existing owner scope, but cannot answer a new version, identity, cleanup, publication or scope decision on the owner's behalf. A host must not turn a login success, `READY_FOR_REVIEW`, plan digest or copied receipt into consent.

## Acceptance cases

- Dynamic upstream list contains a maintenance and a feature release: both are shown, one may be recommended by evidence, no hard-coded version appears in source.
- Latest upstream is blocked: it is shown as `analyze-only`; a safer candidate may be recommended.
- Debian is already current: offer no-op/status rather than fabricate an update.
- Source unavailable: mark freshness unknown and stop or use only owner-approved offline evidence.
- Candidate changes after selection: invalidate response and regenerate options.
- Harness without forms: same object rendered conversationally; no generic "what do you want?" after an explicit bare draft invocation.
- Identity options conflict: show conflict and ask once; never guess.
- Publish object differs from draft: require a new exact approval; never reuse draft approval.
