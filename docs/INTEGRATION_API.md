# Public integration index v1 — design contract

Status: proposed implementation contract for #833; not a live endpoint. Consumers: Joomla field and module in jeckodevelopment/operaplus-extensions#1.

## Isolation
Read a coherent, validated published catalog snapshot and its companion channels; verify manifest hashes and counts. Never rewrite v2 manifest, channels, identities, or frontend. New outputs only under public/integrations/v1/. Run an independent workflow on successful publication (and manual dispatch); pin snapshot, serialize integration publications, reject stale overwrite, publish atomically using dedicated allowlisted paths. Do not add a blocking dependency or shared concurrency cancellation to refresh-catalog. On failure retain last known good and report independently. No SFTP deployment required for GitHub-hosted JSON.

## Shape
UTF-8 JSON object: schema_version: 1; source_revision: full commit SHA; catalog_reviewed_on: ISO date from manifest; entities: array sorted by type then id.
Each entity: type (opera|composer|theatre|festival|production), id (opaque stable string scoped by type), title (nonempty), subtitle (string or null), url (canonical public HTTPS URL or null), composer_ids (array of stable composer IDs), image (object or null), fallback_image (object or null), aliases (array of strings). Production optionally has production_kind (staging|group|program); IDs retain existing namespace or use explicit kind prefix to prevent collisions. Do not conflate staging with group or invent routes. Image object: url, alt, source_url, author, license, license_url, credit; required verified rights before reuse. Null means unavailable, never a guessed URL. No season entities or recite entities in v1.

## Source mapping
- opera: works channel, existing id, title, composer; canonical /atlas/opere/{route_slug or slug}/, validated by current routing; poster from existing work-posters companion if reuse rights verified.
- theatre: use published venue directory (including directory-only theatres); reconcile IDs to venues channel where supported, persist mapping if needed, no title-derived ID regeneration; canonical city/venue route from existing prerender rules.
- production: existing stagings (url), production-groups (existing group routes), published programs only when their public route and identity are verified. Keep distinct kinds.
- festival: festival-directory companion; use permanent id, never edition id; canonical /atlas/directory.html?section=festival&id={id}. Historical edition links resolve client-side to the permanent identity. Use registered image subject to rights.
- composer: independent additive registry, stable ID and aliases; derive candidate list from all works, including joint composer credits with explicit editorial disambiguation. No assumptions that a public composer detail route exists. url=null until a verified public route is available. Consumers may select composers but must omit invalid CTA or hide box according to configuration.

## Portrait registry
New data/composer-registry.json and data/composer-portraits.json; do not alter existing canonical catalog. Explicit mappings from work IDs to composer IDs; preserve ambiguous names for editorial review, no automated fuzzy merge. Target all composers represented in Atlas. Prefer verified public domain or compatible licensed portraits; record source, author, license URL, credit, alternate text, review date and reuse restrictions. No image until rights verified. Work box prefers verified composer portrait then verified work image; production prefers verified production art then work art. Theatre/festival use their verified images. No external scraping at Joomla request time.

## Consumer behavior
Fetch fixed trusted HTTPS endpoint using bounded timeouts and size, validate schema, types, IDs, links, image permissions and relationships. Cache last known good independently of failed refresh; never store unvalidated data. Prevent SSRF (no arbitrary endpoints or redirect destinations), escape output. Field stores ordered type+id references and optional primary reference; no copied title/URL. Module resolves at render time, manual/context mode, hides missing entities and never links to nonexistent pages. Unknown additive fields ignored; incompatible major version rejected.

## Acceptance
Deterministic export for same snapshot; unique type/id pairs; referential integrity; canonical route verification, explicit null fallback; tests for malformed inputs, duplicate identifiers, ambiguous composer names, invalid rights, malicious URLs, stale snapshot and failed publication. Compare existing catalog output bytes before/after at same input. Verify independent workflow cannot block or cancel refresh; previous valid index survives failures. Validate actual public endpoint before declaring delivery. No endpoint or workflow implementation included in this documentation PR.
