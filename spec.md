# Beam Designer

## Purpose
A beam design tool for engineers and students. The user sets up a beam,
places loads on it, and picks a steel or lumber section. The app shows the
shear, moment, and deflection diagrams and checks whether the beam is
strong and stiff enough, updating instantly as anything changes.

##Platfrom
-

## Users
A civil engineering student checking a homework beam, or an engineer
sizing a floor beam or deck joist.

## Inputs
- Support type: two radio buttons for Simply supported (default) or Cantilever
  (fixed at the left end).
- Span: 4 to 40 ft, set with a slider and a number box that stay in sync.
  Default: 20 ft. The slider uses 0.1 ft increments, and the number box
  accepts decimal values with no forced step. If the span is outside 4 to
  40 ft, show an inline error and stop updating calculations.
- When the span changes, scale all point-load positions proportionally
  to the new span and scale uniform-load start and end positions
  proportionally. Point-load positions are clamped to the beam endpoints
  after scaling.
- Loads, listed in a panel where each can be edited or removed:
  - Point loads: magnitude (kips, downward positive) and position (ft).
    Magnitude range: 0 to 100 kips. Position range: 0 to the beam span.
    Magnitude and position use number boxes. A new point load defaults to
    1 kip at midspan (at the free end of a cantilever).
  - Uniform loads: magnitude (kips/ft) and start and end positions (ft).
    Magnitude range: 0 to 10 kips/ft. Start and end ranges: 0 to the beam
    span. Magnitude, start, and end use number boxes. A new uniform load
    defaults to 1 kip/ft from 0 ft to the beam span.
  - "Add point load" and "Add uniform load" buttons.
  - Point loads can also be dragged along the beam in the drawing,
    snapping to 0.25 ft.
  - Loads that extend past the end of the beam are cut off at the end.
  - Invalid values and uniform loads whose start position is greater than
    their end position show an inline error and do not update the
    calculations. An equal start and end is a valid zero-length uniform
    load, equivalent to no load.
- Material and section, from these tables:

  Use separate dropdown controls for material and section. The material
  dropdown contains Steel and Lumber. The section dropdown contains only
  sections for the selected material. Default: Steel, W12x26.
  Switching to Steel selects W12x26; switching to Lumber selects 2x10.

  Steel W-shapes (E = 29,000 ksi, allowable bending stress Fb = 30 ksi):

  | Section | Ix (in^4) | Sx (in^3) | Weight (lb/ft) |
  |---------|-----------|-----------|----------------|
  | W8x10   | 30.8      | 7.81      | 10 |
  | W10x12  | 53.8      | 10.9      | 12 |
  | W12x26  | 204       | 33.4      | 26 |
  | W14x22  | 199       | 29.0      | 22 |
  | W16x26  | 301       | 38.4      | 26 |
  | W18x35  | 510       | 57.6      | 35 |
  | W21x44  | 843       | 81.6      | 44 |
  | W24x55  | 1350      | 114       | 55 |

  Douglas Fir-Larch No. 2 lumber (E = 1,600 ksi, Fb = 0.900 ksi):

  | Section | Ix (in^4) | Sx (in^3) |
  |---------|-----------|-----------|
  | 2x8     | 47.63     | 13.14     |
  | 2x10    | 98.93     | 21.39     |
  | 2x12    | 177.98    | 31.64     |

- Deflection limit: dropdown with L/240 or L/360. Default: L/360.
- Self-weight is ignored.

## Calculations
- Use x = 0 ft at the left end, positive x toward the right, and y positive
  upward. Shear V(x) is in kips and moment M(x) is in kip-ft. Positive shear
  equals the sum of upward forces to the left of the cut. Positive moment
  follows the sagging convention.
- Reactions from statics: use vertical force equilibrium and moment
  equilibrium. For a simply supported beam, solve the left and right vertical
  reactions using sum Fy = 0 and sum M = 0. For a cantilever, the left vertical
  reaction is the sum of the applied downward loads (as an upward reaction),
  and the fixed support also provides the reaction moment opposite the
  resultant applied moment.
  Display reaction magnitudes with kips or kip-ft and indicate upward/downward
  or moment direction.
- Shear V(x) and moment M(x) along the beam, at 1 ft spacing or finer,
  plus exactly at every load point and load start/end.
- Report max shear as the maximum absolute value, |V|max, and label its
  location xV. Report max moment as the maximum absolute value,
  |M|max, and label its location xM.
