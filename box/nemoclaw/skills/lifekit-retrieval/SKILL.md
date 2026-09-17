# lifekit-retrieval: online retrieval for queued questions

A question the library cannot answer waits in a queue. When the internet is reachable, the
retrieval program on the box works each queued question: Nemotron names a topic; the
program searches the offline Wikipedia archive for articles on that topic; Nemotron picks
the articles that fit; the program downloads them into the library under a section, writes
a cover for each with Nemotron, and asks Nemotron to answer the question from the
downloaded pages. Each step is written to the event log.

## What runs

- Service: `lifekit` (systemd), `/home/springbuilt/lifekit`, API on port 8008. The retrieval
  program runs inside the service as a thread that wakes when a question is stored and
  every minute while the queue holds questions.
- Model: Ollama on 127.0.0.1:11434, model `nemotron-3-nano`.
- Archive: `/home/springbuilt/lifekit/packs/zim/wikipedia_en_all_nopic_2026-06.zim`.
- Downloaded documents: `/home/springbuilt/lifekit/packs/volumes/<id>/`.
- Event log: table `retrieval_event` in `/home/springbuilt/lifekit/packs/library.sqlite`;
  also `GET http://127.0.0.1:8008/api/events`.

## Commands for the operator

This console advises; the operator runs the commands, because the Nemotron serving
template rejects tool calls in streaming mode.

- Queue: `curl -s http://127.0.0.1:8008/api/digest | python3 -m json.tool | grep -A3 pending`
- Last run's steps: `curl -s "http://127.0.0.1:8008/api/events" | python3 -c "import sys,json; [print(e['at'], e['step'], e.get('topic', e.get('title',''))) for e in json.load(sys.stdin)['events'][-20:]]"`
- Start a run now: `curl -s -X POST http://127.0.0.1:8008/api/sync -H "X-LifeKit-Token: $LIFEKIT_TOKEN" -d '{}'`
- Pause: `systemctl set-environment LIFEKIT_QUEUE_WORKER=off && systemctl restart lifekit`
- Resume: `systemctl unset-environment LIFEKIT_QUEUE_WORKER && systemctl restart lifekit`
- Service log: `journalctl -u lifekit -n 50 --no-pager`
