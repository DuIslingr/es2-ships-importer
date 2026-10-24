# EVERSPACE 2's engine exhaust, decompiled

How EVERSPACE 2 (UE 5.6) draws its ship engine flames, read from the game's own compiled shaders (2026-10-24), so the
remake's `GoF2/ModEngineFlame` (its `_Es2` mode) reproduces them exactly. Nothing from the game is in this repository: the
tools in `tools/shaders` read your own installation.

## How it was read

1. `tools/shaders/ShaderDump` (CUE4Parse, .NET 10) opens the IoStore archives (`ES2_GAME`, `ES2_USMAP`, `ES2_AES_KEY`) with
   shader maps on (`ReadShaderMaps`) and loads `/Game/Assets/Vehicles/Effects/Materials/M_Vehicle_EngineExhaust`. The
   material's shader maps are cooked inline (not in the shared library): `SP_PCD3D_SM5` (18 shaders) and `SP_PCD3D_SM6`.
   Each shader's code is Oodle-compressed; inside is a DXBC container. `uniforms.json` is the material's
   `FUniformExpressionSet`: its numeric parameters and the preshader bytecode that fills each slot of its `Material`
   uniform buffer.
2. `tools/shaders/disasm.c` (llvm-mingw, run in Wine) disassembles the DXBC with `d3dcompiler_47`'s `D3DDisassemble`.
3. Shaders read: pixel shader 012 (the translucent base pass), 005 (the velocity pass: the same opacity, discarded below
   0.337) and the vertex shaders' world position offset.

The material: unlit, `BLEND_TranslucentGreyTransmittance` (alpha blended), two-sided, one texture (`T_Noise_018_M`).
All 139 ship module meshes use it directly (no instance), so its defaults are the ships'.

## Inputs

- Vertex colour: **R** = main flame cards, **G** = boost cards (alpha unused). UV0: u from the nozzle (0) to the card's
  end (1) along the stub, v across.
- Per-ship custom primitive data (`ScalarPrimitiveDataIndexValues` / `VectorPrimitiveDataIndexValues`; custom data starts
  at primitive scene data float4 35): `ThrustAmount` (vector, index 10: x = forward thrust, the shaders saturate it),
  `AngularThrustAmount` (13), `BoostAmount` (16), `TravelMode` (21).
- Parameters (defaults): EngineColor (1, 0.4, 0.1), BoostColor (0.2, 0.6, 1), TravelModeEngineColor (0.1, 0.85, 1),
  CruiseMode 0, OpacityExponent 6, Length 500 (cm), SteeringOffset (0, 0, 0), RefractionFresnelExponent 2; unnamed: 1000
  (emissive), 0.05, 0.0001, 4, -0.008, 128, 0.02. `MI_Vehicle_EngineExhaust_Short` sets Length 150.

Material uniform slots (preshaders decoded: 3 = Parameter, 2 = Constant, 4 Add, 5 Sub, 6 Mul, 7 Div, 11 Max, 12 Clamp,
24 Length, 25 Normalize, 37 Swizzle):
cb[0] EngineColor, cb[1] BoostColor x 2, cb[2] TravelModeEngineColor / 1000, cb[3] SelectionColor (a / rgb),
cb[4] CruiseMode / OpacityExponent / 1 / max(0.05, 1e-4) - 2 = 18 / 1e-4, cb[5] 4 / Length,
cb[6] SteeringOffset normalized x clamp(|SteeringOffset|, 0, 10000) x -0.008 / RefractionFresnelExponent,
cb[7] 128 / 0.02 / RefractionDepthBias.