- Deflection y(x) by integrating M/EI twice with the boundary conditions
  for the support type (y = 0 at both supports; or y = 0 and slope = 0 at
  the fixed end). E is the modulus of elasticity in ksi, I is the selected
  section's moment of inertia in in^4, and EI is in kip-in^2. y(x) is in
  inches. Convert x and M to inches and kip-in throughout the integration,
  with y = 0 and slope = 0 in the appropriate boundary conditions.
  Report max deflection as |y|max at location xy.
- Convert the max moment to inch-kips before bending-stress calculation:
  Mmax-in-kip = |M|max (kip-ft) x 12 (in/ft). Bending stress
  fb = Mmax-in-kip / Sx (in^3) in ksi, where Sx is the selected section's
  section modulus. The bending check passes if fb <= Fb, where Fb is in ksi.
- Deflection limit L/240 or L/360 uses L in inches:
  Lin = L(ft) x 12 (in/ft). The deflection check passes if
  |y|max <= Lin / 240 or Lin / 360.
- Check-card ratios are actual divided by allowable: fb / Fb for bending and
  |y|max / (Lin / 240 or Lin / 360) for deflection.
- Lightest passing section: of the sections in the chosen material, the
  lightest steel section that passes both checks (if two weigh the same,
  the one with the larger Ix), or the first lumber size in the table
  that passes. If no section passes, display "No passing section."
- Units: kips, ft, and kip-ft on screen; inches for deflection.

## Outputs
- A beam drawing with the supports, load arrows (point loads as single
  arrows, uniform loads as a row of small arrows), and the reactions.
- Three diagrams stacked under the beam and lined up with it on the same
  x scale: shear (kips), moment (kip-ft), and deflected shape (in). Each
  diagram is filled and shows its maximum value labeled at its location.
- Moving the mouse over any diagram shows a vertical line across all three
  with the values of V, M, and y at that x, calculated from the curves at
  the cursor position.
- Two check cards: Bending and Deflection. Each shows the actual value, the
  allowable value, a bar for the ratio (green under 70%, amber 70-100%,
  red over 100%), and PASS or FAIL.
- A line suggesting the lightest passing section, with a button to use it.
- When no section passes, show "No passing section." and do not show the
  use-section button.
- Everything updates immediately whenever any input changes.

## Look and feel
- Opens with an example already loaded (20 ft simply supported W12x26
  with a 1 kip/ft uniform load over the full span), so it is useful the
  moment it opens.
- Clean and professional, like a commercial engineering web app: light
  background, white cards with soft shadows, one accent color, a modern
  system font, generous spacing. No clutter.
- Inputs in a panel on the left; drawing, diagrams, and checks on the right. Window can be resized. 
- Every input has a short label with units. Hovering over a check card
  explains the formula used.

## Validation
1. Simply supported, 20 ft, W12x26, uniform 1 kip/ft over the full span:
   reactions 10 k and 10 k; max shear 10 k; max moment 50.0 kip-ft at
   10 ft; fb = 17.96 ksi; max deflection 0.609 in at 10 ft; L/360 =
   0.667 in; both checks pass.
2. Simply supported, 20 ft, W12x26, point load 10 k at 5 ft: reactions
   7.5 k (left) and 2.5 k (right); max moment 37.5 kip-ft at 5 ft;
   fb = 13.47 ksi; max deflection 0.340 in at 8.82 ft.
3. Cantilever, 10 ft, W12x26, point load 5 k at the free end: reaction
   5 k and fixed-end moment 50 kip-ft; max deflection 0.487 in at the free
   end (PL^3/3EI); L/360 = 0.333 in, so deflection fails.
4. Simply supported 12 ft 2x10 joist, uniform 0.05 kip/ft: max moment
   0.90 kip-ft; fb = 0.505 ksi; max deflection 0.147 in; both pass.
5. Simply supported, 30 ft, W18x35, uniform 2 kips/ft from 0 to 15 ft
   only: reactions 22.5 k (left) and 7.5 k (right); max moment
   126.6 kip-ft at 11.25 ft.

## Out of scope
- Self-weight, shear stress, lateral-torsional buckling, load
  combinations, and continuous beams.
- Saving designs.

## Build stages

### Stage 1: Build the page shell and static beam mockup
- Create the responsive left-input/right-results layout.
- Add the default support type, 20 ft span controls, load area, material
  dropdown, section dropdown, and deflection limit control.
- Draw the 20 ft simply supported beam, fixed initial uniform load, and
  placeholder areas for diagrams and check cards.
- No engineering calculations should run in this stage.
- Check: the page matches the light professional look, the example is shown
  on first load, desktop layout is left/right, and phone layout stacks.

### Stage 2: Make the inputs interactive
- Implement add/remove/edit behavior for point and uniform loads.
- Synchronize the span slider and number box at 0.1 ft increments.
- Add inline validation, load range limits, load scaling when span changes,
  material-to-section switching, and deflection-limit selection.
