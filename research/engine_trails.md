# EVERSPACE 2's engine trails (the customization's "Engine trail" / "Booster trail")

Decompiled 2026-10-25 from the game's own files (nothing of them is in this repository): `DT_ShipExhaustParticles` (the
choices), `BP_Ship_Player.UpdateEngineTrails` (Kismet), the `NS_Vehicle_EngineTrail_Player_*` Niagara systems (their VM
bytecode, `tools/shaders/niagara.py`; the parameter stores, curves and renderers from FModel's JSON export) and their
materials' compiled shaders (SP_PCD3D_SM5, disassembled with d3dcompiler_47). The remake runs them in
`Modding.Es2Trails` / `GoF2/ModEs2Trail`; this importer writes the table, curves, textures and meshes (`tools/trails.py`).

## The choice

`DT_ShipExhaustParticles` has 13 rows (row name = the id, `ParticlesName`, `ParticleSystem`, `Icon`):

| Row | Name | System |
|---|---|---|
| Default | Default | NS_Vehicle_EngineTrail_Player_Default (the veil, engine_exhaust.md) |
| Glitter | Stardust | ..._Glitter |
| Rings | Rings of Nerea | ..._Rings |
| Veils | Ion Veils | ..._Veils |
| Triangles | Delta Surge | ..._Triangles |
| Squares | Tetragons | ..._Squares |
| FireTrail | Thermal Blaze | ..._FireTrail |
| Sparks | Firestarter | ..._Sparks |
| Lightning | Voltaic Tendrils | ..._Lightning |
| SpeedLines | Residuum | ..._Lines |
| Smoke | Raw Combustion | ..._Smoke |
| Bubbles | Coolant Leak | ..._Bubbles |
| DarkTrail | Void Reverb | ..._DarkTrail |

A ship has two: `ThrustParticlesID` for the engine sockets (components tagged "Thruster") and `BoostParticlesID` for the
booster sockets ("Booster"); `UpdateEngineTrails` sets each component's asset (an invalid id: the Default system). The
inputs are the ones the Default system has (`User.Color` = EngineColor / BoosterColor, `Scale` = the socket's scale,
`ThrustAmount`, `BoostAmount`, `Booster`); `User.SpeedFactor` is each system's own default (Bubbles 0.7, Sparks 1.5).

## What every system shares

- `NPC_EngineTrails_Player` (a parameter collection): BaseVelocity -2500 cm/s (local X), BaseLifetime 0.4 s,
  SpawnPositionOffset (100, 0, 0) cm, InheritVelocityFalloffTime 0.4, InheritVerlocityFalloffSmoothing 0.5,
  InheritVelocityLimit 20000 cm/s, HangarMode 0 (1 in the hangar's customization screen).
- The emitters are in local space (the socket, turned to the ship). The opacity input `InputOpacityResult` =
  `Booster ? BoostAmount x ThrustAmount : ThrustAmount`; a spawn rate's particles are only born while it is above 0
  (Sparks: always). Spawns are interpolated over the frame.
- Inherited velocity: the target is -(the owner's velocity in local space, clamped to 20000), each particle's velocity eased
  toward it by `1 - 0.5^(dt x 0.4 [x SpeedFactor])` a frame (at spawn: by its age): the particles come to rest in the world.
  In HangarMode the velocity stays the spawn velocity, every colour is x 4 and every alpha is squared.
- Curves are 128-entry LUTs (`NiagaraDataInterfaceCurve.ShaderLUT`) over the normalized age.
- Material inputs: Niagara's sprite / ribbon / mesh vertex factories give the particle colour (rgb x the alpha), the
  relative time (normalized age), MaterialRandom and the dynamic parameter; a ribbon's U0 / V0 / U1.
- Every trail material is unlit and `BLEND_TranslucentGreyTransmittance` (alpha blended) except Smoke (volumetric lit).
  Their emissive is x (1 + `MPC_GlobalParameters.EmissiveExposureCompensation`, 10): every ES2 effect has it, so the
  remake's `_Gain` (ModMaterials.Es2FlameGain / 1000) already holds it.
- Engine textures the materials use: UE's `View.PerlinNoiseGradientTexture` (128 x 128, a gradient of the 12 cube-edge
  midpoints per texel, `FRandomStream(12345)`) for the simplex noise of Bubbles, and `View.PerlinNoise3DTexture` (16^3, a
  gradient per texel stored x 127 + 127 and in alpha 127 + dot(gradient, the texel)) for the gradient noise of Lightning.
  The remake makes both the same way (the bytes may differ from UE's; the noise is statistically the same).

Units below: cm and seconds (ES2's); U = uniform random, curveN = the system's Nth curve.

## The systems

### Glitter ("Stardust") - sprites, M_Vehicle_EngineTrail_Player_Glitter
Rate 200 x Scale /s while opacity > 0. Life U(0, 0.8) x 0.4. Born in a box of 50 x Scale cm around the socket, velocity a
2.5 deg cone (cos in [0.999048, 1]) about local X x BaseVelocity. Size 50 x (1 + U). Colour = User.Color; alpha =
Color.a x U(0, opacity) x curve0. Material (texture T_Pattern_Barcode_001): twinkle = sat((sqrt(barcode(Time x 0.5 +
MaterialRandom, 0)) - 0.5) x 2); colour x (1 + 40 twinkle); r = max(1 - 2 |uv - 0.5|, 0); a = r / (1 + (1 / (0.05 -
0.04375 twinkle) - 2)(1 - r)); alpha a^3 x particle alpha x min(camera distance x 0.002, 1).

### Smoke ("Raw Combustion") - sprites, ViewDepth sort, M_Vehicle_EngineTrail_Player_Smoke (lit)
Rate 200 / Scale. Life 0.4 x (0.7 + U(0, 0.3)). Born at the socket, velocity a 4 deg cone (cos >= 0.997564) x
BaseVelocity (no SpeedFactor). Size 100 x (0.5 + U(0, 0.5)) x Scale x lerp(1, 3, curve0). Rotation U(0, 360). Colour =
User.Color x 10, alpha = Color.a x opacity^3 x (1 + U) x curve1. DynamicMaterialParameter.x = U.
Material: normal T_Sphere_001_N (tangent space of the sprite); base colour sat(0.3 x (0.5 + 0.5 MaterialRandom) x
sqrt(T_SmokeSeamless_001_H(uv x 0.5 + Dyn.x))); emissive pow((1 - t) / (1 + 18 t), 2.5) x colour (t = relative time); opacity
T_SmokePuff_002_M(uv) x alpha x sat((scene depth - pixel depth) x 0.005). Lit by the translucency lighting volume
(directional): here the main light and the ambient.

### Bubbles ("Coolant Leak") - sprites facing the camera, M_Vehicle_EngineTrail_Player_Bubbles
SpeedFactor 0.7. Rate 50 x Scale x opacity. Life (0.4 + U(0, 0.3)) x 0.4 / SF. Box 50 x Scale, cone 5 deg x BaseVelocity x
SF, inherit falloff x SF. RotateAroundPoint: a random unit axis per particle, the position circling it at 1 turn/s with
radius 10 x the normalized age. Size 10 x (1 + U) x lerp(1, 3, curve1). Colour = User.Color x lerp(1, 10, curve0), alpha =
Color.a x curve2. Dyn.x = U.
Material: N = T_Sphere_001_N; a highlight H = normalize(V + 0.1): spec = sat((sat(H.N) - 0.95) x 20), spec^2 x 10; emissive
spec + colour. Opacity: r = max(1 - 2 |uv - 0.5|, 0); a bubble pops with noise: turb = |simplex3(N.xy x 0.5 x (1 - r)^3,
Dyn.x) x 32|; visible where (1 - r)(1 - turb) >= 1 - alpha; x min(50 r, 1) x (fresnel (1 - max(N.V, 0))^3 x 0.98 + 0.02).

### Sparks ("Firestarter") - velocity-aligned sprites, M_Particle_Spark_001
SpeedFactor 1.5. Rate 50 x SF x Scale (always). Life 0.4 / SF x 0.8. Box 50 x Scale, cone 5 deg x BaseVelocity x SF.
Size 2 x (1 + U); drawn (lerp(1, 2, speed / 1000) , lerp(1, 20, speed / 1000)) x curve0 x it (y along the velocity).
Colour User.Color x 50, alpha = Color.a x U(0, opacity) x (1 - normalized age).
Material: a stadium: s = normalize(size.yx); p = max((uv - (1 - s)) / s, min(uv / s, 0.5)); d = 2 |0.5 - p|;
a = min(max(1 - d, 0) x 10, 1)^2; alpha min(alpha^2 x a, 1); colour = the particle's.

### DarkTrail ("Void Reverb") - ribbon (TiledOverRibbonLength 800, RibbonUVDistance), M_..._DarkTrail
Rate 50. Life 0.44. Born at SpawnPositionOffset, BaseVelocity on X. Width 60 x Scale. Colour x 10, alpha Color.a x
opacity^4 x curve0 x 10. Dyn.x = 0 (UVOffset).
Material (T_Noise_020_M): a = max(1 - |2V - 1|, 0); n = noise(-Time x 0.7 + 0.15 U0 + Dyn.x, 0.3 fold(V) + Dyn.x), fold(V) =
V <= 0.5 ? V : 1.5 - V; p = a^(1 / (1 - n)^3); emissive (1 - p)^32 x colour; opacity bias(a, p)^1.5 x U1^2.5 x
min(5 (1 - U1), 1)^2 x alpha x sat((camera depth - 24) x 0.005)^2 (bias(x, b) = x / ((1/b - 2)(1 - x) + 1)).

### FireTrail ("Thermal Blaze") - ribbon (TiledOverRibbonLength 800), M_..._FireTrail
Rate 50. Life 0.44. Width 80 x Scale. Colour x 30, alpha Color.a x opacity^4 x curve0.
Material (T_Noise_020_M): uv = (0.5 U0 - 3 Time + Dyn.x, 0.5 V + Dyn.x); n = min(tex(uv + (0, 0.7 Time)),
tex(uv + (-0.7 Time + 0.5, 0.5))); opacity (n x max(1 - |2V - 1|, 0))^2 x (s / (1 + 18 (1 - s)))^1.5 x min(10 (1 - s), 1)^2
x alpha x sat((scene depth - pixel depth) x 0.002)^2, s = sat(1 - U1); emissive = colour.

### SpeedLines ("Residuum") - ribbon (ScaledUsingRibbonSegmentLength), M_..._Lines
Rate 50. Life 0.4. Width 60 x Scale. Colour x 10, alpha Color.a x opacity^2 x curve0.
Material (T_Noise_012_M): uv = ((0.05 U0 - 0.2 Time) x 0.25 + Dyn.x, V x 0.25 + Dyn.x); n = sat((sqrt(tex) - 0.3) / 0.7);
opacity sat(n x max(1 - |2V - 1|, 0) x s / (1 + 18 (1 - s)) x min(10 (1 - s), 1)^2 x alpha); emissive = colour.

### Lightning ("Voltaic Tendrils") - a ribbon and arc sprites
Ribbon (TiledOverRibbonLength 2000): rate 50, life 0.4, width 120 x Scale, colour x 100, alpha Color.a x opacity^4 x
curve0. Material M_..._Lightning: n = turbulence gradient noise, 6 octaves, of ((U0 - 2 Time, 0.25 V) x 2, Time x 5) + Dyn.x,
x 2 - 1; s = sat(1 - U1); y = n x (1 - s)^0.25 x 0.5 + V; band = min(max(1 - |2y - 1|, 0) x 1.0101, 1); opacity
sat((band / (1 + 98 (1 - band)))^2 x (s / (1 + 18 (1 - s)))^1.5 x min(20 (1 - s), 1)^2 x alpha).
Arcs (sprites, pivot (0, 0.5), rotation U(0, 360)): rate 20 while opacity > 0, life (0.5 + U(0, 0.5)) x 0.4, size
(1 + U) x 80 x Scale, drawn (0.5 curve0 x it, curve0 x it); colour x 5000, alpha Color.a x U(0, 2) x opacity x curve1;
Dyn = (0, 0, sat(4 x normalized age), 0.01). Material MI_Particle_Lightning_Arc: n = gradient noise (6 octaves, x 3 each,
amplitude / 3) of (3 (uv + Dyn.xy), 3); y = n x 0.3 x u^0.2 + v; band = max(1 - |2y - 1|, 0); core = sat((band - 0.95) /
0.05)^16; the arc grows out from the pivot: w = smoothstep(e - 0.05, e + 0.05, 1 - u), e = 1.2 (1 - Dyn.z) - 0.1; colour x
(1 + core x (1 - w)^2 x 1000); opacity sat(alpha^2 x (core + Dyn.w x bias(band, 0.0002)) x max(1 - |2u - 1|, 0)^2 x w x
flicker), flicker = sqrt(barcode(Time, 0)) (T_Pattern_Barcode_001).

### Rings / Squares / Triangles ("Rings of Nerea", "Tetragons", "Delta Surge") - mesh particles
SM_CrossShape_Circle / _Square / _Triangle (a cross section 1 cm deep along X), M_Vehicle_EngineTrail_CrossShape (two
sided). Rate 15 while opacity > 0. Life 0.4. Born at the socket, BaseVelocity on X. Scale 25 x Scale x (2, 1, 1); Rings x
curve1 (2 -> 0.5). Colour x 0.5, alpha Color.a x opacity x curve0. Triangles turn about X by 2 pi x 0.3 x the emitter's age
at birth. Material: g = u / (1 + 3 (1 - u)) (the mesh's UV u), opacity sat(g^3 x alpha x sat((camera depth - 24) x 0.002)
x |N.V|^2); emissive = colour.

### Veils ("Ion Veils") - two ribbons, M_Vehicle_EngineTrail_Player_Veil
Each: rate 50, life 0.4, width 50 x Scale, colour x 5, alpha Color.a x opacity^4 x curve0; velocity (BaseVelocity, 200 w(phi_y),
200 w(phi_z)) with w(phi) = (sin phi + sin 2.67235 phi + sin 1.23498 phi) / 3, phi = 10 Time + 10 x a fixed random per
emitter and axis. Dynamic parameters (0.05, 2, 0.05, 1.5) and (0.05, 2, 0.05, 1): the veil material's across bias,
across power, along bias, along power (Default: 0.8, 2, 0.05, 1.2).
