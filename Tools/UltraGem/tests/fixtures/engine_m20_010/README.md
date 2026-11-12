# Engine ENG-M20-010 content-metadata fixtures (vendored, read-only)

Byte-exact copies of `Packages/com.match3.engine/Tests/Editor/Fixtures/ContentMetadata/*.json`
from `Sekiph82/MATCH3_ENGINE` at commit `5f5aaac37a844b2d152dcc1a07e0c962a1b47ace`
(last change to these fixtures / `Runtime/LiveOps/ContentMetadataReceiver.cs` at or before that
commit: `767b1968501117d780093b30a8551f60645b6998`). Copied with `git show <sha>:<path>`; `.meta`
files omitted. `.gitattributes` keeps them byte-exact (no CRLF conversion).

The Engine is authoritative. Do not edit these files; re-vendor from a newer Engine commit and
update this SHA and `ENGINE_CONTRACT_SHA` in `Tools/UltraGem/engine_envelope.py` together.
Used by `Tools/UltraGem/tests/test_engine_envelope.py`.

Verify: `git hash-object <file>` here must equal the Engine blob id below.

| file | Engine git blob |
|---|---|
| bad_schema_major.json | 5b844735399aab9b9af54d6d2b570d2114d4308c |
| dangling_level_ref.json | b476724c0cf29184e0dbffcce8a52f683e7bfdff |
| digest_mismatch.json | c94f34f2dedc15c18840b5e1beed7635c7fe1d75 |
| duplicate_content_id.json | 9a14240c19f9b7862226ee2f2569da9317f9ef71 |
| duplicate_json_key.json | 79fd98b12d0bf914c16ba2e3ef003952a1806b81 |
| forbidden_price_field.json | 5e9b4f09b2f2cae87b13e60e281664b5d0d7cf47 |
| inverted_window.json | b4b4fb8bf56e611099591b93767d7282d99510d6 |
| non_integer_number.json | 9ff3e2f5eafd3ef538c755f6b0d3d85e1f1688d3 |
| unknown_kind.json | df96a0eb81a1568be0486b1771bd88c43ea6a09b |
| unknown_payload_field.json | 70684f03d2bd35c262abdc19d93258a61ecbc4eb |
| unknown_top_level_field.json | cfc3ab7898adad5d1dc15dcbf3c968a459fe4d07 |
| valid_event.json | 23c4a956339aa039150f6aac817b850ce125df39 |
| valid_level.json | 859506f6580b447881a7b0fc2f5878ce189ea70e |
| valid_world.json | 50cb881f0d849569f7ed2a56e3b2e4b9784343a9 |
| wrong_game.json | 578ac211e16bf68a1fe61c113e279179f3d18b32 |
