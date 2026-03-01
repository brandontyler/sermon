# Frontend Design Spec — PSR MVP

For the developer building the Next.js frontend. Three pages, one API, no auth.

Tech: Next.js + TypeScript + Tailwind CSS + Recharts (radar chart). Deployed on Azure Static Web Apps (free tier).

---

## Design Principles

1. Lighthouse report, not a dashboard. The detail page should feel like opening a Lighthouse audit — big score, category breakdown, expandable reasoning.
2. Typography is the design. Inter font, generous whitespace, no decorative elements. The numbers speak.
3. Three colors for scores. Green (70+), yellow (50-69), red (below 50). That's it.
4. Light theme only for MVP. Gray-50 background, white cards. Dark mode is Phase 1.
5. Screenshot-friendly. The top fold of the detail page (score + summary + radar) should look good shared on Twitter/Discord without cropping.

---

## Page 1: Upload (`/`)

Centered on screen, vertically and horizontally. Single column, max-width 400px.

```
┌─────────────────────────────────────┐
│                                     │
│              PSR                    │  ← wordmark, text-xl, gray-900
│       Pastor Sermon Rating          │  ← text-sm, gray-500
│                                     │
│     ┌───────────────────────────┐   │
│     │                           │   │
│     │   Drop audio file here    │   │  ← dashed border, gray-200
│     │   or click to browse      │   │
│     │                           │   │
│     │   MP3, WAV, M4A · max 1hr│   │  ← text-xs, gray-400
│     └───────────────────────────┘   │
│                                     │
│         [ View All Sermons → ]      │  ← text link to /sermons
│                                     │
└─────────────────────────────────────┘
```

After file is selected, the drop zone collapses to a filename + size confirmation and optional fields appear below. Still centered, still minimal:

```
┌─────────────────────────────────────┐
│                                     │
│              PSR                    │
│       Pastor Sermon Rating          │
│                                     │
│     ✓ sermon_audio.mp3  (42 MB)    │  ← green-500 check, text-sm
│                                     │
│     [________________________________] ← placeholder: "Sermon title (optional)"
│     [________________________________] ← placeholder: "Pastor name (optional)"
│                                     │
│           [ Analyze Sermon ]        │  ← blue-600 button, full-width within column
│                                     │
│     ████████████░░░░░░░░  uploading │  ← appears after button click
│                                     │
└─────────────────────────────────────┘
```

Behavior:
- Accept drag-and-drop or file picker (accept: `.mp3,.wav,.m4a`)
- On file select: drop zone replaced by filename confirmation + two optional text inputs + submit button
- Inputs use placeholder text only — no labels. Keeps it clean. Placeholders: "Sermon title (optional)", "Pastor name (optional)"
- Inputs are plain: border-b border-gray-200, no box border, no background. Typography-first.
- If fields are left blank, the pipeline's LLM metadata extraction fills them from the transcript
- If the user provides them, they take priority over LLM extraction
- "Analyze Sermon" button: blue-600 bg, white text, rounded-lg, full column width
- On click: POST to `/api/sermons` with multipart form data (file + optional title + optional pastor)
- Show progress bar during upload (thin, blue-600, below button)
- On success: redirect to `/sermons/{id}` (detail page shows processing state)
- On error: show inline error message (red-500 text below button)
  - File too large (>100MB): "File too large. Max 100MB. Try converting to MP3."
  - Wrong format: "Unsupported format. Upload MP3, WAV, or M4A."
- "View All Sermons →" link stays visible in both states

---

## Page 2: Sermon Feed (`/sermons`)

ESPN QBR table layout. The score is the hero column.

```
PSR — Pastor Sermon Rating                              [ Upload → ]

┌─────┬──────────────────────────────────┬──────────┬──────────┬─────────┐
│ PSR │ Sermon                           │ Type     │ Duration │ Date    │
├─────┼──────────────────────────────────┼──────────┼──────────┼─────────┤
│ 83  │ Called According to His Purpose   │ Expos.   │ 35 min   │ Feb 28  │
│     │ John Piper                       │          │          │         │
├─────┼──────────────────────────────────┼──────────┼──────────┼─────────┤
│ 78  │ The Power of Grace               │ Topical  │ 47 min   │ Feb 25  │
│     │ Pastor Name                      │          │          │         │
├─────┼──────────────────────────────────┼──────────┼──────────┼─────────┤
│ ··· │ Don't Waste Your Life            │ Topical  │ 56 min   │ Feb 22  │
│     │ John Piper                       │          │          │         │
└─────┴──────────────────────────────────┴──────────┴──────────┴─────────┘
```

