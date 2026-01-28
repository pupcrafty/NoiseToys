## Phrase Detection (Removed)

The phrase inspector subsystem (`PhraseInspector` and `audio_service/phrase_inspector.py`) has been removed
from the project. The runtime now only exposes beat/tempo and raw audio feature data; no phrase states or
phrase score signals are produced or visualized anymore.

This file is kept only as a short note so that any older references to the phrase logic don’t cause confusion.
