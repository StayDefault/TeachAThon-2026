# Dyscover interactive workflow

Interaction is continuous: the learner can ask, inspect, revise, arrange, and review the conversation throughout a study thread. These branches describe available actions, not mandatory interaction-mode buttons.

```mermaid
flowchart TD
    A["Open Dyscover and sign in"] --> B{"New or saved session?"}
    B -->|New| C["Upload files and start studying"]
    C --> D["Extract sources and show one topic node"]
    B -->|Saved| E["Restore materials map and full conversation"]
    D --> F{"What does the learner want to do next?"}
    E --> F
    F -->|Ask or explain| G["Speak or type"]
    G --> H["Use source passages map and recent dialogue"]
    H --> I["Explain review understanding or expand missing topics"]
    I --> J["Validate and save the answer and map changes"]
    J --> K["Present speech one-line captions and visible map feedback"]
    K --> F
    F -->|Expand a branch| AD["Read all sources and add the complete immediate level in one batch"]
    AD --> AE["Show all child topics in the branch panel"]
    AE --> AF{"Choose the next interaction"}
    AF -->|Select a child and expand it| AD
    AF -->|Learn this topic| G
    AF -->|Inspect a child silently| L
    F -->|Inspect| L["Open a node silently and clear New"]
    L --> M["Read its explanation citation or original source"]
    M --> F
    F -->|Arrange| N["Move nodes or arrange branches"]
    N --> O["Update presentation without content review"]
    O --> F
    F -->|Create or edit content| P["Save learner wording and mark Edited"]
    P --> Q["Automatically queue a source-based review"]
    Q --> R{"Review result"}
    R -->|Agreed| S["Keep learner wording and clear Edited"]
    R -->|Corrected| T["Show the actual learner claim and supported correction"]
    R -->|Proposed deletion| U["Retain the node and show crosslines with a reason"]
    R -->|Review failed| V["Retain the saved edit and show the error"]
    S --> W["Save review feedback in Conversation"]
    T --> W
    U --> W
    W --> F
    V --> F
    F -->|Decide on a removal| X["Open the proposed node"]
    X --> Y{"Keep or confirm deletion?"}
    Y -->|Keep| Z["Clear the proposal and retain the content"]
    Y -->|Confirm deletion| AA["Remove the node and descendant branches"]
    Z --> F
    AA --> F
    F -->|Read the dialogue| AB["Open the session-wide Conversation panel"]
    AB --> F
    F -->|Pause or leave| AC["Retain saved progress for reopening"]
    AC --> E
```

The current prototype applies ordinary validated additions and corrections directly. Only deletion has a required confirmation step. Captions roll within one line, while complete messages remain in Conversation. Tutor-explained source-supported ideas are mapped immediately. Explicit expansion reveals a complete immediate branch level; the learner then chooses a child to expand or returns to learning. Moving a node and opening a node do not trigger tutor review.

See [the interactive design architecture](DESIGN_ARCHITECTURE.md) for responsibilities, review sequencing, state meanings, and current limitations.
