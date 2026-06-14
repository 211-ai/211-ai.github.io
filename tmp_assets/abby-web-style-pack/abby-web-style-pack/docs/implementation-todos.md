# ABBY Home Screen Implementation TODOs

## Asset upload

- [ ] Copy the `assets/` folder into the app/public/static asset directory.
- [ ] Copy `css/abby-theme.css` into the app stylesheet directory or merge it into the existing global CSS.
- [ ] Keep the `reference/` folder out of production unless it is needed for design review.
- [ ] Confirm all asset URLs resolve relative to the compiled CSS file.

## CSS variables

- [ ] Add the ABBY color tokens from `css/abby-theme.css` to the app theme.
- [ ] Map existing design tokens to the ABBY palette:
  - Primary text: `--abby-ink` or `--abby-navy`
  - Primary action: `--abby-forest`
  - Selected state: `--abby-teal`
  - Soft surfaces: `--abby-off-white`, `--abby-soft-panel`, `--abby-mist`
  - Borders: `--abby-border`

## Background and layout

- [ ] Apply the page-level watercolor wash using `assets/watercolor-wash.svg`.
- [ ] Keep the existing dashboard layout and information architecture.
- [ ] Add `assets/abby-header-landscape.svg` as a subtle decorative header background.
- [ ] Keep header artwork behind the title at low opacity and ensure it never reduces readability.

## Sidebar

- [ ] Replace the sidebar background with a pale off-white/mist surface.
- [ ] Use `assets/abby-logo-mark.svg` or `assets/abby-logo-lockup.svg` for the brand area.
- [ ] Add `assets/abby-evergreen-cluster.svg` as a subtle bottom-left decoration.
- [ ] Restyle active nav item as a soft mist-green pill.
- [ ] Use navy for inactive nav text/icons and teal for the active item.

## Cards

- [ ] Update top cards to use off-white surfaces, soft teal borders, gentle shadows, and rounded corners.
- [ ] Keep icon tiles in pale mist green with teal icons.
- [ ] Keep card titles deep navy and descriptions readable.

## Quick action panel

- [ ] Apply `assets/watercolor-card-wash.svg` as a subtle background to the Next check-in panel.
- [ ] Use a teal border and mist-green fill.
- [ ] Make “Check in now” a filled forest-green button.
- [ ] Use readable sans-serif text for labels, dates, and button text.

## Lower support card

- [ ] Add a support card below the summary row.
- [ ] Use `assets/abby-help-badge.svg` on the left.
- [ ] Use `assets/abby-bridge-watermark.svg` as a low-opacity right-side decoration.
- [ ] Suggested copy:

```text
Need help today?
Find shelter, services, and support through your local 211 network.
```

- [ ] Add a primary action button: `Find help near you`.

## Typography

- [ ] Use a friendly display font only for major headings and card headings.
- [ ] Use a readable sans-serif for navigation, metadata, descriptions, dates, and buttons.
- [ ] Do not ship font files unless the project already has licensed fonts available.

## QA checklist

- [ ] Page still feels like a working app, not a poster.
- [ ] Core actions are easy to scan.
- [ ] Decorative motifs are subtle and non-blocking.
- [ ] Button focus states are visible.
- [ ] Text contrast passes accessibility requirements.
- [ ] The screen visually matches the generated preview direction.
