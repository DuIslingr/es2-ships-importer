# NPC AI: EVERSPACE 2 against Galaxy on Fire 2

Compiled 2026-11-06. It compares what each game's fighter AI does, with constants, and what the remake already has.

## Sources

**ES2** (UE 5.6, `ES2-Win64-Shipping.exe` with its PDB names):
- 77 AI assets dumped with `SD blueprint` into `es2_re/ai/*.json`, and printed as outlines by a small tree printer:
  - behaviour trees `BT_*`, blackboards `BB_*`, Blueprint services and decorators
  - `DT_AimingNoiseTable`
- The native tasks, decompiled with Ghidra in `es2_re/ghidra/ai.c` and `ai2.c`:
  - `UBTT_Attack`, `UBTT_FlyToAvoidCollision`, `UBTT_OrbitAttack`, `UBTT_FlyAwayFrom`, `UBTT_BarrelRollEvasiveMove`, `UBTT_FollowLeader`
  - `UBTS_DetectNearestEnemyNative`, `UBTS_CheckIfUnderAttack`
  - `FBehaviourTreeTaskLib::Attack`, `FireWeaponIfInRangeAndInFOV`, `GetAimingNoise`, `CalcLeadingReticuleWithAimingInertia`, `CalcAiRotationInput`, `CalcAiLinearInputStrength`
  - `AESPawn::RegisterAttackingAi`, and the constructors
- Pawn defaults from `??0AESPawn` (`es2_re/ghidra/espawn.c`); field offsets from the Dumper-7 SDK.
- Constants the decompile left as `_UNK_` were read from the exe.
- Values that live only in `BP_GameInstance` were not read: the per-difficulty maps and the AI director's four parameter sets.

**GoF2:**
- `PlayerFighter::update` and `PlayerFighter::roll` from the iOS GoF2 HD 1.1.19 binary (`gof2_re/gof2hd`, arm64, with symbols), decompiled through REA's Ghidra provider.
- They agree with the remake's port, `NpcShip` ("Fighters" in its header) and `docs/notes/npcs-and-combat.md` "AI".

**Units:**
- ES2 positions are in cm; its task fields (radii, offsets, zig-zag lengths) are in metres.
- GoF2 positions are in game units. The remake's Unity scale is 0.05 m per unit.
- The ES2 importer scales ES2 metres for ships and ranges by 3.6.

## Architecture

| | GoF2 (`PlayerFighter::update`) | ES2 |
| --- | --- | --- |
| Structure | One update function per fighter, about 12 KB of code with flags | A UE behaviour tree per pawn type: selectors, sequences, decorators and services over a blackboard (Target, Leader, HealthIsCritical, IsTailed, InvestigationLocation, DockingGizmo, NextIdleLocation, UnderAttack...); native C++ tasks do the flying |
| Modes | Patrol the route, attack, circle away inside 8000 units, boost | Idle (investigate, follow the leader, dock, waypoints, wander, jump out) / flee / attack (fly-at, orbit, gain distance, tailed evasion, barrel roll) / formation attack |
| Per-type behaviour | The same for all fighters; freighters fly straight; turrets are separate | 40+ trees: `BT_Default` (outlaw fighters), `BT_Drone` (orbit drones), `BT_Gunship`, `BT_Freighter`, `BT_Destroyer`, `BT_FormationAttack`, sniper / fast / shielded / detonator / loot drones, `BT_OutlawViper` (special-attack phases), turrets, Chromagore, Okkar |
| Movement model | Kinematic: speed 2 units/ms (boost 5.5); the heading is blended toward the target, `fwd += normalize(dir - fwd) · dt · 48/65536`, snapped within an L1 distance of 0.0625; no inertia | Physics: the AI writes 0..1 yaw, pitch, roll and thrust inputs into `UShipMovementComponent`, which applies acceleration and damping |

## Target selection