Details:
- PSR column: large bold number, color-coded (green/yellow/red). If still processing, show a spinner icon with "···"
- Sermon column: title on first line (medium weight), pastor name on second line (small, muted)
- Type column: badge/pill — "Expos." / "Topical" / "Survey"
- Rows are clickable → navigate to `/sermons/{id}`
- Default sort: newest first. Clickable column headers to sort by PSR score or date
- Filter row above table: sermon type dropdown (All / Expository / Topical / Survey)
- No pagination for MVP

Data source: `GET /api/sermons` → returns array of sermon summaries.

---

## Page 3: Sermon Detail (`/sermons/{id}`)

This is the main event. Layout is a single column, max-width ~720px, centered.

### Section 1: Header

```
← Back to sermons

Called According to His Purpose
John Piper · Feb 28, 2026 · 35 min · [Expository]
```

- Back link (text, not button)
- Title: large, bold (text-2xl or text-3xl)
- Metadata line: pastor · date · duration · type badge
- If status is "processing": show a centered status message instead of all sections below:
  ```
  Analyzing sermon...
  Transcribing audio ✓
  Scoring biblical accuracy ···
  Scoring structure & content ···
  Scoring delivery ···
  ```

### Section 2: Score Hero

```
        ┌─────────┐
        │         │
        │   83    │         ← large number centered in circular arc gauge
        │  /100   │
        │         │
        └─────────┘

  "Strong expository sermon with excellent biblical
   grounding. Application could be more concrete."
```

- Circular arc gauge (not full circle — 270° arc like Lighthouse)
- Score number centered inside, large (text-5xl or bigger)
- "/100" below the number, small and muted
- Arc color: green (70+), yellow (50-69), red (<50)
- Below gauge: one-sentence AI summary in italic, muted text
- This section + the radar below should fit in one screen for screenshot-ability

### Section 3: Category Breakdown

2×4 grid of category cards. Each card:

```
┌──────────────────────────────┐
│ Biblical Accuracy      25%   │  ← name + weight, small
│ ████████████████░░░░  95     │  ← horizontal bar + score number
│                              │
│ ▸ View reasoning             │  ← expandable, collapsed by default
└──────────────────────────────┘
```

- Bar is color-coded by score (green/yellow/red)
- Bar width = score percentage (95 = 95% filled)
- Weight shown as small muted text aligned right of category name
- "View reasoning" expands to show the LLM's reasoning text from the API response
- Grid order (left to right, top to bottom), sorted by weight:
  1. Biblical Accuracy (25%)
  2. Time in the Word (20%)
  3. Passage Focus (10%)
  4. Clarity (10%)
  5. Engagement (10%)
  6. Application (10%)
  7. Delivery (10%)
  8. Emotional Range (5%)

On mobile: stack to single column.

### Section 4: Radar Chart

Opta-style 8-axis radar using Recharts `<RadarChart>`.

```
            Biblical Accuracy
                  ╱╲
     Emot. Range /  \ Time in Word
               /    \
    Delivery ─/──────\─ Passage Focus
               \    /
    Engagement  \  / Clarity
                 ╲╱
             Application
```

- 8 axes, one per category
- Color-grouped fills (optional, can be single color for MVP):
  - Blue area: biblical categories (accuracy, time in word, passage focus)
  - Green area: content categories (clarity, application, engagement)
  - Orange area: delivery categories (delivery, emotional range)
- Single-color fill (blue-500 at 20% opacity with blue-500 stroke) is fine for MVP
- Axis labels are category names (abbreviated if needed)
- Tooltip on hover showing exact score
- Fixed size: ~400×400px, centered

### Section 5: Strengths & Improvements

Two columns side by side (stack on mobile):

```
✓ Strengths                    △ Areas to Improve
• Biblical grounding           • More concrete application
• Practical application        • Vary emotional tone
• Clear structure              • Reduce filler words
```

- Green checkmark icon for strengths, yellow triangle for improvements
- Simple bullet lists, 3 items each (from API response)

### Section 6: Transcript

Scrollable container with the full transcript text. Segment types are color-coded with subtle left-border or background tint:

```
│ blue   │ "The morning text for today's sermon is Romans 8:28-30..."
│ gray   │ "We know that in everything God works for good..."
│ green  │ "I want you to find refuge in this promise..."
│ orange │ "I was at a construction site last week..."
```

Color key:
- Blue left border: scripture reading/reference
- Gray (default): teaching/exposition
- Green left border: application
- Orange left border: anecdote/illustration

Scripture references in the text should be visually distinct (bold or linked). Clicking a reference could show a tooltip with the verse text (Phase 1 — for MVP, just bold them).

---

