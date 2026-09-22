---
name: Aonic Sourcing Engine
description: Sourcing rendered as a structure under load, on Aonic's own ground.
colors:
  paper: "#fcfbf9"
  paper-sunk: "#f3f1ec"
  paper-deep: "#eae7df"
  ink: "#171614"
  ink-2: "#5b564e"
  ink-3: "#8b8479"
  rule: "#ddd8ce"
  rule-strong: "#bdb6a8"
  tension: "#c4402f"
  tension-wash: "#f7e9e5"
  slack: "#aaa49a"
  sand: "#c9b48a"
  sand-deep: "#8a6d3b"
  sand-wash: "#f5efe2"
  breach: "#a6301f"
  breach-wash: "#f9e6e2"
typography:
  display:
    fontFamily: "Inter Tight, system-ui, sans-serif"
    fontSize: "clamp(28px, 3.4vw, 42px)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.022em"
  heading:
    fontFamily: "Inter Tight, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.02em"
  body:
    fontFamily: "Inter Tight, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "10px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.14em"
  figure:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "-0.01em"
rounded:
  none: "0px"
spacing:
  gutter: "24px"
  gutter-mobile: "16px"
  rail: "208px"
  section: "28px"
  row: "11px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "11px 18px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "11px 18px"
  button-danger:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.breach}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "11px 18px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.figure}"
    rounded: "{rounded.none}"
    padding: "10px 12px"
  node:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "14px 16px"
---

# Design System: Aonic Sourcing Engine

## Overview

A buyer's working tool, drawn as a tensegrity structure. Every offer is a strut, the price ceiling is a fixed vertical member nothing may cross, and the negotiation is a red cord pulling each strut toward it. The world was chosen from a bolder re-roll (Breathing Column) and translated onto Aonic's pinned brand: the source's concrete ground became Aonic's off-white, and its carbon rods and nylon cord became drawn line weight, since no product photography was available.

The surface is operational. A buyer returns to it in short bursts, reads where a run is holding and where it is about to fail, and acts at two gates. Expression lives in precise detail: hairline rules, clipped corners, leader lines to node readings, signed tabular figures. Nothing is decorative that does not also carry state.

Light, by scene: a buyer at a desk in daylight, reading numbers against limits.

## Colors

### Primary

**Tension red `#c4402f`** is the only accent with authority. It carries everything under live load: the current rail link, the approval waiting on a person, the red trace through a primary action, the cord in the force field, a counted escalation. Use it where something is moving or waiting. Never as decoration.

### Secondary

**Sand `#c9b48a` and sand deep `#8a6d3b`** are Aonic's own accent, reserved for a settled state: an agreed offer, the leading row in a ranked table, a measured value approaching its limit, and every notice that states an assumption. Sand says "this is decided" or "this is ours, not the supplier's".

### Tertiary

**Breach `#a6301f`** marks a limit crossed: a failed certificate line, a price over the ceiling. It is darker than tension on purpose. Tension is activity; breach is a fault.

### Neutral

**Paper `#fcfbf9`** is the ground everywhere. **Paper sunk** and **paper deep** are the only fills, for hover and inset tracks. **Ink `#171614`** carries text and structure, with **ink 2** for secondary text and **ink 3** for labels. **Rule** and **rule strong** draw every hairline. **Slack `#aaa49a`** is a member under no load: a struck, void or walked-away supplier.

### Named Rules

**The One Force Rule.** Red appears only where something is under load right now. A page at rest is ink on paper.

**The Never Colour Alone Rule.** Every verdict pairs its colour with a mark and a word: a filled circle for pass, a rotated square for fail, a hollow circle for pending, a hatched square for void. A buyer who cannot see red still reads every state.

**The Assumption Rule.** Anything the engine did not read from a supplier or from Aonic, such as a specification limit or a freight rate, sits on a sand notice that says so.

## Typography

Inter Tight is Aonic's own face and carries every word. JetBrains Mono carries every number, code and label, so figures align in columns and a label never competes with the content it names.

### Hierarchy

