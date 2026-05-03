# Anime Remix Workflow

Use the remix workflow only with cleared, private test, or original material. Register rights metadata in the manifest before sharing outputs outside private verification.

## Forms

- `anime-club`: intro, verse chop, build, chorus drop, breakdown, final drop, outro.
- `anime-dnb`: intro, pre-drop vocal, drop, bridge, second drop.
- `anime-future-bass`: intro pad, vocal verse, build, supersaw drop.

## Practical Order

1. Initialize the manifest.
2. Register vocal and instrumental stems as absolute paths.
3. Import a manual section map.
4. Generate a plan with `remix plan`.
5. Inspect `remix apply --dry-run`.
6. Apply only after confirming the Live Set and target tracks.
7. Run `remix qa`.

The first implementation favors manual section and stem registration. Automatic analysis and external separation are provider interfaces and can be expanded without changing the manifest contract.
