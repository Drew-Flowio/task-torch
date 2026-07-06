# Offgrid Minds Engineering Rules

These rules govern implementation work under the approved Offgrid Minds architecture and the company Constitution.

- Raw Sources are immutable.
- Every Knowledge Object has a permanent UUID.
- Every relationship has an ID.
- Every transformation is reversible.
- Every operation is logged.
- Every Knowledge Object has provenance.
- Every Expert Pack must be reproducible.
- Never optimize away evidence.
- Never duplicate canonical knowledge.
- Prefer simple implementations first.
- Every feature should be Pi 5 friendly.
- Profile before optimizing.

## Implementation Defaults

- Use small, replaceable modules.
- Prefer standard library dependencies until a concrete need appears.
- Keep storage layers separate even when they share one local database.
- Make audit logs append-only.
- Treat missing provenance as a blocker.
- Do not implement future phases inside the current milestone.
