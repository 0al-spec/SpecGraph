# Deprecated Bootstrap Task Index

`tasks.md` is no longer the active SpecGraph backlog.

The current backlog should be read from derived graph surfaces, especially
`runs/graph_backlog_projection.json`, after rebuilding it with:

```sh
python3 tools/supervisor.py --build-graph-backlog-projection
```

Completed bootstrap task history is preserved in
[`tasks_archive.md`](/Users/egor/Development/GitHub/0AL/SpecGraph/tasks_archive.md).

This file remains only as a stable compatibility path for older specs, docs,
and tooling that still mention `tasks.md`. Do not append new work items here;
new durable work should be represented through canonical specs, proposals, and
derived graph artifacts.
