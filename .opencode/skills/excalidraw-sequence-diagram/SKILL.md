---
name: excalidraw-sequence-diagram
description: Use when creating or extending Excalidraw sequence diagrams for service flows, including lifelines, message arrows, flow group containers, note boxes, and color-coded swim lanes. Produces valid Excalidraw JSON that renders correctly — arrows visible, z-order correct, labels bound.
---

# Excalidraw Sequence Diagram

## Overview

Produces Excalidraw JSON for UML-style sequence diagrams: vertical lifeline bars, color-coded dashed flow group containers, forward and return arrows with bound labels.

The most common failure modes are invisible arrows (z-order wrong), missing lifeline bars (only label created), and unbound labels (not linked to their arrow). This skill documents the exact field values and ordering rules that prevent them.

---

## Mandatory field values

These fields have caused incorrect output across multiple projects. Every element must use exactly these values — no exceptions:

| Field | Required value | Never use |
|---|---|---|
| `fillStyle` | `"solid"` | `"hachure"` |
| `strokeWidth` on arrows | `2` | `1` |
| `strokeWidth` on flow group containers | `1` | any other |
| `strokeWidth` on lifeline bars | `2` | `1` |
| `roughness` | `1` | any other |
| `fontFamily` | `5` | any other |
| `opacity` | `100` | any other |
| `angle` | `0` | any other |
| `elbowed` on regular arrows | `false` | `true` |
| `elbowed` on self-loop arrows | `true` | `false` |

---

## Z-order — the invisible arrow problem

Excalidraw uses **two** mechanisms for render order — both must be correct simultaneously:

1. **Array position** — elements later in the `elements` array render on top
2. **`index` field** — a fractional-index string (`"a0"`, `"a1"`, `"b0"`) that also controls z-order; higher string = rendered on top

Lifeline bars have a solid fill. Any arrow with a lower `index` than a bar will be painted over and become invisible — appearing only after a double-click.

**Required array order and index order:**

```
Position    index range    Elements
────────    ───────────    ─────────────────────────────────────
1–2         a0–a1          Diagram title + description texts
3–N         a2–aN          Lifeline label texts (one per participant)
N+1–M       b0–bM          Lifeline bar rectangles (one per participant)
M+1–P       c0–cP          Flow group containers (dashed rectangles)
P+1–Q       d0–dQ          Flow group label texts
Q+1–R       e0–eR          Arrows (ALL arrows — forward + return)
R+1–S       f0–fS          Arrow label texts (containerId-bound)
S+1–T       g0–gT          Note box rectangles (if any)
T+1–U       h0–hU          Note box texts (if any)
```

Assign `index` values in strict ascending order. **Arrows must have a higher `index` than all lifeline bars.** Never give an arrow an `index` below `"e0"`.

---

## Coordinate system

- Origin is top-left. Positive x goes right, positive y goes down.
- Lifelines are spaced ~190px apart horizontally.
- Messages (rows) are spaced ~40px apart vertically within a block.
- Minimum gap between blocks: 80px. If a block has long arrow labels, use 100px. The label above the first arrow needs room — never place the next block's first arrow closer than 80px below the previous block's last arrow.
- Each flow group container starts 40px above its first arrow row (space for the group label).

### Vertical spacing budget per block

```
group_start_y  = previous_group_end_y + 80   // 80px gap between blocks
first_row_y    = group_start_y + 40           // 40px for the group label
next_row_y     = previous_row_y + 40          // 40px per message row
group_end_y    = last_row_y + 20              // 20px padding at bottom
group_height   = group_end_y - group_start_y
```

If any arrow label wraps to multiple lines, add 20px extra to that row and expand `group_height` accordingly.

### X position formula

```
center_x(n) = start_x + (n × 190)    // n = 0-based participant index
bar_left_x  = center_x - 17
```

The leftmost participant's `center_x` is typically around -190 or 0 — choose a value that places the diagram comfortably in the canvas. The diagram width grows with participant count; there is no fixed maximum.

---

## Element catalog

### 0. Diagram title block

Every diagram must have a title and a description above the lifeline headers.

