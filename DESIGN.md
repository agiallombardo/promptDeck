# Design System Strategy: The Synthetic Architecture

## 1. Overview & Creative North Star
**Creative North Star: "The Tactical Obsidian"**

This design system is engineered to move beyond the "SaaS dashboard" cliché and into the realm of high-stakes cybersecurity intelligence. It treats the interface not as a flat canvas, but as a physical, machined console carved from dark matter. 

The aesthetic is "Synthetic Architecture"—a digital environment characterized by structural depth, intentional asymmetry, and the tension between "Recessed" data pits and "Elevated" control surfaces. We break the template look by using high-contrast typography scales and staggering layout elements to create an editorial flow that feels orchestrated, not generated.

## 2. Colors & Surface Logic
The palette is rooted in ultra-low-frequency neutrals to allow the **Cyber Cyan (#00E5FF)** to function as a literal "light source" within the UI.

*   **Primary (#00E5FF):** To be used sparingly for critical data points, active states, and "light-bleed" effects.
*   **The Background (#050507):** The void. All logic begins here.
*   **Recessed Surface (#0A0B0E):** Used for data-rich environments, terminal windows, and input areas to create a sense of immersion.
*   **Elevated Surface (#16181D):** Reserved for floating modules, navigation, and modal overlays.

### The "No-Line" Rule
Standard 1px borders are forbidden for sectioning. Structural boundaries must be defined through **Background Color Shifts**. To separate a sidebar from a main stage, transition from `surface-container-low` to `surface`. If a boundary is visually required for high-density data, use a "Ghost Border"—the `outline_variant` at 15% opacity.

### Glass & Gradient Rule
To add "soul" to the cybersecurity aesthetic, use subtle linear gradients (0% opacity to 10% opacity of `primary`) on the top-left edge of elevated surfaces. For floating "Command HUDs," apply a `backdrop-blur` of 12px to `surface_container_high` at 80% opacity to simulate a glass interface over a dark terminal.

## 3. Typography: The Intelligence Stack
We utilize a three-font system to delineate role and authority:

*   **Display & Headlines (Space Grotesk):** Geometric and authoritative. Used for high-level "Editorial" moments and section headers. High tracking (-2%) for a tighter, more technical feel.
*   **UI & Metadata (JetBrains Mono):** The "Intelligence" layer. All technical data, timestamps, and system status must use this monospaced face to convey accuracy and raw data.
*   **Body (Geist):** The "Narrative" layer. Geist provides a clean, neutral sans-serif for long-form reporting and descriptions, ensuring high legibility against dark backgrounds.

**Hierarchy Note:** Use extreme scale contrast. A `display-lg` headline (3.5rem) should often sit adjacent to a `label-sm` (0.6875rem) JetBrains Mono tag to create a high-end, asymmetric editorial look.

## 4. Elevation & Depth: Tonal Layering
In this system, depth is a functional tool, not a stylistic choice.

*   **The Recessed Principle (Inset):** For data feeds and code blocks, use `surface_container_lowest` (#0A0B0E) with an inner shadow: `inset 0 2px 4px rgba(0,0,0,0.5)`. This makes the data feel "carved" into the hardware.
*   **The Elevated Principle (Outer):** For action-oriented cards, use `surface_container_highest` (#16181D). 
*   **Ambient Shadows:** Floating elements must use a "Cyan-Tinted Shadow" rather than grey. Use a 24px blur with `primary` at 4% opacity to simulate the glow of a high-tech monitor reflecting off a dark surface.
*   **Radii:** Maintain a strict **4px (DEFAULT)** radius. This sharpness reinforces the "machined" industrial feel. Avoid "full" pill shapes unless used for status pips.

## 5. Components

### Buttons
*   **Primary:** Solid `primary` (#00E5FF) with `on_primary` (#00363D) text. No border. Subtle outer glow on hover.
*   **Secondary:** `outline` border (Ghost Border style) with `primary` text. Use `surface_container_low` as the background.
*   **Ghost:** No background or border. Text in `on_surface_variant`. Active state reveals a `primary` underline (2px).

### Input Fields
*   **Visual Style:** Always "Recessed." Use `surface_container_lowest`. 
*   **Active State:** The 1px border illuminates to `primary` (#00E5FF) with a 2px "light bleed" (inner shadow) of the same color.
*   **Font:** Must use **JetBrains Mono** for the input text to emphasize data entry.

### Cards & Modules
*   **Rule:** No divider lines. Separate header from body using a background shift (e.g., Header: `surface_container_high`, Body: `surface_container`).
*   **Structure:** Use intentional asymmetry. Place metadata (JetBrains Mono) in the top-right corner, staggered against a left-aligned headline.

### The "Scanner" Progress Bar
*   A custom component for this system. A ultra-thin (2px) track in `surface_container_highest` with a `primary` lead that has a 10px blurred "comet tail" effect.

## 6. Do's and Don'ts

### Do
*   **Do** use vertical white space (from the Spacing Scale) to separate thoughts.
*   **Do** use `primary` for "Success" or "Safe" states, but keep it as the primary brand color—if an error occurs, use the `error` (#ffb4ab) token sparingly.
*   **Do** align elements to a strict grid but break the grid with one "Hero" element (like a large display-sm title) that overlaps two columns.

### Don't
*   **Don't** use pure white (#FFFFFF) for text; use `on_surface` (#e5e1e5) to reduce eye strain in ultra-dark environments.
*   **Don't** use standard drop shadows. If it doesn't look like an ambient glow or a structural recess, it doesn't belong.
*   **Don't** use rounded corners above 8px. This system is built on precision and sharpness.