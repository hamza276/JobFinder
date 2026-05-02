# Frontend Components

## Design System
- Colors: `#0a1628` (deep navy), `#f5f0e8` (cream), `#c9a84c` (gold), `#2d6a4f` (forest green for high scores)
- Fonts: `Playfair Display` (serif, titles) + `Inter` (sans, body) — load from Google Fonts
- Border radius: 12px for cards, 8px for buttons
- Shadow: `0 4px 24px rgba(10,22,40,0.12)`

## Component Directory Map
```
components/
├── JobCard/
│   └── index.jsx     ← Main job card for the feed
├── ProfileWizard/
│   └── index.jsx     ← Multi-step form wizard
├── EmailModal/
│   └── index.jsx     ← Email preview + copy modal
└── common/
    ├── Button.jsx
    ├── Input.jsx
    ├── TagInput.jsx   ← For skills entry
    ├── Loader.jsx
    ├── Toast.jsx
    └── ScoreBar.jsx   ← Visual relevance score indicator
```

## JobCard Design Notes
The JobCard is the most important UI component.
- Size: Full width in a single-column layout on mobile, 2-col masonry on desktop
- Header: Company logo (circle avatar with initials fallback) + Company name + Location tag
- Title: Large serif font (Playfair Display, 1.4rem)
- Body: 2-line truncated description snippet
- Footer: Posted date (relative: "2 days ago") + Source badge (LinkedIn/Rozee/etc.) + ScoreBar
- Hover: Slight lift with box-shadow transition (150ms)
- Click: Opens right-side drawer with full JD

## ScoreBar
A horizontal bar showing relevance score (0-1):
- 0.0 - 0.4: Red/orange (low match)
- 0.4 - 0.7: Yellow (medium match)
- 0.7 - 1.0: Green (strong match)
- Shows percentage label on hover (e.g., "87% match")

## ProfileWizard Steps
Each step is a separate component passed as children:
```
<WizardStep title="Basic Info" step={1} totalSteps={5}>
  ...fields
</WizardStep>
```
Progress bar at top shows completion. Back/Next buttons at bottom.

## Notes for Codex
- Use Tailwind classes, not inline styles
- All components should be keyboard accessible
- JobCard should have `aria-label` for screen readers
- Use `React.memo` on JobCard to prevent unnecessary rerenders in long feed lists