**GoF2:**
- Its enemy list holds the player first, then the ships of hostile races.
- It attacks the first enemy inside a ±50 000-unit box.
- Every 5 s it re-rolls: 30 % pick a random enemy from the list (5 tries), else back to index 0, which is usually the player.
- Same-race ships never target each other.
- There is no attacker cap: a raider group all goes for the player. The remake's "Smarter NPC targeting" option adds a cap: nearest target, the player counted at ×0.7 distance, at most 2 + difficulty attackers per target.

**ES2** (`BTS_DetectNearestEnemyNative`, every 2 ± 0.5 s):
- It looks for the nearest enemy within `PawnSensingRadiusMeters`, 2000 m by default.
- The current target can be favoured (`PreferOldTarget`, scored 0.01 m), and so can the player (`PreferPlayerAsTarget`, scored 0).
- Filters:
  - targets more than 2 levels inferior and beyond 0.25 × the radius are skipped;
  - a target out of line of sight is remembered for `NoLOSMemoryThreshold`, 40 s;
  - optional weapon- and turret-cone filters and damaged-hull filters.
- Followers can use the leader's sensing sphere or the leader's target.
- `RegisterAttackingAi` records attackers of the player in `AiPawnsAttackingMe`, and the Wanted level reads that list.
- **ES2 has no hard attacker cap either.** It limits crowds through the AI director (below).

## Aiming and firing

**GoF2:**
- It fires one gun when the target lies within ±0.0076 of the nose (ship-space unit vector x and y) and within ±35 000 units on every axis.
- It aims at the target's position: no lead and no noise.
- Inside the ±8000 box (±12 000 while the player is docked at an object) it steers along its own right vector. That breaks the line, so it never fires at close range.
- The remake adds "Aim spots": fighters aim at a point on the hull instead of the centre.

**ES2** (`FBehaviourTreeTaskLib::Attack`, every attack tick):

*Leads the target, with aiming inertia:*
- The aim point is the target's position plus its velocity × T, plus noise.
- The weapon's lead (`CalcLeadingReticuleInWorld`) is taken from it.
- The reticule slides linearly onto the new lead over T seconds; then T is rolled again.
- T = `AimingInertiaSeconds × DifficultyFactor × (accelF + countF + levelF − 2)`.

