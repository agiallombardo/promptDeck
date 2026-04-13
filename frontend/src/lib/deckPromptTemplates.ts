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
    body: "Create a quarterly business review deck: executive summary, KPI highlights vs last quarter, wins, challenges, and next-quarter priorities. Use a clean corporate style with 6–8 slides. Add 'Internal only' on every slide.",
  },
  {
    id: "pitch",
    label: "Pitch",
    body: "Create a short investor pitch deck: problem, solution, market, product demo outline, business model, traction, team, and ask. Aim for ~10 slides, bold titles, minimal text per slide. Add 'Internal only' on every slide.",
  },
  {
    id: "training",
    label: "Training",
    body: "Create a training module deck: learning objectives, 4–5 teaching sections with one key idea each, knowledge check prompts, summary, and next steps. Friendly, readable layout. Add 'Internal only' on every slide.",
  },
  {
    id: "architecture",
    label: "Architecture",
    body: "Create a technical architecture overview: context diagram, main components and responsibilities, data flow, key integrations, security boundaries, and deployment view. Diagram-style slides with short labels. Add 'Internal only' on every slide.",
  },
  {
    id: "product-launch",
    label: "Product launch",
    body: "Create a product launch narrative: what we built, who it is for, core benefits, how it works at a glance, pricing or packaging teaser, and call to action. Marketing tone, 7–9 slides. Add 'Internal only' on every slide.",
  },
  {
    id: "weekly",
    label: "Weekly update",
    body: "Create an all-hands or team weekly update: headline, metrics snapshot, shipped items, blockers, and shout-outs. Casual internal tone, 5–6 slides. Add 'Internal only' on every slide.",
  },
];

/** Suggestions for editing an existing uploaded deck. */
export const DECK_PROMPT_TEMPLATES_EDIT_DECK: readonly DeckPromptTemplate[] = [
  {
    id: "edit-tighten",
    label: "Tighten copy",
    body: "Shorten on-slide text, fix redundancy, and improve scannability without changing the overall story or slide order. Keep or add an 'Internal only' label on every slide.",
  },
  {
    id: "edit-visual",
    label: "Visual polish",
    body: "Improve contrast, spacing, and typography hierarchy. Keep content the same but make slides feel more polished and consistent. Keep or add an 'Internal only' label on every slide.",
  },
  {
    id: "edit-restructure",
    label: "Restructure",
    body: "Reorder and merge slides for a clearer narrative. Keep the same facts and branding; improve flow and section breaks. Keep or add an 'Internal only' label on every slide.",
  },
  {
    id: "edit-brand",
    label: "Unify style",
    body: "Unify fonts, colors, and spacing to one consistent style across all slides without changing the underlying message. Keep or add an 'Internal only' label on every slide.",
  },
  {
    id: "edit-agenda",
    label: "Add agenda",
    body: "Add a table-of-contents slide after the title and short section divider slides where helpful; keep existing content otherwise. Keep or add an 'Internal only' label on every slide.",
  },
  {
    id: "edit-accessible",
    label: "Accessibility",
    body: "Improve color contrast for text on backgrounds, increase minimum font sizes where too small, and add concise alt text for key images. Keep or add an 'Internal only' label on every slide.",
  },
];

/** Suggestions for generating a brand-new XYFlow diagram from the file manager. */
export const DIAGRAM_PROMPT_TEMPLATES_NEW_DIAGRAM: readonly DeckPromptTemplate[] = [
  {
    id: "diagram-architecture",
    label: "Architecture",
    body: "Create a software architecture diagram with clear layers (clients, edge/API, services, data stores, integrations), primary request/data paths, and concise labels.",
  },
  {
    id: "diagram-business-process",
    label: "Business process",
    body: "Create a business process diagram from intake to completion with roles, decision points, handoffs, and exceptions. Keep the flow left-to-right and easy to scan.",
  },
  {
    id: "diagram-automation",
    label: "Automation flow",
    body: "Create an automation workflow diagram showing trigger, validation, branching rules, actions, retries, notifications, and completion states.",
  },
  {
    id: "diagram-data-flow",
    label: "Data flow",
    body: "Create a data flow diagram that traces source systems, ingestion, transformation, storage, serving layers, and consumers with directional edges.",
  },
  {
    id: "diagram-org-chart",
    label: "Org chart",
    body: "Create an organizational chart showing leadership hierarchy, teams, and reporting lines with role labels.",
  },
  {
    id: "diagram-erd",
    label: "ERD / Database",
    body: "Create a high-level database design diagram with key entities/tables, primary relationships, and a short label for each relationship.",
  },
];