```json
// Title (fontSize: 28)
{
  "type": "text",
  "x": <left_edge>,
  "y": <top_of_diagram>,
  "fontSize": 28,
  "fontFamily": 5,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "textAlign": "left",
  "verticalAlign": "top",
  "containerId": null
}

// Description (fontSize: 16, placed 36px below title)
{
  "type": "text",
  "fontSize": 16,
  "strokeColor": "#868e96"
  // same other fields as title
}
```

### 1. Lifeline bar (mandatory — the vertical line)

> **Every participant needs exactly two elements: one bar rectangle + one label text. The bar is the vertical line. If you skip it, the lifeline disappears. Never generate only the label.**

```json
{
  "type": "rectangle",
  "x": <center_x - 17>,
  "y": <header_bottom_y>,
  "width": 35,
  "height": <total_diagram_height>,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#e9ecef",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "roundness": { "type": 3 },
  "boundElements": [],
  "link": null,
  "locked": false
}
```

One rectangle per participant. `height` must span from `header_bottom_y` to the bottom of the last flow group plus 40px.

### 2. Lifeline label

```json
{
  "type": "text",
  "x": <center_x - (estimated_width / 2)>,
  "y": <header_top_y>,
  "fontSize": 20,
  "fontFamily": 5,
  "strokeColor": "#1e1e1e",
  "textAlign": "left",
  "verticalAlign": "top"
}
```

### 3. Flow group container

```json
{
  "type": "rectangle",
  "x": <diagram_left_edge>,
  "y": <group_start_y>,
  "width": <diagram_width>,
  "height": <group_height>,
  "strokeColor": "<group_color>",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "strokeStyle": "dashed",
  "roughness": 1,
  "roundness": null
}
```

Paired with a label text at `x = left_edge + 10`, `y = group_start_y + 5`, `fontSize: 20`, same `strokeColor` as the container.

### 4. Message arrow (forward call)

```json
{
  "type": "arrow",
  "x": <from_center_x + 17>,
  "y": <row_y>,
  "width": <to_center_x - from_center_x - 34>,
  "height": 0,
  "angle": 0,
  "strokeColor": "<message_color>",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "roundness": { "type": 2 },
  "boundElements": [{ "id": "<label_id>", "type": "text" }],
  "startArrowhead": null,
  "endArrowhead": "arrow",
  "elbowed": false,
  "points": [[0, 0], [<width>, 0]]
}
```

**Width formula:**
```
Adjacent participants (190px spacing): width = 190 - 34 = 156
Skipping N lifelines: width = (N × 190) - 34
```

When an arrow label visually crosses another element, set `backgroundColor: "#ffffff"` on both the arrow and its label to mask the overlap.

### 5. Return arrow

Same structure as a forward arrow, but `x` starts at the far participant and `points` go negative:

```json
{
  "x": <to_center_x + 17>,
  "points": [[0, 0], [-(width), 0]]
}
```

- **ACK / void returns:** `strokeStyle: "solid"`, `strokeColor: "#868e96"` (grey)
- **DTO / data payload returns:** `strokeStyle: "dashed"`, `strokeColor: "#868e96"` (grey)

### 6. Arrow label

Always bound to its arrow via `containerId` — unbound labels float and break when the arrow moves.

```json
{
  "type": "text",
  "fontSize": 16,
  "fontFamily": 5,
  "strokeColor": "<same as arrow>",
  "backgroundColor": "transparent",
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": "<arrow_id>"
}
```

Use `fontSize: 13` for dense labels that must fit in a narrow space.

### 7. Self-referencing loop arrow

For any call that originates and terminates on the same lifeline. Use `elbowed: true` with a 4-point path — regular arrows cannot represent a self-loop.

```json
{
  "type": "arrow",
  "elbowed": true,
  "roundness": null,
  "points": [
    [0, 0],
    [42, 0],
    [42, <loop_height>],
    [0, <loop_height>]
  ]
}
```

### 8. Note box

Yellow box for implementation details placed to the right of the lifeline area:

```json
{
  "type": "rectangle",
  "backgroundColor": "#fff9db",
  "strokeColor": "#1e1e1e",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "strokeStyle": "solid",
  "roundness": { "type": 3 }
}
```