## API Contracts

The frontend needs three endpoints from the Azure Functions backend:

### `POST /api/sermons`
Upload a sermon audio file.

Request: `multipart/form-data` with fields:
- `file` (required): audio file (MP3, WAV, M4A, max 100MB)
- `title` (optional): sermon title. If blank, extracted from transcript by LLM.
- `pastor` (optional): pastor name. If blank, extracted from transcript by LLM.

User-provided values take priority over LLM extraction.

Response:
```json
{
  "id": "sermon-uuid",
  "status": "processing"
}
```

### `GET /api/sermons`
List all sermons (feed page).

Response:
```json
[
  {
    "id": "sermon-uuid",
    "title": "Called According to His Purpose",
    "pastor": "John Piper",
    "date": "2026-02-28",
    "duration": 2100,
    "status": "complete",
    "sermonType": "expository",
    "compositePsr": 82.7
  }
]
```

`compositePsr` is `null` when `status` is `"processing"`.

### `GET /api/sermons/{id}`
Full sermon detail.

Response: the full Cosmos DB sermon document. Key fields the frontend reads:

```json
{
  "id": "sermon-uuid",
  "title": "Called According to His Purpose",
  "pastor": "John Piper",
  "date": "2026-02-28",
  "duration": 2100,
  "status": "complete",
  "sermonType": "expository",
  "compositePsr": 82.7,
  "summary": "Strong expository sermon with excellent biblical grounding...",
  "categories": {
    "biblicalAccuracy": { "score": 95, "weight": 25, "reasoning": "..." },
    "timeInTheWord": { "score": 70, "weight": 20, "reasoning": "..." },
    "passageFocus": { "score": 90, "weight": 10, "reasoning": "..." },
    "clarity": { "score": 82, "weight": 10, "reasoning": "..." },
    "engagement": { "score": 89, "weight": 10, "reasoning": "..." },
    "application": { "score": 68, "weight": 10, "reasoning": "..." },
    "delivery": { "score": 75, "weight": 10, "reasoning": "..." },
    "emotionalRange": { "score": 90, "weight": 5, "reasoning": "..." }
  },
  "strengths": ["Biblical grounding", "Practical application", "Clear structure"],
  "improvements": ["More concrete application", "Vary emotional tone"],
  "transcript": {
    "fullText": "The morning text for today's sermon is Romans 8:28-30...",
    "segments": [
      {
        "start": 0.0,
        "end": 45.2,
        "text": "The morning text for today's sermon is Romans 8:28-30...",
        "type": "scripture"
      }
    ]
  }
}
```

Segment types: `"scripture"`, `"teaching"`, `"application"`, `"anecdote"`, `"illustration"`, `"prayer"`, `"transition"`

---

## Processing State

When `status` is `"processing"`, the detail page shows a simple status view instead of the scorecard:

```
Analyzing sermon...

◻ Transcribing audio
◻ Analyzing biblical content
◻ Evaluating structure
◻ Scoring delivery

This usually takes 1-2 minutes.
```

Poll `GET /api/sermons/{id}` every 5 seconds. When status flips to `"complete"`, render the full scorecard. No websockets needed for MVP.

---

## Component Inventory

| Component | Library | Notes |
|-----------|---------|-------|
| File drop zone | react-dropzone or native | Drag-and-drop + click to browse |
| Score gauge | Custom SVG or CSS | 270° arc, number centered. ~50 lines of SVG |
| Category bar | Tailwind div | Colored div with width as percentage |
| Radar chart | Recharts `<RadarChart>` | 8 axes, single dataset |
| Transcript viewer | Native scroll div | Left-border color per segment type |
| Sermon table | Native HTML table | Sortable columns via state |

No component library (no shadcn, no MUI). Tailwind utility classes only. Keep the dependency count minimal.

---

## Design Tokens

```
Font:          Inter (Google Fonts) or system font stack
Background:    gray-50 (#f9fafb)
Card:          white, border gray-200, rounded-lg (8px)
Text primary:  gray-900
Text muted:    gray-500
Score green:   green-500 (#22c55e) — scores 70+
Score yellow:  yellow-500 (#eab308) — scores 50-69
Score red:     red-500 (#ef4444) — scores below 50
Accent:        blue-600 (#2563eb) — links, active states
Spacing:       16px grid (p-4, gap-4 as base unit)
Max width:     720px for detail page, 960px for feed page
```

---

## What's NOT in MVP

- Dark mode
- Social sharing / export card
- Audio playback in transcript viewer
- Sermon comparison (side-by-side)
- Search
- Pastor profiles
- Auth / user accounts
- Animations beyond basic transitions