## Vertex shader (world position offset)

    offset = -LocalX * u * Length * (1 + 4 TravelMode + CruiseMode)          (backward along the ship's -X)
           + u^2 * SteeringOffset' * sat(ThrustAmount.x / |ThrustAmount|) * (1 - MPC[1].w)   (a bend, none at u = 0)
    offset = clamp(offset, -MaxWPODisplacement, MaxWPODisplacement)

The length does not change with thrust: the thrust shows only in the opacity.

## Pixel shader

    colour  = R * EngineColor + G * BoostColor * 2
    colour  = lerp(colour, TravelModeEngineColor, TravelMode) * 1000 * (1 - MPC[1].z) * (1 + MPC[0].w)
    colour  = lerp(colour, SelectionColor.rgb, SelectionColor.a)
    lit     = sat(TravelMode + CruiseMode + sat(Thrust) * (R + G * sat(Boost + CruiseMode)))
    w       = (1 - u) / (1 + 18 u)
    opacity = sat(pow(lit, 6) * (w * 1e-4 + pow(w, 4)) * pow(T_Noise_018_M.r(time * 2, v), 2))
    out     = (colour * fog.a + fog.rgb) * preExposure, alpha = opacity

So: no view-angle term (from behind the flat cards are thin rays by geometry alone); the flame is bright only near full
thrust (thrust^6); it falls off steeply along its length, so its visible length is set by how far 1000 x colour x opacity
stays above the exposure (a short white-hot core ringed in the engine colour, as the game's screenshots show); the noise
is constant along the flame and changes across it and in time (flickering streaks). (MPC = the material parameter
collection F08692C5-4C9E1C96-FE7313BB-586C2CEA, game-wide.)

## What drives it (the blueprints and the exe)

`BP_ShipBase` (its Kismet bytecode, read with ShaderDump's `blueprint` mode) and `AESPawn::UpdatePrimativeDataParamsNative`
(the shipping exe, decompiled with Ghidra by the symbols of the shipped `ES2-Win64-Shipping.pdb`):

- `EngineVFX_Update`, per tick, by `EngineOpacityControlledBy`: 1 (normal control) LinearThrustTarget = the movement input
  (`ShipMovement.GetLastInputVector`, ship frame, X forward), BoostTarget = `bIsBoosting || JumpDrive.IsInCruiseMode`,
  AngularThrustTarget = the pending input rotator (roll, pitch, yaw); 0 (following a spline) LinearThrustTarget =
  ClampVectorSize(velocity in the ship's frame / GetMaxForwardSpeedWithoutBoost, 0, 1), BoostTarget = speed > that speed;
  2 nothing.
- `EaseEngineVFX(current, target, 16, 8)` (angular: 8, 8): VInterpTo(current, target, dt, |target| > |current| ? 16 : 8)
  with dt = `EngineVFXUpdateRate` when above 0 (the player's ship 0.05, `BP_ShipBase` 0.3), else the frame time;
  `EngineVFXEasing` false = the target at once. With 0.3 the alpha is 1: other ships jump to the target.
- `UpdatePrimativeDataParamsNative` per mesh: custom primitive data 10 = LinearThrustCurrent (zero when the VFX are off),
  16 = BoostCurrent, 21 = TravelMode (1 / 0), 13 = AngularThrustCurrent (with AngularThrustEffects); with
  `EngineVFXApplySteeringOffset` (the player's ship) the material parameter `SteeringOffset` = the pawn's velocity rotated
  into the ship's frame (the quaternion conjugate of the root's rotation; the vertex shader adds it in world space).
- The Niagara engine systems get `ThrustAmount` = max(LinearThrustCurrent.X, 0), `BoostAmount`, `LengthFactor`.

## Its engine particles

`InitializeEngineVFX` spawns `EngineTrailSystem` at every `SKT_Engine` socket and `BoostTrailSystem` at every `SKT_Booster`
socket (attached, then turned to the ship's rotation), with `Scale` = the socket's largest scale axis, `Color` =
EngineColor / BoosterColor, `Booster`, `Trail` = SpawnEngineTrails, `Glow` = SpawnEngineGlow, `MirrorScale` = the sign of the
socket's Y. `BP_ShipBase`: `NS_Vehicle_EngineTrail`, glow and trail on; `BP_Ship_Player`: `NS_Vehicle_EngineTrail_Player_Default`
(the customization's engine trail), glow off. Their VM scripts (UE 5.6's legacy VectorVM bytecode; `tools/shaders/niagara.py`
disassembles them: constants are the script's parameters after 640 bytes of engine globals, then its literals; 1280 + 2 x
the parameter size for an interpolated spawn script, 32 for a system script):

- **Player trail** (one ribbon emitter in the system's local space, `M_Vehicle_EngineTrail_Player_Veil`): 50 particles a
  second while the opacity (`Booster ? BoostAmount x ThrustAmount : ThrustAmount`) is above 0; born at `SpawnPositionOffset`
  (100, 0, 0) cm, velocity `BaseVelocity` -2500 cm/s on X, eased each frame toward -(the owner's velocity, local, clamped to
  `InheritVelocityLimit` 20000) by 1 - 0.5^(dt x 0.4) (`NPC_EngineTrails_Player`: smoothing 0.5, falloff time 0.4); lifetime
  `BaseLifetime` 0.4 x 1.1; width 50 cm x the owner's scale; colour `Color` x 5, alpha 0.05 x a 1 -> 0 cosine curve over its
  life x the opacity now; dynamic material parameters (0.8, 2, 0.05, 1.2). The material (no texture; alpha blended):
  across a = max(1 - |2v - 1|, 0), a / (1 + (1/0.8 - 2)(1 - a)), squared; along b = 1 - u, b / (1 + 18 (1 - b)) ^ 1.2 x
  min(20 u, 1)^2; x the particle alpha; x sat((depth - 24 cm) x 0.002).
- **NPC glow** (`NE_Glow`, `M_Vehicle_EngineTrail_Glow`): one camera-facing sprite, 10000 cm x the socket scale, colour
  `Color` x 3 (x 0.5 unless a booster), alpha 0.5 x (`Booster ? BoostAmount : ThrustAmount`) x a LOD distance fade; the
  material r = max(1 - 2 |uv - 0.5|, 0), (r / (1 + 98 (1 - r)))^2 (Bias 0.01, Power 2).
- **NPC trail** (`Trail_0`, `M_ShipTrail_001`, UV tiled every 5000 cm from the start): points spawned per unit distance
  (`SpawnPerUnit` 1000 cm x lerp(1, 5, the LOD fraction)), lifetime 2 x `LengthFactor` x the socket scale, width 500 x
  `Scale`, colour `Color` x (1, or 0.5 unless a booster), alpha (`Booster ? Boost : Thrust`) x pow(sat(velocity^ . the
  owner's forward), 32) at birth; the material: across a, opacity (a^4 + sqrt(max((a - 0.9) x 10, 0))) x 0.5 x alpha, colour
  x 0.5 (BaseIntensity) x (1 + 19 h^3), h = max((sat(1 - u) - 0.9) x 10, 0) (SourceIntensity 20).

## The player's engine lights

`BP_Ship_Player.CreateEngineLight`: a point light per `SKT_Engine` socket (EngineColor) and per `SKT_Booster` socket
(BoosterColor), attenuation radius 300 cm x the socket scale, soft source radius 100 cm x it; per tick intensity
`EngineVFXLightIntensity` (20) x LinearThrustCurrent.X (boosters: x BoostCurrent).

## The manoeuvring jets

`BP_Ship_Player` spawns `P_Vehicle_LateralThruster` (Cascade) at every `SKT_LateralThruster` socket with `Color` =
LateralThrusterColor; per tick, f the emitter's forward:

    Opacity = sat(f . -input_world + sat(f . v^) x (Deceleration > 0) x (|input| = 0) + sat(f . -Z) x (gravity <> 0))
    Boost   = max(f . -input_world x bIsBoosting, sat(f . -Z) x (gravity <> 0))

(v^ = the velocity's direction; -v^ while following a spline), or `LateralThrustersOpacityOverride` when above 0; hidden
in the first-person camera. The system: a `PSA_Rectangle` sprite locked to rotate about X, 300 x 80 cm, and a "Front" sprite
locked to face X, 100 x 100 cm, 10 cm toward the camera, both colour `Color` x 20 and alpha `Opacity` x (1 + 3 `Boost`); a
lights-only emitter (radius 200 cm, exponent 16, brightness 1..5, 10 cm out). `M_Vehicle_LateralThruster`: d = 2 |uv - 0.5|,
s = sat(max(1 - d, 0) x 1.05), s / (1 + 18 (1 - s)), ^ (2 + sqrt(noise(time x 100))), x sat((u - 0.5) x 10) (the half
beyond the socket), x the particle alpha; additive.

## Not used

`P_Vehicle_EngineGlow` (Cascade): its Haze, Trail and Debug emitters are disabled and no blueprint above spawns it; its
lens-flare streak (`M_LensFlare_Streak`) and light were an older engine glow. The other engine trails of the customization
(`NS_Vehicle_EngineTrail_Player_*`: Veils, Sparks, FireTrail, ...) are not decoded yet.
