# Maintainers Onboarding

## Goal

Keep code, workflows, containers, and docs aligned.

## Alignment checklist

For every user-visible change:

* CLI option changes in Python tools are mirrored in CWL inputs
* docs reflect current behavior and defaults
* examples and notebooks remain coherent with current interfaces

## High-risk drift points

* `stac-zarr` CLI flags vs `app-water-bodies.cwl` `stac-zarr` inputs
* `stac-eopf-product` CLI flags vs `app-water-bodies.cwl` `stac-eopf-product` inputs
* STAC/Zarr conventions described in docs vs emitted metadata
* workflow output expectations in consumer tooling

## Release hygiene

Before publishing:

* run scoped unit tests
* run release-oriented CWL checks
* verify CWL fields and defaults for new parameters
* verify MkDocs navigation includes new pages
* review docs for behavior/default mismatches

Recommended commands:

```bash
task test:unit:scoped
task cwl:check:release
task compliance:check:all
task containers:build:all
```

## Ownership recommendation

Treat these artifacts as one change set whenever touching Zarr output behavior:

* `command-line-tools/stac-zarr/stac_zarr/app.py`
* `cwl-workflow/app-water-bodies.cwl`
* `docs/input-stac.md`
* `docs/compliance/stac-zarr-best-practices.md`
* `docs/on-boarding/developers.md`
* `docs/on-boarding/eoap-users.md`
* `docs/on-boarding/maintainers.md`
