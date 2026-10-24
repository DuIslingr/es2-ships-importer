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

## Not yet reproduced

The engines' other parts, in `P_Vehicle_EngineGlow` (Cascade): a GPU heat haze (`M_Particle_Haze_001`), a lens-flare streak
(`M_LensFlare_Streak`, 150 x 2, rectangle aligned), a point light (brightness 30), a ribbon trail (`M_ShipTrail_001`, rate
by its "Trail" parameter up to 30); `P_Vehicle_LateralThruster` (the manoeuvring jets); `P_Vehicle_EngineTrail`; the
customization's exhaust particles (`DT_ShipExhaustParticles`). The steering bend (SteeringOffset is set by game code).
