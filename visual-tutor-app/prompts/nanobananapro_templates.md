# Nano Banana Pro Prompt Templates

Templates for generating high-quality educational diagrams with Nano Banana Pro.

## General Structure

All prompts should include:
1. **Clear Description** - What the diagram shows
2. **Spatial Layout** - Where elements are positioned
3. **Text Labels** - What text must appear
4. **Color Coding** - How colors are used
5. **Style Notes** - Visual style preferences

---

## Mathematics Templates

### Algebra - Equation Solving

```
Create an educational diagram showing step-by-step equation solving for: [EQUATION]

LAYOUT:
- Title at top center: "Solving [EQUATION]"
- Steps arranged vertically, numbered 1-N
- Each step shows the equation transformation
- Arrow between each step with operation label

TEXT REQUIREMENTS:
- Step numbers clearly visible
- Operation labels (e.g., "subtract 3 from both sides")
- Final answer highlighted in a box

COLORS:
- Black text for equations
- Blue for operation labels
- Green highlight for final answer
- Light gray background for step boxes

STYLE: Clean, minimalist, textbook-quality
```

### Geometry - Triangle Properties

```
Create an educational diagram explaining [PROPERTY] of triangles.

LAYOUT:
- Large, clear triangle in center
- Labels for vertices (A, B, C)
- Angle markers at each corner
- Side length labels if relevant
- Annotation arrows pointing to key features

TEXT REQUIREMENTS:
- Vertex labels: A, B, C
- Angle measurements or variables
- Property name as title
- Brief formula or rule below diagram

COLORS:
- Triangle outline: dark blue
- Angle arcs: red
- Height/altitude: green dashed line
- Labels: black

STYLE: Geometric, precise, educational
```

### Calculus - Derivative Visualization

```
Create a visual explanation of the derivative concept showing:

LAYOUT:
- Coordinate system with clear axes
- Smooth curve representing f(x)
- Tangent line at point (a, f(a))
- Secant line showing Δy/Δx
- Zoomed inset showing limit process

TEXT REQUIREMENTS:
- Axis labels (x, y)
- Function label: y = f(x)
- Point label: (a, f(a))
- Slope notation: f'(a) = lim[Δx→0] Δy/Δx

COLORS:
- Curve: blue
- Tangent line: red
- Secant line: orange (lighter)
- Point marker: green

STYLE: Mathematical, precise with smooth curves
```

---

## Physics Templates

### Mechanics - Force Diagram

```
Create a free body diagram showing forces acting on [OBJECT] in [SITUATION].

LAYOUT:
- Object represented as simple shape at center
- Force arrows originating from center of object
- Arrow length proportional to force magnitude
- Force labels at arrow tips
- Net force indicator (if applicable)

TEXT REQUIREMENTS:
- Force labels: F_gravity, F_normal, F_friction, etc.
- Magnitude values if known
- Direction indicators (up, down, left, right)

COLORS:
- Weight/Gravity: RED (pointing down)
- Normal force: GREEN (perpendicular to surface)
- Friction: ORANGE (opposing motion)
- Applied force: BLUE
- Tension: PURPLE

STYLE: Schematic, physics textbook standard
```

### Electricity - Circuit Diagram

```
Create a circuit diagram showing [CIRCUIT DESCRIPTION].

LAYOUT:
- Components arranged in logical flow
- Clear wire connections
- Standard circuit symbols
- Current direction arrows
- Voltage polarity marks

TEXT REQUIREMENTS:
- Component labels (R₁, C₁, etc.)
- Component values
- Current labels (I₁, I₂)
- Voltage labels (V₁, V₂)

SYMBOLS:
- Resistor: zigzag line
- Capacitor: parallel lines
- Battery: long/short parallel lines
- Switch: break with dot
- Bulb: circle with X

COLORS:
- Wires: black
- Current arrows: blue
- Voltage labels: red
- Component labels: black

STYLE: Technical schematic, IEEE standard
```

### Waves - Wave Properties

```
Create a diagram illustrating [WAVE PROPERTY] for [WAVE TYPE].

LAYOUT:
- Horizontal axis representing distance/time
- Wave shown as sinusoidal curve
- Wavelength/period marked with arrows
- Amplitude marked with vertical arrows
- Reference line (equilibrium)

TEXT REQUIREMENTS:
- Axis labels
- λ (wavelength) or T (period)
- A (amplitude)
- Crest and trough labels

COLORS:
- Wave: blue
- Wavelength markers: red
- Amplitude markers: green
- Reference line: gray dashed

STYLE: Clean, scientific diagram
```

---

## Chemistry Templates

### Atomic Structure

