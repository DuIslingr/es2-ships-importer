# The ship modules' glow materials, read from their compiled shaders

EVERSPACE 2's ship modules light up through two materials: `M_Vehicles_Floaters_Emissive` (the lights, nozzle glows and
boost vents) and `M_ShipModules_Floaters_Parent` (the detail cards, with the cybernetic glow). Their shader maps were dumped
from the game's IoStore with CUE4Parse (SM5) and disassembled with Wine's d3dcompiler_47. The input signatures (ISGN) give
the registers' meaning, and the material's uniform expression set maps the constant buffer slots to parameters. The
importer's `glow_split` and `floater_split` (tools/build.py) follow what this note describes.

## M_Vehicles_Floaters_Emissive

The forward pixel shader (`001_SF_Pixel`; `013` is the same) reads COLOR0 (the vertex colour, only its red), TEXCOORD0 (the
UV) and the primitive's custom data (thrust, boost). Its material constants, by the preshaders:

| slot | parameter | default |
|---|---|---|
| cb3[1].y / z | ScrollSpeed | 0.3 |
| cb3[1].w | CruiseMode | 0 |
| cb3[2] | EmissiveIntensityHigh x EmissiveColor1 | 20, #3FC0FF |
| cb3[3] | EmissiveIntensityLow x EmissiveColor2 | 2, #FF653F |
| cb3[4] | EngineGlowIntensity x EngineColor | 20, #FFAA59 |
| cb3[5] | BoosterGlowIntensity x BoostColor | 20, #59C4FF |

The emission is

    slot colour x mask x vertex red x flicker

- **The slot is picked by the UV quadrant:**

  | quadrant | slot | when it glows |
  |---|---|---|
  | u < 0.5, v < 0.5 | Emissive 1 | always |
  | u >= 0.5, v < 0.5 | Emissive 2 | always |
  | u < 0.5, v >= 0.5 | the engine colour | x the thrust (a sum of the thrust vector's components, at most 1) |
  | u >= 0.5, v >= 0.5 | the boost colour | x saturate(boost + CruiseMode) |

  The glTF export's v is the Unreal v (the image's row); checked by the lights matched in the game's customization screen,
  23 904 / 23 760 faces in the E1 / E2 quadrants.
- **The mask** is `T_Vehicles_Floaters_Emissive_M`'s red x green, sampled at **twice the UV**, so each quadrant shows the
  whole atlas. Red scrolls sideways (ScrollSpeed) on the rows where sin(4 pi v) < 0, the atlas' band rows.
  - In the two light quadrants the mask is lit wherever red x green > 0: the shader divides by zero there, so there is no
    gradient.
  - In the engine and boost quadrants the gradient is revealed with the thrust a (or the boost):
    smoothstep(saturate((m - (1 - min(2a, 1))) / (1 - 2 max(a - 0.5, 0) - (1 - min(2a, 1))))). At half thrust that is m,
    at full every lit texel.
- **The vertex colour's red** multiplies everything. Faces with red 0 (black, green, cyan vertex colours) never glow,
  whatever their UVs; grey ones (1/3, 2/3) glow dimmer.
- **The flicker** is a damage effect (DamageSize, Min / MaxAmount); left out.

### What changed against the earlier, eyeballed rules

Most of the earlier rules (vertex colour plus atlas row) fell out of the quadrants: the Raptor's nose frame (u >= 0.53,
Emissive 2), the lamps beside it (u 0.43-0.48, Emissive 1), the fins' dots and the strip rows. Over every ship module (the
counts are faces):

| earlier rule | the shader | faces |
|---|---|---|
| white nozzle faces in the engine colour | Emissive 1 (always on) | 39 074 |
| white nozzle faces in the engine colour | the boost colour (boost only) | 10 598 |
| white nozzle faces in the engine colour | Emissive 2 | 515 |
| green "hot discs" (NozzleCore) | dark (vertex red 0) | 27 289 |
| black faces as Emissive 2 | dark | ~10 400 |
| Ring2 faces | Emissive 1 | 6 371 |

The Wraith's blade and wing-tip lights, taken for Emissive 1 against the player's captures, are in the boost quadrant.
Those captures are ES2's Engine Colors page, which runs the engines boosting, and the default boost colour (#59C4FF) looks
like the default Emissive 1 (#3FC0FF).

The black faces were checked against the player's captures: the Nemesis-E9-1 (wings 009, body E = Medium_Body_009, rear 9)
and the Raptor-D1-1 (wings 016, body D = Medium_Body_004, rear 1) have none. The parts that do are body I (014), the
Hawk / Gryphon / Stalker wings, Mercury tier III / IV, Wasp tier IV, light Rear 5, heavy body 5, Rear 7 and the Bomber A /
Liberator / Gunship B wings.

## M_ShipModules_Floaters_Parent

The base pass reads `T_ShipModules_Floaters_001_C_A` (the colour) and `..._R_MT_E` (sampled .yxzw):

    emission = C_A.rgb x R_MT_E.b x "Emissive Intensity" + R_MT_E.a x EdgeLighting^3 x 80 x EdgeLightingIntensity x EdgeLightingColor

- "Emissive Intensity" is 1 in the parent and 30 in MI_ShipModules_Floaters_001. The blue channel lights a block of four
  bars and two small grilles: 230 faces, mostly on cockpits. These always glow.
- **The cybernetic glow** is the alpha channel: three strips at the atlas' top left, u 0 to 0.35. EdgeLighting is the
  game's Cybernetic Glow on / off, its intensity row EdgeLightingIntensity.
- Against the earlier UV box (u < 0.25, v < 0.15): 301 926 faces agree, 3 782 are in the box but on no lit texel, and 475
  are lit outside it (the third strip, u 0.25-0.35).
