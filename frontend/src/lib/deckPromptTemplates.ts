export type DeckPromptTemplate = {
  id: string;
  label: string;
  body: string;
};

/** Suggestions for generating a brand-new deck from the file manager. */
export const DECK_PROMPT_TEMPLATES_NEW_DECK: readonly DeckPromptTemplate[] = [
  {
    id: "qbr",
    label: "QBR",
    body: "Create a quarterly business review deck: executive summary, KPI highlights vs last quarter, wins, challenges, and next-quarter priorities. Use a clean corporate style with 6–8 slides.",
  },
  {
    id: "pitch",
    label: "Pitch",
    body: "Create a short investor pitch deck: problem, solution, market, product demo outline, business model, traction, team, and ask. Aim for ~10 slides, bold titles, minimal text per slide.",
  },
  {
    id: "training",
    label: "Training",
    body: "Create a training module deck: learning objectives, 4–5 teaching sections with one key idea each, knowledge check prompts, summary, and next steps. Friendly, readable layout.",
  },
  {
    id: "architecture",
    label: "Architecture",
    body: "Create a technical architecture overview: context diagram, main components and responsibilities, data flow, key integrations, security boundaries, and deployment view. Diagram-style slides with short labels.",
  },
  {
    id: "product-launch",
    label: "Product launch",
    body: "Create a product launch narrative: what we built, who it is for, core benefits, how it works at a glance, pricing or packaging teaser, and call to action. Marketing tone, 7–9 slides.",
  },
  {
    id: "weekly",
    label: "Weekly update",
    body: "Create an all-hands or team weekly update: headline, metrics snapshot, shipped items, blockers, and shout-outs. Casual internal tone, 5–6 slides.",
  },
];

/** Suggestions for editing an existing uploaded deck. */
export const DECK_PROMPT_TEMPLATES_EDIT_DECK: readonly DeckPromptTemplate[] = [
  {
    id: "edit-tighten",
    label: "Tighten copy",
    body: "Shorten on-slide text, fix redundancy, and improve scannability without changing the overall story or slide order.",
  },
  {
    id: "edit-visual",
    label: "Visual polish",
    body: "Improve contrast, spacing, and typography hierarchy. Keep content the same but make slides feel more polished and consistent.",
  },
  {
    id: "edit-restructure",
    label: "Restructure",
    body: "Reorder and merge slides for a clearer narrative. Keep the same facts and branding; improve flow and section breaks.",
  },
  {
    id: "edit-brand",
    label: "Unify style",
    body: "Unify fonts, colors, and spacing to one consistent style across all slides without changing the underlying message.",
  },
  {
    id: "edit-agenda",
    label: "Add agenda",
    body: "Add a table-of-contents slide after the title and short section divider slides where helpful; keep existing content otherwise.",
  },
  {
    id: "edit-accessible",
    label: "Accessibility",
    body: "Improve color contrast for text on backgrounds, increase minimum font sizes where too small, and add concise alt text for key images.",
  },
];
