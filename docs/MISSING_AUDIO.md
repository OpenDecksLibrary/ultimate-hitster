# Unavailable audio and safe Anki imports

The catalogue keeps every recording, membership, catalogue year and production
study ID. Unavailable/uncertain audio is not replaced with a different recording.
The APKGs retain the corresponding notes/cards but mark their new cards suspended.

## Import options matter

Enable the client's **Import learning progress** / **Include scheduling**
option (wording varies by client) to preserve the suspension state of newly
imported unavailable cards. Automated tests in the Anki engine verify that this
also preserves existing card identities, due dates, intervals, review history
and personal deck placement when updating the published v0.2.0-beta.1 collection.

If learning-progress import is disabled, Anki resets the suspension state of
new cards. The package cannot override that importer choice. Tests cover both
behaviors; do not assume a suspended package alone is sufficient.

After every upgrade, especially from a candidate already imported, open Browse
and search:

~~~text
tag:audio::missing Playback:*unavailable*
~~~

Select those current unavailable cards and use **Toggle Suspend** if they are
active. Check that all selected cards are suspended, then return to ordinary
reviews. Existing cards deliberately retain their user's scheduling during an
APKG update; the release does not forcibly change an existing queue or delete
history. Suspension changes their queue status, not their stored due date,
interval or review log. Do not delete notes/decks to update.

This is required for previously imported active exception cards and for imports
with learning progress disabled. Fresh imports with learning progress enabled
already suspend them automatically.

## Tags can outlive a data correction

Anki can merge tags across imports, so audio::missing alone may also find a card
whose audio was subsequently restored. The combined Playback query above checks
the current field and excludes restored players. Automated tests check this.

To inspect previously missing cards that now have a player but remain suspended:

~~~text
tag:audio::missing -Playback:*unavailable* is:suspended
~~~

Review their current audio and your own suspension intent before unsuspending.
A restored source never automatically unsuspends an existing card. This protects
manual suspension choices and existing progress.

The release's exceptions.json lists remaining study IDs, recording IDs, edition
card numbers, titles, reasons and audio evidence. validation.json records package
counts and fresh-import suspension checks; successive-imports.json records the
actual published-beta upgrade sequence. Checksums cover all three reports and
all ten APKGs.

## Remaining manual checks

The Anki-engine tests are automated. The full v0.3 import controls and playback
still need actual Anki Desktop, AnkiDroid and AnkiMobile results. Direct mobile
APKG import and playback after media sync are separate checks. Physical-card QR
targets and disputed musical versions have not been manually validated. Follow
MANUAL_VALIDATION.md and record actual results rather than inferring success.
