# Multi-Agent Coordination Plan

**Created:** 2026-02-21
**Status:** Approved for phased implementation

---

## Phase Roadmap

```
Phase 1 (done)      : Supervisor + one-shot SubAgentTool
Phase 2 (near-term) : TaskGraph executor (sequential + parallel)
                      Shared agent context store
                      Propagated trace IDs across all events
Phase 3 (mid-term)  : Remote agent HTTP adapter (A2A-compliant)
                      Durable task store (survive process restarts)
Phase 4 (future)    : Event bus for fully async / distributed agents
```

---

## Scenarios to Handle Across All Phases

### Group 1 — Delegation Topology
| # | Scenario | Phase |
|---|---|---|
| 1 | Sequential pipeline (A → B → C) | 2 |
| 2 | Parallel fan-out (master spawns N agents simultaneously) | 2 |
| 3 | Fan-in / reduce (merge results from parallel agents) | 2 |
| 4 | Deep nesting (A → B → C, 3+ hops) | 2 |
| 5 | Peer-to-peer (agents call each other without a master) | 3 |
| 6 | Dynamic routing (next agent chosen by intermediate result) | 2 |

### Group 2 — State & Continuity
| # | Scenario | Phase |
|---|---|---|
| 7 | Long-running async task (user disconnects, reconnects) | 3 |
| 8 | Shared working memory across agents | 2 |
| 9 | Session resumption after process restart | 3 |
| 10 | Mid-task handoff (partial output from one agent to next) | 2 |

### Group 3 — Human-in-the-Loop Inside Chains
| # | Scenario | Phase |
|---|---|---|
| 11 | HITL inside a deep chain (SubAgent-3 needs approval) | 2 |
| 12 | Multiple agents waiting for user simultaneously | 3 |
| 13 | User redirects mid-chain | 2 |
| 14 | Timeout on human response | 1 (done) |

### Group 4 — Coordination Patterns
| # | Scenario | Phase |
|---|---|---|
| 15 | Critic-author loop (generate → score → refine) | 2 |
| 16 | Consensus / voting (N agents evaluate, majority decides) | 3 |
| 17 | Competitive execution (race N agents, take first success) | 2 |
| 18 | Map-reduce (split data, parallel process, merge) | 2 |

### Group 5 — Failure & Recovery
| # | Scenario | Phase |
|---|---|---|
| 19 | Sub-agent timeout | 1 (done) |
| 20 | Cycle detection | 1 (done) |
| 21 | Cascading failure + rollback | 2 |
| 22 | Output type mismatch between agents | 2 |
| 23 | Partial success (7 of 10 parallel agents succeed) | 2 |

### Group 6 — Observability & Control
| # | Scenario | Phase |
|---|---|---|
| 24 | Distributed tracing (trace_id across all hops) | 2 |
| 25 | Per-agent rate limiting and cost quotas | 3 |
| 26 | Streaming partial results from deep chains | 2 |
| 27 | Audit trail / chain replay | 3 |

---

## Non-Negotiable Design Rules (All Phases)

1. Every task in every hop carries the same `trace_id` — required for debugging
2. HITL (`INPUT_REQUIRED`) always bubbles up to the top-level caller — never swallowed
3. Cancellation propagates down the full chain — if master is cancelled, all subtasks are
4. Cycle detection is registry-level, not per-agent
5. Streaming works end-to-end — users see output from deep agents incrementally

---

## Phase 2 — Details

See `specs/phase2-task-graph.md` for full implementation breakdown.

---

## Approach Decision

**Chosen: Hierarchical Supervisor + Shared Context Store**

Builds directly on existing architecture (ReAct + A2A events + in-process agents).
No architectural break. Grows into message-queue / actor model later if needed.

Alternatives considered and rejected for now:
- **DAG executor only**: too static for dynamic routing
- **Event bus**: correct long-term, too big a jump from current state
- **Actor model**: right direction but requires framework investment not justified yet
