# Ten-song playback comparison

Run from the repository root using the same Python environment and
`prototype/requirements.txt` as the original experiment.

```sh
# Small APKG containing URLs; no audio download at build time:
python prototype/build_comparison.py --mode remote

# Both variants, fetching the same ten pinned clips for the native package:
python prototype/build_comparison.py --mode both --download

# Rebuild offline from the already downloaded build/previews files:
python prototype/build_comparison.py --mode both
```

Outputs:

- `build/france-original-10-remote.apkg`: ten HTML5 players with remote Apple
  previews, no bundled media. Internet access is required when playing.
- `build/france-original-10-native.apkg`: ten native Anki replay controls using
  the same preview bytes, bundled once per distinct content hash.

Import both into a disposable profile. They appear under **Ultimate Hitster →
France Original Sample → Native / Remote**. These are intentionally separate
notes/models for comparison, so importing both creates 20 cards. They do not
overwrite the original one-card **Playback Prototype**, whose schema, templates,
builder, model ID and deck ID remain unchanged.

Both question sides contain only their audio control. Remote uses a plain
`<audio controls preload="none">`: no autoplay, iframe, SDK, login, external
script, artwork, track labels or metadata attributes. The answer displays year,
title, artist and an optional album. With no album, its paragraph is omitted.
The provider chooses the excerpt; the player does not play the full recording
or choose a timestamp in it.

## Sample

| Card | Artist | Title | Catalogue year |
| --- | --- | --- | --- |
| 1 | The Trammps | Disco Inferno | 1976 |
| 2 | Gipsy Kings | Volare (Nel Blu di Pinto di Blu) | 1989 |
| 3 | Yazoo | Don't Go | 1982 |
| 4 | Elvis Presley | Can't Help Falling in Love | 1961 |
| 5 | Lukas Graham | 7 Years | 2015 |
| 6 | Kendji Girac | Andalouse | 2014 |
| 7 | K.Maro | Femme Like U | 2004 |
| 8 | Alain Souchon | Foule sentimentale | 1993 |
| 9 | Axelle Red | Sensualité | 1993 |
| 10 | Thelma Houston | Don't Leave Me This Way | 1976 |

See [source structure and recording-selection limits](../docs/HITIFY_CATALOGUE.md).
The small fixture deliberately stays outside the production catalogue.

## Import and compare

1. In each deck, play, pause, seek and replay several cards before revealing
   the answer. Confirm no title, artist, year, album or artwork appears early,
   including keyboard focus/accessibility labels.
2. Reveal the answer during playback, then move to the next card. Check whether
   playback stops and whether the replay control works on the answer. HTML5
   elements may restart when Anki replaces the question DOM with the answer.
3. Disable the network. The native package should retain its clips; the remote
   package must not be relied on offline, even if a browser cache sometimes helps.
4. Record latency, seeking behavior, volume, visual layout and error behavior.
   Check night mode and narrow screens. Remote failure is represented by the
   browser's standard audio control; there is no silent fallback to a different song.
5. Grade a card, import a newer build of the **same variant**, and inspect Card
   Info for the existing review. Do not delete the deck to update it.
6. Mobile clients remain unvalidated. Test AnkiDroid and AnkiMobile separately
   after syncing, recording the client/OS version and results rather than
   extrapolating from desktop or engine tests.

Stable GUIDs use immutable sample ID plus the playback variant. Editing metadata,
album or a preview URL retains that variant's GUID. Model IDs are `1735068221`
(native) and `1735068222` (remote); deck IDs are `1735068231` and `1735068232`.
These are disposable experiment identities, not frozen production IDs.

Neither APKG conceals data from someone inspecting its fields or source. The
blind interface keeps metadata out of the normal question display. The media
file itself can contain metadata; avoid OS media integrations when assessing
blind playback.

## Results and tradeoffs, 2026-11-16

| Method | Benefits | Limits | Evidence |
| --- | --- | --- | --- |
| Native Anki, original tone prototype | No runtime network or JavaScript; native replay | Embedded media increases package size | User confirmed import/playback works; client version and detailed checks not recorded |
| Native Anki, ten real previews | Same audio as remote, available locally; content hashes avoid filename collisions | About 11 MB for this sample; AAC/M4A client decoding must be checked | Actual APKG import, media checks and decoding passed; manual playback pending |
| HTML5 remote, ten real previews | Tiny APKG, normal play/pause/seek controls; no provider interface to crop | Network latency, URL changes, webview codecs and browser media behavior; remote files do not sync as Anki media | Ten URLs fetched/decoded; Anki rendering/import tests passed; in-client playback pending |
| Spotify iframe as in Quiz Bowl | Provider handles playback; no bundled files | CSS cropping relies on provider layout and does not remove metadata from the iframe/accessibility tree | Existing reference inspected; not distributed as a blind comparison APKG |

The Spotify variant is deferred because reliable metadata concealment has not
been established. Its 40 × 80 clipped wrapper is a visual technique, not a
guarantee that answers remain undisclosed while focusing controls. The HTML5
experiment avoids that provider UI entirely.

Automated suite: **13 tests pass** (six original, seven comparison tests).
Checks cover ten-card bounds, safe URLs, no question text, conditional escaped
albums, deduplicated media, coexistence with the original note type, stable
updates retaining an actual review, bounded HTML extraction and ID-based URL
refresh with mocked networking. CI builds both schemas using synthetic local
test media; its sample command builds the remote APKG without live downloads.

A separate live Apple ID lookup also returned all ten selected recordings;
no preview URL changed during that refresh on the inspection date.

All ten real clips decoded successfully with FFmpeg as AAC, with measured
durations between 30.000000 and 30.019002 seconds. Imported real packages have
ten cards each; native media checking reports no missing/unused files and remote
has no packaged media. These checks do not prove playback in Anki's GUI.

Browser UI validation could not be completed: this environment blocked the
data-URL test page and then blocked direct playback of the public preview in
the cloud browser. Local headless-browser installation also failed. No browser
playback/layout success or mobile compatibility is claimed. Manual comparison
of the delivered APKGs is the next validation step.

This branch publishes no release, generates no full edition and adds no
general-purpose builder dependency. `deck-builder` remains unchanged.
