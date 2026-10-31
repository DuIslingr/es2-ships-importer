# EVERSPACE 2's warp, travel-mode and cruise effects

What EVERSPACE 2 (UE 5.6) draws when the ship goes to supralight travel, jumps through a gate, charges its jump drive or
cruises, read from FModel's JSON export of the game's assets (2026-10-30), for the remake's planned warp flight (the
Khador sequence as a flyable space between the systems, masked by these effects: built, `tools/drives.py` ships the tunnel's
three texture layers and two sounds) and the cruise drive's own feedback.
Nothing from the game is in this repository: the README's export table says which folders to export and
`tools/warp_assets.txt` what `tools/shaders`' `export` adds (the tunnel meshes, the shared noise textures, the materials
resolved through their parent chains).

## The effects and their assets

| Effect | Assets (ES2/Content/...) |
|---|---|
| **Travel mode's warp tunnel** (the supralight look while travelling between points of interest) | `Assets/TravelMode/Effects/Materials/M_TravelMode_WarpTunnel` (additive, unlit, two-sided, depth test off; samples five noise textures, the warp mask function `MF_TravelMode_WarpMask` and the collection `MPC_TravelMode`), its jump variant `MI_TravelMode_WarpTunnel_Jump` (`SpeedFactor` 0.5) |
| **Speed particles** (the streaks and debris flying past) | `Assets/TravelMode/Effects/Particles/P_TravelMode_SpeedParticles` (Cascade; emitters Clouds, Debris, Lights) with `M_TravelMode_SpeedParticles_Clouds` / `_Debris`; the instances `Assets/Effects/Materials/MI_SpeedParticles_TravelMode` (`SpawnSphereRadius` 100 000, `MinRadius` 1000) and `_Slow` (1000 / 50) of `MI_SpeedParticles_Near` |
| **Travel mode's post-process** | `M_TravelMode_PostProcess` (post-process domain) and `Assets/Effects/Materials/MI_PostProcess_LensFlare_TravelMode` of `M_PostProcess_LensFlare` |
| **Planet proximity** (the sphere drawn when a planet comes close in travel mode) | `M_TravelMode_PlanetProximityEffect` on `Assets/TravelMode/Effects/Meshes/SM_TravelMode_PlanetProximityEffectSphere` |
| **The collection** every travel-mode material reads | `Assets/TravelMode/Materials/MPC_TravelMode`: `PlayerInTravelMode` (1 while travelling), `BoostPercentage`, `PawnForwardVector`, `SunPositionAfterOriginShift`, `SpaceObjectScaleFactor` 5000, `PlanetScaleMaxDistance` 5 000 000 |
| **Jump gate tunnel** (the hyperspace jump between systems) | `Assets/Environment/Structures/Effects/Particles/NS_JumpGate_WarpTunnel` (Niagara; the tunnel is `Assets/Shared/Meshes/SM_Sphere_XAligned_001` with `M_JumpGate_WarpTunnel`, translucent grey transmittance, unlit, two-sided, depth test off, and `M_JumpGate_WarpTunnel_Aperture`); `NS_JumpGate_Overload` (the gate's `SM_JumpGate_Merged_001` and `SM_Plane_Offset_001` flashes) |
| **Cruise mode's friction sphere** (the shimmer when something slows the cruise) | `Assets/Vehicles/Effects/Materials/M_CruiseMode_Friction` (additive, unlit, two-sided) |
| **Jump drive charge** (the glow building at the nose) | `Assets/Vehicles/Effects/Materials/M_JumpDrive_Charge_Front` (translucent grey transmittance, unlit, two-sided) |
| **Teleport and portal** (the fast travel's glow and trail, the NPC jump, the travel portal) | `Assets/Vehicles/Effects/Particles/NS_FastTravel_Teleport` (`M_FastTravel_Teleport_Glow` / `_Trail`), `P_NPCJump` (`M_NPCJump_Trail`), `Assets/Environment/Effects/Particles/NS_TravelPortal` (`M_TravelPortal_Base` / `_DarkSwirls`) |
| **HUD** | `Blueprints/UI/IngameMenu/WG_CruiseModeProgress`, `WG_JumpDrive`, `UI/Images/Elements/InfoBars/CruiseTravelRadial` |

The particle systems (`NS_*`, `P_*`) come out of FModel's Properties export of their folders; `tools/shaders`' `niagara.py`
disassembles a Niagara system's spawn and update scripts from that JSON when the emitters' numbers are needed.

## Camera shakes (`Blueprints/Effects/CameraShakes`, legacy oscillation patterns)

| Shake | Duration (blend in / out) | Rotation (amplitude / frequency) | Location (amplitude / frequency) |
|---|---|---|---|
| `BP_CamShake_CruiseMode_Start` | 0.4 s (0 / 0.4) | pitch, yaw, roll 1 / 25 | x, y, z 2 / 25 |
| `BP_CamShake_CruiseMode_Rumble` | 1 s (0 / 1) | pitch, yaw 1 / 80, roll 2 / 20 | x, y, z 0 / 20 |
| `BP_CamShake_TravelMode_Warp` | 1 s (0 / 0) | roll 0 / 100 | x 200 / 1.27, y 100 / 0.87, z 50 / 1.98 (offset zero) |
| `BP_CamShake_JumpDrive_Charge_Rumble` | 1 s (0 / 1) | pitch, yaw 1 / 80, roll 2 / 20 | x, y, z 0 / 20 |
| `BP_CamShake_JumpGateOpen` | 3 s (2 / 1) | pitch, yaw, roll 0.5 / 80 | x, y, z 5 / 80 |

Force feedback beside them: `Blueprints/Effects/ForceFeedbacks/FF_CruiseInit`, `FF_JumpDrive_Charge`.

## Sounds (`Audio/SFX`, with FModel's "Convert audio on bulk export")

- `Ship/Cruise_Mode`: `S_Cruise_Mode_Charging_004`, `_005` (the cruise charge).
- `HUD/TransitionToHyperspace`: `S_Transition_To_Hyperspeed_Init_001` (the start), `S_Hyperspeed_001`, `S_Hyperspeed_Loop_002`
  (the loop; the sound cues `S_SC_Hyperspeed_Loop`, `S_SC_Hyperspeed_Add_Loop`).
- `Environment/JumpGate`: `S_Jumpgate_Activation_001`, `_InnerRing_001`, `_Loop_001` / `_002`, `S_Jumpgate_Active_Loop_001`,
  `S_Jumpgate_InnerRing_Loop_001`, `S_Jumpgate_Deactivation_001`, `S_Jumpgate_004`.

## What a plain folder export lacks

Walking the exported JSON from the effects above to everything they reference (121 objects) against an export of their
folders alone: five shared textures (`Assets/Shared/Textures/Effects/T_Gaussian_N`, `T_Noise_004_M`, `T_Noise_019_M`,
`T_Pattern_MotionBlurSparks_001`, `T_Singularity_001_N`) and three meshes (`SM_JumpGate_Merged_001`,
`SM_Plane_Offset_001`, `SM_Sphere_XAligned_001`) had no PNG / glb. `tools/warp_assets.txt` lists every mesh, texture and
material of that walk, so `export ... all` fills the gaps whatever folders were exported.

## The cruise mode itself (from the SDK dump, `ES2_classes.hpp`)

The ship's cruise is a charge (`CruiseModeChargeDelay`, `OnCruiseModeCharge(Progress)`, `GetCruiseModeChargeProgess`)
that an interruption ends (`InterruptCruiseMode`), with a friction sphere around obstacles (`CruiseModeFrictionSphere`) and
a camera field-of-view offset (`CameraCruiseModeFOVOffset`, `CameraCruiseModeFOVMax`): the remake's cruise drive follows
that shape (its `CruiseDrive` rules).
