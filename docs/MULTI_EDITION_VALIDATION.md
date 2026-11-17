# Multi-edition validation snapshot

Source import checked on 2026-11-16. This is automated source/audio evidence,
not a manual Desktop/mobile or physical-card validation result.

## Coverage

| Measure | Result |
| --- | ---: |
| Hitify editions inventoried | 175 |
| Editions imported | 3 (1.7% of the registry) |
| Catalogue card occurrences | 924 |
| Unique recordings | 643 |
| Unique Anki study facts | 643 |
| Repeated occurrences sharing existing studies | 281 |
| Recordings appearing more than once | 278 |
| Records with optional album metadata | 643 |
| Recordings with downloaded and decoded MP3 evidence | 631 |
| Unique MP3 content hashes | 630 |
| Records without enabled audio | 12 |
| Conflicting catalogue years in this actual selection | 0 |

| Edition | Catalogue cards | Shared recordings with other imported editions |
| --- | ---: | ---: |
| hitster-guilty-pleasures-france | 308 | 3 |
| hitster-original-france | 308 | 278 |
| hitster-original-refresh-france | 308 | 278 |

The Original/Refresh overlap contains 278 exact Spotify identities. The Original
family union contains 338 studies. France and the entire imported catalogue
currently select the same 643 studies because only French editions were imported.
The generator still supports other countries; country/deck interactions are also
exercised with independent synthetic French/Belgian fixtures. No Belgian edition
is claimed imported. Radio Contact remains in the available registry, but the
complementary per-card source did not cover it.

For both new editions, all 308 source IDs were resolved as exact Spotify track
pages, and every publicly exposed playlist position (100 per playlist) matched
the complementary source. This partial positional check does not certify the
other 208 physical QR codes. No recording was selected by title search.

There are 905 verified memberships, seven existing explicit version-label reviews,
eight source metadata conflicts and four provider metadata mismatches. A matching
ID/title is metadata evidence, not a manual comparison of musical masters.
The twelve uncertain memberships are retained below. Six are shared with a
verified Original France study; the shared player uses that exact study's known
audio in every package while the edition disagreement stays flagged. No alternate
recording is substituted.

## Uncertain edition references

| Edition | Card | Catalogue title | Provider title | Status |
| --- | ---: | --- | --- | --- |
| hitster-original-refresh-france | 110 | La Bamba | La Bamba - Single Version | source_conflict |
| hitster-original-refresh-france | 171 | Lean On (feat. MØ & DJ Snake) | Lean On | metadata_mismatch |
| hitster-original-refresh-france | 182 | The Ketchup Song (Aserejé) | The Ketchup Song (Aserejé) - Spanglish Version | source_conflict |
| hitster-original-refresh-france | 232 | Happy | Happy - From "Despicable Me 2" | source_conflict |
| hitster-original-refresh-france | 242 | Get Lucky (feat. Pharrell Williams and Nile Rodgers) | Get Lucky (Radio Edit) [feat. Pharrell Williams and Nile Rodgers] | source_conflict |
| hitster-original-refresh-france | 275 | Under Pressure | Under Pressure - Remastered 2011 | source_conflict |
| hitster-guilty-pleasures-france | 26 | Crying at the Discoteque - Radio Edit | Crying at the Discoteque | metadata_mismatch |
| hitster-guilty-pleasures-france | 221 | Jamais nous | Jamais nous | source_conflict |
| hitster-guilty-pleasures-france | 225 | Yeah! | Yeah! (feat. Lil Jon & Ludacris) | source_conflict |
| hitster-guilty-pleasures-france | 228 | Hotel California | Hotel California - 2013 Remaster | source_conflict |
| hitster-guilty-pleasures-france | 241 | Say You'll Be There | Say You'll Be There - Single Mix | metadata_mismatch |
| hitster-guilty-pleasures-france | 297 | Copacabana (At the Copa) | Copacabana (At the Copa) - Short Version | metadata_mismatch |

Canonical display labels are shown above. The exact edition labels and source
values remain in each membership/snapshot. Metadata disagreements require review;
version labels such as Live, Radio Edit and Remaster are not stripped to manufacture
a match. The original seven v0.2 reviews remain separate and still require their
previously documented physical-edition listening checks.

## Records without enabled audio

| Artist | Title | Reason |
| --- | --- | --- |
| Elsa | Jamais nous | metadata_mismatch |
| Eagles | Hotel California | metadata_mismatch |
| Worlds Apart | Baby Come Back | provider_no_preview |
| Alcazar | Crying at the Discoteque - Radio Edit | metadata_mismatch |
| L5 | Une étincelle | provider_no_preview |
| Village People | YMCA | provider_no_preview |
| Barry Manilow | Copacabana (At the Copa) | metadata_mismatch |
| USHER, Lil Jon, Ludacris | Yeah! | metadata_mismatch |
| Kana | Plantation | provider_no_preview |
| Jena Lee | Je Me Perds | provider_no_preview |
| L5 | Question De Survie | provider_no_preview |
| Spice Girls | Say You'll Be There | metadata_mismatch |

Six exact provider references expose no preview. Six further records are blocked
by metadata/artist/version uncertainty. These rows remain in validation APKGs with
a neutral player without a source. Strict missing_policy:error builds refuse them.
Albums are optional provider metadata and do not replace the catalogue year.

One MP3 hash is shared by two distinct pinned recording IDs. Packaging includes
the bytes once. An identical excerpt alone is not sufficient evidence to merge
the complete recordings or their study identities.

## Automated and manual evidence

The candidate workflow generates online/offline APKGs, per-selection counts,
SHA-256 sums and validation.json. It checks complete mode-switch imports and
successive overlapping imports starting with the published v0.2.0-beta.1 online
APKG, pinned by SHA-256. Tests compare actual review history, scheduling and user
deck placement. Unit tests cover conflicting years (none occur in this snapshot),
unknown references, missing previews, distinct IDs/versions and media reuse.

Consult the successful workflow's validation.json for exact run/commit results;
this document does not infer a successful run before it completes.
Desktop full-selection playback, AnkiDroid, AnkiMobile, physical QR verification
and listening to disputed versions remain pending. Follow MANUAL_VALIDATION.md.
v0.3.0-beta.1 is not published by this PR.