1. **Display**, Inter Tight 600 at 28 to 42px, tracked in to -0.022em. Page titles only.
2. **Heading**, Inter Tight 600 at 15px, tracked slightly open, over a full-width ink rule. Section heads.
3. **Body**, Inter Tight 400 at 15px, 1.5 line height, measure held under 68 characters.
4. **Figure**, JetBrains Mono with tabular and slashed-zero numerals. Every price, ppm and day count.
5. **Label**, JetBrains Mono 500 at 10px, uppercase, tracked to 0.14em, in ink 3. The one label style in the system.

### Named Rules

**The Two Voices Rule.** Words are set in Inter Tight, measurements in JetBrains Mono. A number set in the sans, or a sentence set in the mono, is a defect.

## Layout

A fixed left rail of 208px holds navigation in mono caps, with the current page marked by a red left rule. The stage to its right opens with a ruled head block, title and description on the left and a readout of three or four figures on the right. Sections follow at a 28px rhythm, each opened by a heading over a full-width ink rule with a mono note flush right. Data sits in ledger tables ruled with hairlines, never in card grids.

Below 900px the rail becomes a horizontal strip, the readout wraps, section notes drop below their heading, and every ledger scrolls inside itself so the page never scrolls sideways.

## Elevation & Depth

Flat. Depth comes from rules and fills, never from shadow. A recessed track is paper deep; a hovered row is paper sunk. The system defines two shadows for future use and ships none of them on screen.

## Shapes

Square. No radius anywhere. The one shape with character is the **clipped corner**: primary buttons clip their top-right corner by 9px and node blocks by 12px, taken from the machined end of a strut. Circles appear only as node points in the force field and as verdict marks.

## Components

### Buttons

Mono uppercase label at 11px, tracked 0.1em, with a 1px ink border and the clipped top-right corner. **Primary** is filled ink with a small red trace drawn through it, the same polyline as the force field, and there is only ever one primary per decision. **Secondary** is ink outline on paper. **Danger** is a breach outline. Disabled drops to rule strong and ink 3.

### Cards / Containers

The **node** is the only container: a hairline-bordered block on paper with a clipped corner, holding one reading or one decision. A node under live load takes a tension border; one in breach takes a breach border; an agreed one takes sand. Nodes never nest.

### Inputs / Fields

Mono text on paper in a 1px rule-strong frame, square. The border darkens to ink 3 on hover and turns tension on focus. The label sits above in the label style.

### Navigation

The rail: wordmark set in type, a label, then mono uppercase links. The current link is red with a red left rule and a paper-sunk fill. A count of waiting approvals sits flush right in red and bold.

### Force Field

The signature component. An SVG column of struts, one per offer, positioned horizontally by normalised delivered price against a single vertical ceiling line. Each strut tilts in proportion to its distance from the ceiling, carries a node point that turns breach when over, and a dashed red cord back to the ceiling whose weight grows with the rounds of negotiation. Leader lines run left to the supplier name and right to the signed reading: the price and how far over or under it sits.

### Load Bar

A 3px track with a fill and a 1px limit tick at the end, reading a measured value against its limit. Ink below 80% of the limit, sand deep from 80% to the limit, breach beyond it. Used for every certificate line and every price against its ceiling.

### Approval Node

A node under tension holding one decision: the headline, one sentence on why a person is needed, the evidence (the shortlist with reasons, the failing certificate lines, the price against the ceiling, or the ranked award table), the choices as buttons, and each choice's consequence written out beneath. A buyer can act without opening anything else.

## Do's and Don'ts

### Do:

- **Do** show the reason beside every automated decision: every cut supplier, every counter, every failed line.
- **Do** set every figure in tabular mono with its sign and unit.
- **Do** keep a walked-away or voided item visible, struck in ink 3. Nothing disappears; it cancels.
- **Do** label anything simulated or assumed, on a sand notice.
- **Do** write a control as the action it takes: "Approve and send the RFQ", never "Submit".

### Don't:

- **Don't** use red for anything not under live load.
- **Don't** round a corner. Clip it, or leave it square.
- **Don't** put data in a grid of same-size cards. Use a ledger.
- **Don't** let a verdict rely on colour alone.
- **Don't** add a label above a heading. The heading carries its own weight.