State-change notes use light purple: `"backgroundColor": "#e5dbff"`.

---

## Color convention

| Color | Hex | Typical usage |
|---|---|---|
| Black | `#1e1e1e` | Standard call arrows, lifelines, labels |
| Grey | `#868e96` | Return arrows, ACKs, response messages |
| Orange | `#f08c00` | Initialization / startup flows |
| Green | `#2f9e44` | Write / mutation flows |
| Blue | `#1971c2` | Polling, scheduled, periodic flows; external lifelines |
| Purple | `#7048e8` | Cleanup, TTL, acknowledgement flows |
| Red | `#e03131` | Error flows |

These are illustrative conventions — the project can define its own palette. What matters is that colors are **consistent** within a project and each color maps to one semantic meaning.

---

## Font size tiers

| Element | `fontSize` |
|---|---|
| Diagram title | `28` |
| Description text | `16` |
| Lifeline label | `20` |
| Flow group label | `20` |
| Arrow / message label | `16` |
| Dense label (multi-line, narrow space) | `13` |

Always `fontFamily: 5` for every text element.

---

## One diagram or many?

**Split into separate diagrams when:**
- Two operations involve a meaningfully different set of participants
- Two operations follow different flow structures (fire-and-forget vs async polling)
- A single diagram would become too wide or too tall to read comfortably

**Consolidate into one diagram when:**
- Two or more operations are structurally identical — same participants, same flow shape — and differ only in the operation name or the specific field being acted on
- In that case, name the operation generically and list the concrete operations it represents in the title

**Decision rule:** If you would have to draw different arrows or different lifelines, draw separate diagrams. If you would only have to change a label, consolidate into one.

---

## Generating a new diagram — checklist

1. Identify participants — list only what the feature's code path actually touches, left to right in call order
2. Assign x positions — space 190px apart
3. Draw lifeline bars — one rectangle per participant spanning the full diagram height
4. Label lifelines — text above each bar
5. Define flow groups — one dashed container per semantic block
6. Add messages row by row — arrow + bound label, 40px vertical spacing
7. Add return arrows — dashed grey for data, solid grey for ACKs
8. Add note boxes for internal logic or state effects
9. Add self-loops (`elbowed: true`) for any call that starts and ends on the same lifeline
10. Verify z-order — all arrows must have a higher `index` than all lifeline bars

---

## Planning step (always before writing JSON)

Before writing any JSON, output a diagram plan:

```
Diagrams to generate:
1. <FeatureName> — participants: A, B, C — flows: [list]
2. <FeatureName> — participants: D, E, F — flows: [list]
```

This makes scope visible, lets the developer correct the plan before any JSON is written, and gives sub-agents a clear brief if parallel generation is used.

**When multiple diagrams are needed:** generate and fully output one diagram before starting the next. Never hold two diagrams in context simultaneously — complete and flush each file before moving on.

---

## Common mistakes

| Mistake | Fix |
|---|---|
| **Arrows invisible until double-clicked** | Both array position AND `index` field are wrong — arrows must appear after all lifeline bars in the array AND have a higher `index` (use `e0`+ for arrows, `b0`+ for bars) |
| **Lifeline has no vertical line** | Lifeline bar rectangle was not generated — label alone does not produce the vertical bar |
| **Arrow label floats** | Set `containerId` on the label text and `boundElements` on the arrow |
| **Return arrow goes right** | `x` must start at the far participant; `points` must use a negative width: `[[0,0],[-width,0]]` |
| **Self-loop not elbowed** | Set `"elbowed": true` and use a 4-point path |
| **`fillStyle: "hachure"`** | Always `"fillStyle": "solid"` on every element |
| **`strokeWidth: 1` on arrows** | Arrows use `strokeWidth: 2`; only flow group containers use `strokeWidth: 1` |
| **Blocks too close** | Minimum 80px gap between last arrow of one block and first arrow of the next |
| **Block contains wrong rows** | Container `y` starts 40px above the first row (space for label); `height` = last_row_y - group_start_y + 60px |
| **Mixed `roughness` values** | Always `roughness: 1` |
| **Wrong font** | Always `fontFamily: 5` |
