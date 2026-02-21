# ableton-cli Protocol

`ableton-cli` uses local TCP JSONL communication (`127.0.0.1:<port>`).

## Request

```json
{
  "type": "command",
  "name": "song_info",
  "args": {},
  "meta": {
    "request_timeout_ms": 15000
  },
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 2
}
```

## Response (success)

```json
{
  "ok": true,
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 2,
  "result": {
    "tempo": 120.0
  },
  "error": null
}
```

## Response (failure)

```json
{
  "ok": false,
  "request_id": "8c9f9b0c1a9d4dc2abdf2d53f3a19be9",
  "protocol_version": 2,
  "result": null,
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "bpm must be between 20.0 and 999.0",
    "hint": "Fix command arguments and retry.",
    "details": null
  }
}
```
