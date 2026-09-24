# Monitoring

The API exposes unauthenticated liveness at `/health` and authenticated control
plane status at `/api/status`. Production integration should scrape process,
latency, error-rate, registry growth, audit-chain validity, qualification gate,
and shadow-disagreement metrics without recording protected source content.

Alerts should fire on invalid audit chains, failed qualification gates, repeated
unsafe shadow disagreements, unauthorized requests, rollback events, and loss of
protected artifact custody.