# debian-packaging-skills

A Claude Code plugin bundling skills for moving an upstream release through
the official Debian packaging path and into Ubuntu. Ships the
`wasmedge-debian-packaging` skill today; more package skills can be added
under `skills/`.

## Install

From a Claude Code session, add the marketplace then install:

```
/plugin marketplace add https://github.com/second-state/debian-packaging-skills
/plugin install debian-packaging-skills@debian-packaging-marketplace
```

Then `/reload-plugins` (or restart) to activate. Once installed the plugin
is available in every project. To work from a local checkout instead, point
the marketplace at the directory:
`/plugin marketplace add /path/to/debian-packaging-skills`.

## Use

Invoke a skill by its namespaced name:

```
/debian-packaging-skills:wasmedge-debian-packaging
```

Claude also loads it automatically when a task matches the skill's
`description`.

## Develop / test without installing

Load the plugin for a single session straight from disk:

```
claude --plugin-dir /path/to/debian-packaging-skills
```

Inspect what the loader sees (skills detected, token cost) without installing:

```
claude --plugin-dir . plugin details debian-packaging-skills
```

## Add another package skill

Copy the skeleton in `templates/package-debian-packaging/` to
`skills/<package>-debian-packaging/`, then replace the package-specific
facts listed in its `references/package-facts.md`. The generic Debian
mechanics are shared — `wasmedge-debian-packaging` is the worked reference
implementation. No manifest change is needed — `plugin.json` and
`marketplace.json` describe the whole plugin, not individual skills.
Reinstall or reload to pick it up.

## Layout

```
.claude-plugin/
  plugin.json         # plugin manifest (name, version, license, author)
  marketplace.json    # marketplace entry (source: "./")
skills/
  wasmedge-debian-packaging/
    SKILL.md          # entry: when to use + workflow
    references/*.md   # deep reference: gbp, ABI/symbols, BTS + MR mechanics,
                      #   post-upload, Ubuntu sync/backport
    scripts/          # preparation helper
templates/
  package-debian-packaging/   # skeleton to copy per new package (not a live skill)
```

## License

MIT — see [LICENSE](LICENSE).

## Contributor workflow

Expose `skills/wasmedge-debian-packaging` through your Pi skill configuration or
user skills directory, then reload skills. No personal checkout path is required.

The skill exposes portable workflow intents: `draft`, `status`, `resume` and `publish`.
A host may map these intents to slash commands, buttons or ordinary conversation;
the repository does not require a particular harness command syntax.

An explicit bare invocation means `draft`: prepare a local contribution through
review, validation and handoff. Automatic skill loading alone does not authorize
execution or publication; follow the user's actual request.

The draft intent prepares a local contribution for review, not just an import.
The assistant detects version choices, workspace and identities and asks only for
missing owner decisions. The publish intent submits the reviewed candidate after checking
Salsa credentials, destination, exact content and explicit publication approval.
Neither intent grants archive-upload rights or permission for unrelated emails.

Local automation uses `scripts/release-workflow.py` with assistant-generated plans
and durable stage results. The user does not fill JSON. See
`references/command-contract.md` inside the skill for the contract and limitations.
Run local tests with `python3 -B -m unittest discover -s tests`.

### Dynamic decisions

Version and workspace choices are generated at runtime from current Debian,
canonical packaging and upstream evidence. The skill does not hard-code release
versions; hosts render the shared decision contract as UI or conversation.