- Implement 0.25 ft point-load snapping and the drawing drag control.
- Check: the default example remains loaded, invalid values show inline errors,
  and all controls update the displayed input state immediately.

### Stage 3: Add beam drawing and shear/moment calculations
- Implement reactions, shear V(x), and moment M(x) for simply supported and
  cantilever beams with the resolved sign conventions.
- Render the beam supports, load arrows, reactions, and filled shear/moment
  diagrams on the same x scale.
- Include load boundaries and 1 ft-or-finer samples in the calculation data.
- Check validation cases 1-3: reactions, max shear, max moment, locations,
  and support-load behavior. Also verify support changes and mixed loads.

### Stage 4: Add deflection and section checks
- Integrate M/EI with inch and kip-in units for simply supported and fixed-end
  boundary conditions.
- Add exact/curve-based maximum deflection lookup, bending stress, allowable
  limits, pass/fail cards, ratios, and bar colors.
- Implement the lightest passing steel or first passing lumber section rule,
  including the no-section result.
- Check validation cases 1-4, especially 20 ft deflection, cantilever
  deflection, lumber behavior, and amber/red thresholds.

### Stage 5: Complete synchronized output interaction
- Add cross-diagram hover behavior with one vertical cursor and exact curve
  values for V, M, and y.
- Label diagram maxima and locations; add the visually exaggerated deflected
  shape with inch labels.
- Add the "use section" button and ensure every input change refreshes all
  outputs immediately.
- Check: hover remains aligned, default and edge-load cases update smoothly,
  and no-pass/use-section behavior is correct.

### Stage 6: Polish responsiveness and final validation
- Refine spacing, shadows, fonts, control units, card formula hover text,
  mobile stacking, and empty/error states.
- Run the full validation matrix and test keyboard, mouse, and small-screen
  behavior.
- Check: all four supplied validation cases match, invalid-input states remain
  clear, and no out-of-scope saving or unsupported beam types appear.

## Resolved notes

- What support type and span should open by default?
  - Resolved: Simply supported / 20 ft.
- How should an invalid span behave?
  - Resolved: show an inline error and stop updating calculations.
- How should the span slider snap?
  - Resolved: 0.1 ft increments.
- What happens to loads when the span changes?
  - Resolved: scale point-load positions and uniform-load bounds proportionally
    to the new span; clamp point positions to the beam endpoints.
- What control should be used for support type?
  - Resolved: radio buttons.
- What range should apply to point-load magnitude and position?
  - Resolved: magnitude 0–100 kips; position 0 to the beam span in ft.
- What range and initial coverage should apply to uniform loads?
  - Resolved: magnitude 0–10 kip/ft; default start 0 ft and default end at
    the beam span.
- What should newly added loads default to?
  - Resolved: 1 kip for a point load and 1 kip/ft for a uniform load.
- What control and default should be used for the material and section?
  - Resolved: separate dropdowns for material and section; default to Steel
    / W12x26.
  Switching to Steel selects W12x26; switching to Lumber selects 2x10.
- What control and default should be used for the deflection limit?
  - Resolved: dropdown with L/240 or L/360; default to L/360.
- How should invalid numeric values and reversed uniform-load bounds behave?
  - Resolved: show an inline error and do not update the calculations.
- How should an equal uniform-load start and end behave?
  - Resolved: treat it as a valid zero-length load, equivalent to no load.
- What numeric-entry precision should be used?
  - Resolved: free numeric entry with no forced step.
- What sign conventions and coordinate system should calculations use?
  - Resolved: x = 0 ft at the left end, positive toward the right, y positive
    upward, positive shear is the sum of upward forces left of the cut, and
    positive moment follows the sagging convention.
- How should deflection be integrated?
  - Resolved: convert x and M to inches and kip-in throughout the integration.
- How should the deflected shape be scaled?
  - Resolved: visually exaggerated; labels remain in inches.
- What should hover values use?
  - Resolved: calculated curve values at the cursor x.
- How should reactions be labeled?
  - Resolved: show kips or kip-ft with upward/downward or moment direction.
- What variables and maximum values needed additional definition?
  - Resolved: E, I, Sx, Fb, L in feet versus inches, absolute maximum shear,
    moment, and deflection, and their locations are now defined.
- What calculation should be used for bending stress?
  - Resolved: convert max moment from kip-ft to kip-in, then divide by Sx
    to get fb in ksi.
- What calculation should be used for check-card ratios?
  - Resolved: fb / Fb for bending and |y|max / allowable deflection.
- What should happen if no section passes?
  - Resolved: display "No passing section." and do not show the use-section
    button.
