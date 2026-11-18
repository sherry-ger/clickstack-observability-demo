SELECT Timestamp, ServiceName, SeverityText, Body, TraceId,
       ResourceAttributes['container.name'] AS container_name,
       ResourceAttributes['container.id'] AS container_id,
       LogAttributes['docker.event.action'] AS action,
       LogAttributes['docker.event.exit_code'] AS exit_code,
       LogAttributes['event.provider'] AS provider,
       LogAttributes['event.id'] AS event_id
FROM default.otel_logs
WHERE toStartOfFiveMinutes(Timestamp) >= toStartOfFiveMinutes({start:DateTime64(9)})
  AND ServiceName = 'docker-events'
  AND Timestamp >= {start:DateTime64(9)} AND Timestamp < {end:DateTime64(9)}
  AND ResourceAttributes['container.id'] = {container:String}
  AND LogAttributes['docker.event.action'] IN ('oom', 'die', 'start')
ORDER BY Timestamp
LIMIT 20
