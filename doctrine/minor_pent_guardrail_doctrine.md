# Minor Pent Guardrail Doctrine

This document is the human-readable reference for canonical minor pentatonic guardrail topology.

Guardrail ownership is musical topology first and fretboard drawing second. A renderer should not invent ownership. A local cell builder should not invent ownership. Repeated octave regions should inherit from canonical corridor identity.

## Shape Regions

Rectangle is not a border around arbitrary space. Rectangle is a 4-tone pentatonic shape region.

For minor pentatonic:

```text
degrees: 1, b3, 4, 5, b7
rectangle degree set: 1, b3, 5, b7
rectangle omitted degree: 4
```

The rectangle visible rail corridors are:

```text
1 -> b3
5 -> b7
```

Stack is also a pentatonic shape region.

```text
stack degree set: 1, b3, 4, 5, b7
stack visible corridors: b3 -> 4, 4 -> 5
stack omitted corridor: b7 -> 1
```

The omitted `b7 -> 1` corridor is the stack center span. It remains doctrinally meaningful, but it should not draw as a visible rail.

## A Minor / C Major Reference

A minor pentatonic and C major pentatonic are relative views of the same five tones:

```text
A minor pentatonic: A, C, D, E, G
C major pentatonic: C, D, E, G, A
```

For A minor pentatonic:

| Degree | Tone |
|---|---|
| `1` | A |
| `b3` | C |
| `4` | D |
| `5` | E |
| `b7` | G |

Rectangle:

```text
degree set: 1, b3, 5, b7
tones: A, C, E, G
omitted degree/tone: 4 / D
```

Stack:

```text
degree set: 1, b3, 4, 5, b7
tones: A, C, D, E, G
visible corridors: C -> D, D -> E
omitted corridor: G -> A
```

For C major pentatonic:

```text
rectangle tones: C, E, G, A
rectangle omitted tone: D
stack tones: C, D, E, G, A
stack visible corridors: C -> D, D -> E
stack omitted corridor: G -> A
```

## Seed Corridors

| Corridor ID | Degrees | Semitones | Ownership | Color | Visible | Notes |
|---|---|---:|---|---|---|---|
| `minor_pent:1->b3` | `1 -> b3` | 3 | rectangle | red | yes | Rectangle rail/cell boundary |
| `minor_pent:b3->4` | `b3 -> 4` | 2 | stack | blue | yes | Stack rail/cell boundary |
| `minor_pent:4->5` | `4 -> 5` | 2 | stack | blue | yes | Stack rail/cell boundary |
| `minor_pent:5->b7` | `5 -> b7` | 3 | rectangle | red | yes | Rectangle rail/cell boundary |
| `minor_pent:b7->1` | `b7 -> 1` | 2 | omitted | blue | no | Stack center span; do not draw as a rail |

## Shared Edges

Shared edges are physical projected boundaries where rectangle and stack semantics both exist. They are not accidental duplicate lines.

| Shared ID | Degree Pair | Required Owners | Required Colors | Render Doctrine |
|---|---|---|---|---|
| `minor_pent:5<->1` | `5 <-> 1` | rectangle + stack | red + blue | paired rails, tiny controlled gap |
| `minor_pent:b3<->b7` | `b3 <-> b7` | rectangle + stack | red + blue | paired rails, tiny controlled gap |

## Global Ownership Consistency

Every equivalent pitch-class corridor must inherit consistent ownership everywhere on the board unless it is declared as a shared edge or another explicit doctrine exception.

This applies regardless of octave, fret position, local cell construction, string region, low/high E location, or B-string warp projection.

Examples are not special cases:

| Example | Rule |
|---|---|
| `D -> F#` | Same degree-pair/corridor identity must not flip ownership across octaves |
| `E -> F#` | Same degree-pair/corridor identity must not flip ownership across octaves |
| `F# -> A` | Same degree-pair/corridor identity must not flip ownership across octaves |
| `B -> D` | Same degree-pair/corridor identity must not flip ownership across octaves |

## E-String Symmetry

String indexing:

| Index | String |
|---:|---|
| 0 | low E |
| 1 | A |
| 2 | D |
| 3 | G |
| 4 | B |
| 5 | high E |

Strings `0` and `5` are octave-equivalent E strings. Equivalent pitch-class corridors on low E and high E must classify identically modulo octave and fret-range clipping.

B minor examples:

| E-string corridor | Expected ownership |
|---|---|
| `E -> F#` / `4 -> 5` | stack / blue |
| `F# -> A` / `5 -> b7` | rectangle / red |
| `B -> D` / `1 -> b3` | rectangle / red |
| `D -> E` / `b3 -> 4` | stack / blue |

## B-String Warp

B-string warp is a coordinate projection rule, not an ownership rule.

| Crossing | Coordinate transform |
|---|---|
| `G -> B` | target B fret = source G fret + 1 |
| `B -> G` | target G fret = source B fret - 1 |

Valid examples include `G2 -> B3`, `G11 -> B12`, and `G14 -> B15`.

Invalid examples include same-fret shortcuts such as `G2 -> B2` and `G11 -> B11`.

## Octave Propagation

Ownership is keyed by corridor identity:

```text
scale_system + from_degree + to_degree -> ownership
```

It is not keyed by absolute fret, local cell order, renderer order, or whether the occurrence is near the nut.

## Regression Examples

Minimum examples before topology rewrite:

- B minor pent debug board
- C major pent reference board
- low/high E string mirror
- G/B warp valid diagonal
- invalid same-fret G/B shortcut rejection
- shared red/blue boundary preservation
