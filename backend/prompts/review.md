## Automatic review of a learner edit

This turn is an automatic review, not a conversation. The learner saved their own wording on node `review_node_id`. Review only that node's exact saved label and description against the sources, then call `review_edit` once:

- `agree` when the label and description are supported. Keep their wording exactly; brevity or missing optional detail is not a mistake.
- `corrected` when it contains a misconception. `said` must quote their saved label or description exactly; `actually` is one short supported correction.
- `remove` when the idea is not in the material at all. The node stays until the learner confirms.

Change no other node. The answer is one or two sentences beginning with "Agreed:", "Corrected:" or "Proposed deletion:". Ask no question.
