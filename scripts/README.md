The profile has desktop and mobile SVG layouts with a shared vector character.

Edit `content/profile.md`, then regenerate both layouts:

```sh
python3 -m pip install -r scripts/requirements.txt
python3 scripts/build_profile.py
```

The generator also writes `content/journey.json`, which records the paragraph
platforms and movement segments for previews. The character geometry and poses
live in `scripts/runner.py`. `assets/hero.svg` supplies the animated graph.

After committing regenerated assets, pin the README to that asset commit:

```sh
python3 scripts/build_profile.py --write-readme --ref FULL_ASSET_COMMIT_SHA
```

Commit the README afterward. Immutable image URLs prevent stale GitHub image
caches from showing the previous animation. Native social and project links,
plus a selectable transcript, appear below the illustration because SVG images
cannot interact with GitHub's surrounding Markdown.

The graph loops. The runner makes one journey through the profile, takes three
breaths, and freezes in its final standing pose. Reduced motion renders the
static graph and final character instead.
