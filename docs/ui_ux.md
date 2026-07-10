# UI/UX & Design System

Profile Guru features a premium, accessible user interface built on a robust semantic design token system, prioritizing both high visual quality and compliance.

---

## 1. Semantic Design Token System

All interface colors, spacing, and styles are driven by custom CSS variables defined in [globals.css](file:///f:/Github/Profile-Guru/frontend/src/app/globals.css). This enables seamless theme transitions while ensuring AA-compliant contrast ratios.

### Canvas & Surface Tokens
- `var(--bg-canvas)`: Main dashboard background (vibrant dark slate / light ash).
- `var(--bg-surface)`: Card containers and workspace columns.
- `var(--bg-surface-raised)`: Headers and active navigation states.

### Brand Accent Tokens
- `var(--brand-teal)`: Main highlight, button active states, and primary analytics line (contrasts at 6.6:1 in light mode for readability).

---

## 2. Reusable UI Primitives

To maintain design consistency across panels, the frontend uses several key React primitives:

### `<ChartFrame>`
A wrapper for Recharts analytics graphs that guarantees accessibility and data visibility:
- **Fallback Data Table:** Includes an accessible toggle showing raw data in standard tables.
- **CSV Exporter:** Features a button to export visual metrics to standard CSV files.

### `<DataCard>`
Containers for displaying metrics (such as daily average volumes) with standard font scaling.

### `<EmptyState>`
Designed empty states featuring standard icons, descriptive text, and a Call-To-Action (CTA) button, used for initial contact lists and empty chat threads.

### `<Skeleton>`
A lightweight loader primitive featuring `prefers-reduced-motion` CSS rules to replace loading spinners during API fetches.

---

## 3. Web Accessibility (A11y) Standards

Profile Guru is audited using ESLint (`eslint-plugin-jsx-a11y`) to enforce web standards:
- **Skip-To-Content:** Includes a focusable skip link at the top of the page layout to bypass navigation sidebars.
- **Label Association:** All form controls (inputs, dropdowns) are linked to labels via matching `htmlFor` and `id` properties.
- **Focus Rings:** Features a highly visible `:focus-visible` ring utilizing the brand teal color.
- **Keyboard Equivalents:** Drag-and-drop zones in the Import Panel are keyboard-focusable and triggered by hitting the Space or Enter keys.
- **Form Grouping:** Configures groups (such as selecting local vs. cloud engines) under `<fieldset>` with descriptive `<legend>` tags for screen readers.

---

## 4. Onboarding, Hints, and Shortcuts

To help practitioners navigate the multi-pane interface, Profile Guru includes interactive onboarding systems:

### Onboarding welcome Tour
- Displays a skippable introduction card upon the first load of the dashboard.
- Utilizes `localStorage` (`pg.onboarding.shown`) to prevent re-displaying after it has been dismissed.
- Can be re-triggered from the User Menu.

### Keyboard Shortcuts Cheatsheet
- Hitting the **`?`** key anywhere in the app displays an overlay listing all available power-user keyboard shortcuts.
- Platform-aware (displays `Cmd` on macOS and `Ctrl` on Windows/Linux).

### Resizable Inspector Pane
- Toggled on/off using the sidebar icon or hitting `Ctrl/Cmd+I`.
- Persists user preferences for pane width across sessions using local storage variables.