*`DT_AimingNoiseTable` rows* (chosen by the pawn's `AimingPrecision`):

| Row | Inertia vs player / vs AI | Deviation vs player / vs AI | Note |
| --- | --- | --- | --- |
| Projectile | 0.2 s / 0.6 s | 0.1° / 1.0° | |
| InstantHit | 0.5 s / 1.0 s | 0.3° / 1.5° | |
| Sniper | 0.3 s / 1.2 s | 0° | ignores difficulty |
| PerfectAiming | 0 | 0 | |

- The noise is 3D noise with amplitude `distance · tan(deviation)`, plus an offset in cm.

*Difficulty:*
- It scales the **inertia only**, against the player (`DifficultyAimingInertias[EDifficulty]`, values in the BP game instance).
- A higher-level NPC re-aims faster: × 0.75 per level above the player.
- A player ship with slow acceleration is aimed at more slowly and less precisely (`accelF`).

*Precision modifiers* (`AddPrecisionModifier`):

| Modifier | Effect |
| --- | --- |
| Perfect | all zero |
| Improved | × 0.7 |
| SlightlyImpaired | inertia × 1.5, deviation × 2 |
| HeavilyImpaired | inertia × 2.5, deviation × 4, offset 400 cm |
| TurretMalfunction | deviation 45° |

*Fire check* (`FireWeaponIfInRangeAndInFOV`):
- Primary and secondary weapons are checked separately.
- The reticule must be within the weapon's range and within its yaw and pitch cone.
- Line of sight is traced from the muzzle: every 5 s after a clear result, every 0.5 s after a blocked one.

*AI director: fire suppression and crowd scaling, against the player only:*
- With n NPCs attacking the player, each one holds fire while `noise + 0.5 ≤ pSuppress`, where `pSuppress = clamp(1 − unsuppressed(n)/n, 0, 0.9)`.
- On average only about `AverageSumUnsuppressedAttackersAtMax` of them shoot at once, in smooth bursts.
- Inertia and aim offset also grow with n.
- There are separate parameter sets for mouse, gamepad and Nightmare Rifts.

*Weapon cone and flight are separate:*
- ES2 ships fire whenever the reticule is inside the weapon cone, so they shoot while orbiting, while zig-zagging away, and during "turn and fight".
- GoF2 fires only while flying straight at the target.

## Manoeuvres

| | GoF2 | ES2 |
| --- | --- | --- |
| Attack run | Heads straight for the target; breaks off along its right vector inside 8000 | `BTT_Attack`: flies at a point beside the target, a random 35–85 m (BT_Default 45–85 m) perpendicular offset at a random angle, chosen once per run |
| Spacing / orbit | none | `BTT_OrbitAttack` (drones' main attack, gunships, destroyers): a point at radius R on a random cone around target→self (cap 135° for drones), on a cone in front of the target, or a continuous horizontal circle at ±45°; waits 3.5 s (drones) at each point; can hold fire until it arrives (`OnlyFireIfAtDestInOrbit`, fast drones) |
| Disengage | none | `BT_Default`, after a 6.5 s ± variance attack: "gain distance": 20 % orbit at 500 m, else zig-zag away (segments up to 350 m, 35°) unless tailed |
| Tailed | none | `BTS_DetectIfTailed` (every 2.5 ± 0.75 s): when the enemy sits behind it, 65 % zig-zag away (350–550 m segments, 35°); 30 % (Mk ≥ 1) a barrel roll (rotation × 3.5, strafe × 3.5, 1.5 s) then fly away; else "turn and fight" (BTT_Attack at radius 1 m) |
| Flee | none: GoF2 fighters fight to the death | `BT_FleeSubtree` while `HealthIsCritical`, from `FleeThreshHealthRatio` (default 0, set per pawn): zig-zag away to 1000 m (100 000 cm), then idle at a safe distance; it stops fleeing once the shield is back to `AbortFleeShieldRatio` (0.75) |
| Boost | 5 % per 5 s, or after losing 40 % of the hull, for 5–8 s | none in the AI; speed comes from the task's speed factors |
| Hold course | every 5 s, 20 % start or stop flying straight with no steering (flag +0x185) | Steering noise: up to 20° (Attack 45°) of 3D noise on the desired direction |
| Bank / roll | Visual only: bank up to about 33° from the averaged turn of the last 5 frames, level again after 750 ms | Real roll input; in a formation or near the destination it matches the target's orientation |
| Collision avoidance | Only inside the first landmark's and the first freighter's volumes (heading += away · speed · 0.03); it flies through asteroids and other ships | Every waypoint: candidate directions in cones (exterior 13: 0/30/60/90/135/180° at speeds 1 and 0.33; interior 22), each tested by integrating the ship's own movement forward and sweeping its collision shape; the first clear path wins; 5 random directions as a last resort |
| Formations | Wingmen only: 3 fixed slots around the player (±4000 right / −3000 back, +2000 up / −2000 back) | Leader/followers for any group: 8 slots a ring (a hashed table of 45° steps around the leader's forward), ring spacing = follower distance + 2 × the leader's radius + 1.5 × the follower's; `BTT_FormationAttack` attacks the leader's target in formation |
| Idle | Patrol route (loop) | Investigate noises, follow the leader, dock, waypoints, random points within IdleRadius (450 m), jump out after idle time |

## Steering detail (ES2)

- **Rotation input:** `CalcAiRotationInput` = sign(err) · clamp((|err| − ½ω²/α) / RotationEaseAngle, 0, 1). It starts coasting once inside the braking angle, so it doesn't overshoot.
- **Thrust:** clamped (distance − stopping distance) / `LinearEaseDistance`, with overshoot prevention. Both inputs are scaled by the task's `SpeedReductionFactor` and `AgilityReductionFactor`.
- **Base task defaults:**

| Field | Default |
| --- | --- |
| AcceptableRadius | 50 m |
| ForceUpdateTime | 2 s |
| TestDirectionCount | 3 |
| OversteerPrevention | 30° |
| RotationEase | 5° |
| LinearEase | 30 m |
| MovementPredictionTime | 4 s |
| Trace steps per second | 20 |

## What the remake already has from ES2 and GoF3

- **GoF3 dogfighting** (`Settings.NpcDogfight`, `Gof3Dogfight`):
  - approach / veer-off / chase / tease modes;
  - lead aiming with a miss that settles;
  - an evade roll on hits, gated by difficulty;
  - V formations.
- **ES2 drone roles** (`NpcRoles`): sniper, detonator, webber, shield charger, armour link, anti-missile, jump suppressor, loot drone.
- **Smarter NPC targeting:** an attacker cap per target, comparable in purpose to ES2's director.
- **Missile warning:** boosting or cloaking shakes off homing missiles.

## Ported (2026-11-06)

- **ES2 aiming** (Options > Gameplay "EVERSPACE 2 NPC aiming", `Settings.Es2Aiming`; `Flight.Es2Aim`, `Es2Director`):
  - lead with aiming inertia;
  - the Projectile and Sniper noise rows;
  - difficulty on the inertia: Easy 1.3, Normal 1, Hard 0.5, Extreme 0.25;
  - the director's crowd suppression.
- **ES2 dogfighting** ("NPC dogfighting" "ES2 for all", or a hull's `"ai": "es2"`; `Flight.Es2Dogfight`):
  - BT_Default's runs, gaining distance, tailed evasion and barrel roll (none on Easy);
  - BT_FleeSubtree at 20 % hull, once.
- The importer's ES2 fighters (not the drones) and traffic ships ask for `"ai": "es2"`.
- Details are in the remake's docs/notes/npcs-and-combat.md under "ES2 aiming" and "ES2 dogfighting".

## What could come over, and how it bears on GoF2's difficulty

**Easier for the player** (could go in ungated):
- **ES2's fire suppression** (the director) is a gentler alternative to the remake's attacker cap. Every attacker still pursues, but only about k shoot at once.
- **Fleeing at critical health:** GoF2 fighters never flee. Fleeing ships escape; with a jump-out they leave without dropping loot.

**Harder for the player** (gate by rank or system security, or leave as options):
- **Lead aiming with inertia:** GoF2 never leads. This is the biggest jump in difficulty; GoF3's dogfight option already leads.
- **Firing while orbiting or zig-zagging:** GoF2 only fires on the straight run.
- **Path-tested collision avoidance:** NPCs would stop flying into asteroids.

**Neutral / flavour:**
- the orbit attack for drones;
- "gain distance" and tailed evasion with zig-zags;
- the perpendicular attack-run offset;
- steering noise;
- leader/follower formations attacking the leader's target.

**Not portable as is:** ES2's physics steering. GoF2's NPCs are kinematic, and ES2's inputs and braking angles assume a rigid body with angular acceleration.

## Difficulty scaling

**ES2 sources:**
- The four maps are set in the `UESGameInstance` constructor (`es2_re/ghidra/ctors2.c`); `BP_GameInstance` doesn't override them.
- `FAiDirectorParameter` defaults come from its constructor (`es2_re/ghidra/aidir.c`); `BP_GameInstance` overrides three of the four sets.
- Rifts use Normal whatever the setting (`UHealthComponent::OnDifficultyChanged`).

**ES2 by difficulty:**

| EDifficulty | Aiming inertia × | Hit points factor ^ exponent = NPC hull / shield / armour × | Damage factor |
| --- | --- | --- | --- |
| VeryEasy | 1.5 | 0.3 ^ 1 = 0.3 | 0.3 |
| Easy | 1.3 | 0.7 ^ 1 = 0.7 | 0.7 |
| Normal | 1.0 | 1.0 | 1.0 |
| Hard | 0.5 | 1.5 ^ 1 = 1.5 | 1.5 |
| VeryHard | 0.25 | 2.0 ^ 1 = 2.0 | 2.0 |
| Nightmare | 0.25 | 2.5 ^ 1.35 = 3.45 | 2.5 |

- **Hit points** [code]: `OnDifficultyChanged` of the health, shield and armour components sets max = pow(factor, exponent) × the NPC levelling value.
- **Damage factor** [inferred from its name]: the code applying it wasn't found. It is presumably the NPCs' damage to the player.
- **Aiming inertia** applies against the player only:
  - It multiplies `DT_AimingNoiseTable`'s inertia. A projectile NPC re-aims every 0.3 s on VeryEasy and every 0.05 s on Nightmare: nearly perfect lead.
  - Deviation doesn't scale with difficulty.
- **Stealth detection** is × 0.5 on VeryEasy and × 0.75 on Easy.

**ES2 AI director** (`GetAIDirectorParameters`: the mouse or gamepad set, the Nightmare Rifts set inside those rifts):

| Parameter | Default (mouse) | Gamepad | Nightmare Rifts | Nightmare Rifts gamepad |
| --- | --- | --- | --- | --- |
| AttackerCountSuppress (attackers) | 3..12 | 3..10 | 3..12 | 3..10 |
| AverageSumUnsuppressedAttackersAtMax | 6 | 4 | 8 | 6 |
| SuppressShootPercent | 0.7 (use not traced) | | | |
| SuppressShootWavelength | 8 | | | |
| AttackerCountAimingInertia / InertiaFactorAtMaxCount | 3..12 / 1.0 (no effect) | | | |
| AttackerCountAimingOffset / AdditionalOffsetAtMaxCount | 3..12 / 0 (no effect) | | | |
| AimingInertia_PlayerAcceleration / InertiaFactorAtMin | 8000..16000 / 2.5 | | | |
| AimingOffset_PlayerAcceleration / AdditionalOffsetAtMin | 8000..16000 / 0 (no effect) | | | |

Read with the code:
- **Suppression:** up to 3 attackers all shoot. Beyond that, the number shooting at once climbs to 6 at 12 attackers (4 at 10 on a gamepad), in noise-driven bursts.
- **The other director terms:** with these defaults, only the player's acceleration changes aiming. A player ship with `AccelerationForward` ≤ 8000 is aimed at with 2.5 × the inertia, sliding to 1 × at 16 000. Neither difficulty nor attacker count changes these terms.

**GoF2** (`Session.Difficulty`, the remake's port; docs/notes/saves.md "Difficulty"):
- Four levels: Easy 0 / Normal 0.5 / Hard 1 / Extreme 1.5.
- `DifficultyFactor` × 0.5 / 1 / 1.5 / 2 applies to:
  - NPC hulls and gun damage
  - raider counts, pirate-base guards (2 / 5 / 7 / 10), Wanted and freelance enemy counts
- Other rules by level:
  - the cloak cooldown
  - Extreme-only rules
  - the remake's Smarter targeting cap of 2 + difficulty attackers
  - the GoF3 dogfight evade chance of 0 / 0.15 / 0.25 / 0.33
- The AI's aim and decisions don't change with difficulty; GoF2 never leads its shots.

**Side by side:**

| | Hull | Damage |
| --- | --- | --- |
| GoF2 (Easy..Extreme) | 0.5–2 × | 0.5–2 × |
| ES2 (VeryEasy..Nightmare) | 0.3–3.45 × | 0.3–2.5 × |

- ES2 also sharpens the aim with difficulty.
- An ES2 aim port fitting GoF2 could map the remake's four levels onto ES2's middle four inertia factors (1.3 / 1.0 / 0.5 / 0.25). It would be behind an option or a rank gate, since GoF2's NPCs don't lead at all now.
- Its suppression (at most about 6 shooters at once) is a player-friendly rule that could go in ungated.

## Not read

- `UBTS_CheckIfUnderAttack`'s defaults.
- Where `DifficultyDamageFactor` is applied, and the use of `SuppressShootPercent`.
- The idle-location shapes in detail.
- The barrel roll's exact strafe vector.
