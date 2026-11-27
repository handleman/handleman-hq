# Green means evidence, not a model's prose

A task is green only when the recorded gate exits are 0 at the final delta, the
reviewer passed, and the verifier did not block. We rejected letting a model
judge be the source of truth: a cheap reviewer once blocked a green task with no
evidence, and a verifier once spent its turn on tool calls and its `unknown`
verdict fell through as a pass. Judges now fail closed, and evidence is
re-verified at save time. The cost is that every green run must carry a
transcript and a delta hash, and a model that cannot answer stops the run
instead of guessing.

**Considered:** LLM-as-judge as the primary signal (rejected: ungrounded),
trusting the coder (rejected: no evidence), one test command (rejected: gates
include lint/type/e2e).