```
Create a diagram of [ELEMENT] atomic structure.

LAYOUT:
- Nucleus at center (protons + neutrons)
- Electron shells as concentric circles
- Electrons distributed according to shell capacity
- Shell labels (K, L, M or 1, 2, 3)

TEXT REQUIREMENTS:
- Element symbol and name
- Atomic number
- Number of protons, neutrons, electrons
- Electron configuration

COLORS:
- Protons: RED
- Neutrons: GRAY/BLUE
- Electrons: BLUE dots
- Nucleus: warm colors
- Shells: light gray circles

STYLE: Bohr model style, educational
```

### Chemical Reaction

```
Create a diagram showing the reaction: [REACTION EQUATION]

LAYOUT:
- Reactants on left side
- Arrow in middle (single → or double ⇌)
- Products on right side
- Molecular structures if applicable
- Energy diagram below (if relevant)

TEXT REQUIREMENTS:
- Chemical formulas
- Coefficients
- Reaction conditions above arrow
- State symbols (s), (l), (g), (aq)

COLORS:
- Different elements: standard CPK colors
  - Carbon: black
  - Oxygen: red
  - Hydrogen: white
  - Nitrogen: blue
- Reaction arrow: black
- Condition text: gray

STYLE: Chemistry textbook, clear molecular representations
```

---

## Biology Templates

### Cell Structure

```
Create a labeled diagram of a [CELL TYPE] cell.

LAYOUT:
- Cell outline showing shape characteristic of cell type
- Organelles positioned appropriately
- Leader lines connecting labels to structures
- Scale bar or size indication

TEXT REQUIREMENTS:
- Cell type name as title
- Labels for all major organelles
- Brief function notes (optional)

STRUCTURES TO INCLUDE:
- Nucleus (with nucleolus)
- Cell membrane
- Cytoplasm
- Mitochondria
- Endoplasmic reticulum (rough and smooth)
- Golgi apparatus
- [Additional cell-type specific structures]

COLORS:
- Nucleus: purple
- Mitochondria: orange
- ER: blue
- Golgi: yellow/green
- Membrane: brown/tan

STYLE: Scientific illustration, textbook quality
```

### Process Flow - Photosynthesis/Respiration

```
Create a process diagram showing [BIOLOGICAL PROCESS].

LAYOUT:
- Input materials on left
- Process steps in middle (sequential)
- Output materials on right
- Energy flow indicators
- Location labels (chloroplast/mitochondria)

TEXT REQUIREMENTS:
- Process name as title
- Input labels (CO₂, H₂O, glucose, O₂)
- Output labels
- Energy indicators (ATP, NADPH)
- Step numbers or names

COLORS:
- Energy molecules: yellow (ATP)
- Oxygen: red
- Carbon dioxide: gray
- Water: blue
- Glucose: green
- Process arrows: black

STYLE: Flow diagram, biochemistry standard
```

---

## History Templates

### Timeline

```
Create a historical timeline for [TIME PERIOD/TOPIC].

LAYOUT:
- Horizontal timeline at center
- Events marked above and below line (alternating)
- Date markers along timeline
- Brief event descriptions
- Optional: images/icons for major events

TEXT REQUIREMENTS:
- Time period title
- Dates (years)
- Event names
- Brief descriptions (10-15 words max)

COLORS:
- Timeline: dark gray
- Date markers: black
- Event boxes: alternating light blue/light green
- Important events: highlighted in gold/yellow

STYLE: Clean, informational, easy to scan
```

### Cause and Effect

```
Create a cause-and-effect diagram for [HISTORICAL EVENT].

LAYOUT:
- Causes on left side (multiple boxes)
- Central event in middle (highlighted)
- Effects on right side (multiple boxes)
- Arrows showing connections
- Time flow indicator (left to right)

TEXT REQUIREMENTS:
- Event name (central, prominent)
- Cause labels (numbered if sequential)
- Effect labels (short-term and long-term)
- Dates where relevant

COLORS:
- Causes: blue boxes
- Central event: red/orange box
- Effects: green boxes
- Arrows: gray
- Timeline: dotted line

STYLE: Organizational, concept map style
```

---

## Universal Best Practices

### Text Rendering
- Use clear, sans-serif fonts
- Ensure sufficient contrast
- Keep labels concise
- Position labels close to elements they describe

### Layout
- Leave adequate whitespace
- Align elements for visual harmony
- Use consistent spacing
- Follow natural reading order (left-to-right, top-to-bottom)

### Color Usage
- Use consistent color coding throughout
- Ensure accessibility (avoid red-green only distinctions)
- Use color to highlight, not decorate
- Keep color palette limited (3-5 main colors)

### Accessibility
- High contrast text
- Clear visual hierarchy
- Not relying on color alone for meaning
- Adequate size for all elements
