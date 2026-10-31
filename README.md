# EVERSPACE 2 ships importer

Builds the **es2_ships** mod for the Galaxy on Fire 2 Unity Remake from **your own copy of EVERSPACE 2**: nine customizable
ships (Light: Vanguard, Scout, Stinger; Medium: Interceptor, Sentinel, Striker; Heavy: Bomber, Vindicator, Gunship) that you
put together in the hangar from EVERSPACE 2's ship modules, in its colour schemes, with its weapon and turret models; and
as much more of EVERSPACE 2 as you want: its weapons, devices and consumables, its fighters, warships and freighters in the
traffic, the Mobile Homebase, and its ten sectors as star systems. Build all of it, or only the parts you pick
(`--parts`, see "Building the mod").

This importer contains **nothing from EVERSPACE 2**: no models, textures or game data, only the scripts that convert the files
you export from your own installation. The mod it builds does contain EVERSPACE 2's models and textures (© ROCKFISH Games),
so it is for your own use: **don't share or upload the built mod**. Share this importer instead.

## What you need

The importer runs on **Windows, macOS and Linux**.

- A version of the **Galaxy on Fire 2 Unity Remake** with customizable ships (the hangar's *Customize ship* button).
- **EVERSPACE 2**, installed.
- **FModel** (fmodel.app), to export the game's files. FModel is a Windows program: on macOS or Linux run it on a Windows
  PC and copy its `Output` folder over, or run it through Wine / CrossOver (Linux: Proton or Wine works).
- **Python 3.9 or newer** with numpy and Pillow:
  - Windows: install Python from python.org (tick "Add python.exe to PATH"), then in a Command Prompt
    `py -m pip install numpy pillow`
  - macOS: install Python from python.org or Homebrew (`brew install python`), then in Terminal
    `python3 -m pip install numpy pillow`
  - Linux: your distribution's `python3`, `python3-numpy` and `python3-pil` (or `python3 -m pip install numpy pillow`)
- For the phone version only: **Blender 4.2 or newer** (blender.org). With Blender installed the ships also get their own
  shop icons and the mod's preview image shows them rendered (without it the ships show the Phantom's icon and the preview
  card their names). It is found by itself on the PATH, in Program Files (Windows; also Steam's copy) or in Applications
  (macOS); else give its path with `--blender`.
- For the sounds, nothing more when FModel converts them (see the Audio row below). A raw export (`.binka`, Unreal's Bink
  Audio) needs **vgmstream** to decode it: a `vgmstream-cli` on the PATH (macOS: `brew install vgmstream`; Linux: your
  distribution's or the AUR's package, or the Linux build from vgmstream's releases), one put next to `import.py`, or given
  with `--vgmstream`; on Windows FModel's own copy in its `Output/.data` folder is found by itself (elsewhere it is run
  through Wine as a last resort). **ffmpeg** on the PATH, or the `soundfile` Python package (`pip install soundfile`), makes
  converted `.wav` sounds Ogg Vorbis (smaller); without either they stay `.wav`.

## Exporting from FModel

1. In FModel's settings set the **model export format** to **glTF 2.0 (binary)** and the **texture export format** to
   **PNG**.
2. Load EVERSPACE 2's game folder in FModel. Two things FModel needs that this importer doesn't provide:
   - **The AES key.** EVERSPACE 2's archives (`.pak` / `.utoc`) are encrypted, and FModel only opens them with the game's
     AES decryption key. [UE AES Key Finder](https://www.nexusmods.com/motortownbehindthewheel/mods/131?tab=files&file_id=593)
     (Nexus Mods) can find it; enter it in FModel's AES settings.
   - **A mappings file (`.usmap`).** FModel needs the game's type mappings to read its packages.
     [Dumper-7](https://github.com/Encryqed/Dumper-7), injected into the running game, generates one; add it in FModel's
     settings (Local Mapping File). Injecting a DLL into the game is at your own risk.
3. In the archive tree, right-click each folder below and run the export actions listed (FModel's wording varies a little
   between versions: the "Save Folder's Packages ..." entries):

   | Folder | Export |
   |---|---|
   | `ES2/Content/Blueprints/DataTables` | Properties (.json) |
   | `ES2/Content/Assets/Vehicles/ShipModules` | Properties (.json), Models, Textures |
   | `ES2/Content/Assets/Equipment/Weapons` | Properties (.json), Models, Textures (optional: the weapon models) |
   | `ES2/Content/Assets/Turrets/Meshes` | Models (optional: only `SK_Turret_PlayerShip_001` is used, the player turret) |
   | `ES2/Content/Assets/Shared/Textures/Effects` | Textures (optional: only `T_Noise_018_M` is used, the engine flames' noise) |
   | `ES2/Content/Blueprints/Pawns`, `ES2/Content/Blueprints/Equipment`, `ES2/Content/Blueprints/Missions` | Properties (.json) (optional: the warships' layouts, the weapons' stats and fire sounds, the Dreadnought) |
   | `ES2/Content/Assets/Vehicles/Warships`, `ES2/Content/Assets/Vehicles/Transporters` | Properties (.json), Models (optional: the warships, freighters and the Dreadnought) |
   | `ES2/Content/Assets/Vehicles/Fighters`, `ES2/Content/Assets/Vehicles/Drones` | Properties (.json), Models (optional: EVERSPACE 2's enemy fighters and drones as traffic) |
   | `ES2/Content/Assets/Vehicles/Traffic`, `ES2/Content/Assets/Vehicles/Miningships` | Properties (.json), Models (optional: EVERSPACE 2's civilian traffic and mining ships as freighters) |
   | `ES2/Content/Dev/Alex/Environments/Structures/Textures` | Textures (optional: only `T_Structures_FX_Lights_001` is used, the light cards of the traffic, some fighters and drones; without it they are left out) |
   | `ES2/Content/Assets/Turrets/Meshes` | Models (all of them: the warships' turrets) |
   | `ES2/Content/Assets/Vehicles/Shared`, `ES2/Content/Assets/Environment/Structures`, `ES2/Content/Assets/Effects/Materials`, `ES2/Content/Assets/Blockouts/Materials` | Properties (.json), Textures (the warships' materials) |
   | `ES2/Content/Maps/TravelMode` | Properties (.json) (optional: EVERSPACE 2's sectors as systems; then also run `tools/shaders`' `export` on `tools/sector_assets.txt`, the sky's and planets' textures FModel's export lacks) |
   | `ES2/Content/Maps/Locations` | Properties (.json) (optional: the sectors' stations as ES2 builds them, with their docked views as hangars; then also run `tools/shaders`' `export` on `tools/station_assets.txt` with `all`, the structure pieces FModel's export lacks) |
   | `ES2/Content/Audio/MusikSets`, `ES2/Content/Audio/Music` | Properties (.json) and Audio (optional: the sector's music) |
   | `ES2/Content/Maps/POIs/POI_HomebaseCarrier_001` | Properties (.json) (optional: the Mobile Homebase as ES2's carrier with its hall, docked inside; then also run `tools/shaders`' `export` on `tools/homebase_assets.txt` with `all`, for the props and the hall's materials FModel's export lacks) |
   | `ES2/Content/Assets/TravelMode`, `ES2/Content/Assets/Environment/Structures/Effects`, `ES2/Content/Assets/Vehicles/Effects`, `ES2/Content/Assets/Environment/Effects`, `ES2/Content/Assets/Effects/Materials`, `ES2/Content/Blueprints/Effects/CameraShakes` | Properties (.json), Textures, Models (optional: EVERSPACE 2's warp effects for the remake's warp flight, `research/warp_effects.md`: the travel mode's warp tunnel, speed particles and post-process, the jump gate's tunnel, the cruise mode's friction sphere, the jump drive's charge, the teleport and portal effects, with their camera shakes; then also run `tools/shaders`' `export` on `tools/warp_assets.txt` with `all`, the tunnel meshes, the shared noise textures and the resolved materials FModel's folder export lacks) |
   | `ES2/Content/Audio` | Properties (.json) and Audio (optional: the engine, boost and weapon sounds, and for the warp effects `SFX/Ship/Cruise_Mode`, `SFX/HUD/TransitionToHyperspace` and `SFX/Environment/JumpGate`). Turn on Settings > **Convert audio on bulk export** first: the sounds then come out playable (`.ogg` / `.wav`) and the importer needs no other tool |
   | `ES2/Content/Assets/Vehicles/Shared/Textures` | Textures (optional: `T_Vehicles_Floaters_Emissive_M`, the glow pattern of the engine nozzles, `T_ShipModules_FX_001_M_A`, the pattern of the wings' hologram discs, the damage maps and `T_Vehicles_Okkar_Techdetail_001_*`, the Wraith's plating) |
   | `ES2/Content/UI/Images/Items` | Textures (optional: EVERSPACE 2's item icons, from which the weapons', devices' and consumables' shop icons are made in Galaxy on Fire 2's style) |
   | `ES2/Content/DataFiles` | ES2's tables, which FModel doesn't export (optional: `factions.csv` and `faction_relations.csv`, who fights whom; `dockables.csv`, the sectors' stations and their factions). Extract them with `tools/shaders`' `pak` mode: `... dotnet run -c Release -- pak pakchunk0-Windows.pak "DataFiles/.*\.csv" <FModel's Output/Exports folder>`. Without them the factions are made without ES2's relations |

   The **Wraith** (the Okkar ship of the Wrath of the Ancients DLC) comes along when `ShipModules/Okkar` was exported with
   the rest (its hull `SK_ShipOkkar_C_001` and cockpit) and its plating textures above: one hull of its own (kit "okkar"),
   with the other ships' colours, weapons and flames.

   FModel writes them to its `Output/Exports/ES2/Content` folder, keeping the game's folder layout (each model's `.glb` next
   to its `.json`).

Without `Audio` the ships play the game's own engine, boost and weapon sounds. Exported without the conversion (`.binka`
files) the importer decodes them with vgmstream (see "What you need") or, without it, says so and builds the mod without
sounds; export `Audio` again with the setting on.

With the warship folders the mod also brings EVERSPACE 2's warships and freighters into the game's traffic (Colonial,
Okkar, G&B, Outlaw, cultist and swarmer capital ships with turrets you can shoot off them, launch decks of ES2 fighters, the
Okkar frigate's weak spots; pirate and Void warships hostile; the Mobile Homebase a station that roams ES2's sectors: you fly
into its hall and land on its pad, as in ES2), EVERSPACE 2's weapons in the shops (every primary and
secondary, the Okkar and legendary variants, with their own colours, sounds and models), and the Outlaw
Dreadnought raiding convoys now and then (Options > Gameplay "Dreadnought raids"). Without them the mod is just the ships.

With `Fighters` and `Drones` it also brings 77 of EVERSPACE 2's enemy fighters and drones (`tools/fighters.py`, from their
blueprints: the Outlaws' raiders, scouts, bombers and drones as pirates, the Okkar as Vossk, the Okkar Prime, the Redeemers
and the Ancients' swarmers as the Void, Grady & Brunt as Midorians, the Coalition as Terrans, the Freelancers as Nivelians;
and the DLCs' and later updates': Zurilia's and the Retaliators' fighters, the Colonial clone hunters, the rogue AI drones,
the Okkar Prime splitters and skirmishers, the Outlaw and Okkar utility drones and their bosses; with the warships the
Zurilia destroyer, the Retaliators' drone carrier and the Okkar Prime and clerical corvettes),
each with its own name on the lock plate, ES2's exhaust flames and engine trails. They fly as their race's traffic (Options
> Gameplay "Mod ships in traffic"), the warships' hangars launch them, and the Okkar Prime Claw is a pirate boss's hull. They
are never sold.

With `Traffic` and `Miningships`, 22 of EVERSPACE 2's civilian ships join the freighters: the haulers, tugs, tankers and
settler ships of its space lanes (Terran, Nivelian and Midorian), the Okkar's transports, liners and their engineer (Vossk),
and Grady & Brunt's mining ship and kilometre-long Viridium mining barge (Midorian). Their running lights are ES2's own
light cards, drawn additively in each light's colour.

Always: EVERSPACE 2's devices and consumables in the shops (`tools/devices.py`), each on the Galaxy on Fire 2 equipment or
secondary that does most nearly what it does in EVERSPACE 2 (the Scout's Shadow Strike and Vanish as cloaks, Spectral Form
as a phase cloak, Static Overload and the repulsors as shock blasts, ARC-9000 as a nuke, the EMP Generator and the
Peacemaker as EMP bombs, the Missile Defense System letting your auto turrets shoot down incoming missiles (the remake's
`missileDefense`), the Phalanx, the Turret and the Combat Drone as sentry guns, Void Swarm, Siphon Pulse and the Nano
Transmitter as transfusion beams, nanobots as repair bots, Entropy Anchor and the Energy Shield as emergency systems, Time
Extender, Energized Boost, Weapon Overdrive and the rest). Those with no GoF2 mechanic to stand on (teleports, grappling
hooks, damage over time, ...) are left out. With the item icons exported, every weapon, device and
consumable gets a shop icon made from EVERSPACE 2's own (`tools/icons.py`): cut out, laid like GoF2's guns, given GoF2's
gloss and a shadow on the plate of its type (red primaries, orange secondaries, green equipment); the white device symbols
become embossed steel emblems glowing in the plate's colour, and weapons sharing an icon get it in their own colour.
(FModel's bulk export may leave `UI/Images/Items` as .json only; `tools/shaders`' `export` on `tools/item_icons.txt`
fetches the images.)

With the travel maps and the sky and planet textures, the mod brings **EVERSPACE 2's galaxy** (`tools/sectors.py`): its ten
sectors (Ceto, Union, Zharkov, the Khaït Nebula, the Khaït Dominion, Drake, Khione, Aethon, Ushak and Rhak) as systems past
the edge of Galaxy on Fire 2's star map, laid out as ES2 lays out its galaxy. It is a galaxy of its own: no jumpgate links it
to Galaxy on Fire 2's systems, so a Khador Drive takes you there; inside it the sectors are linked as ES2 links them, its
jumpgates and its wormholes both as Galaxy on Fire 2 jumpgates (Ceto - Union - Zharkov / Drake / Aethon, Zharkov - the Khaït
Nebula / Ushak, the Khaït Nebula - the Khaït Dominion - Rhak - Ushak; Khione, which ES2 reaches by its story alone, only by
the Khador Drive). A system holds 7 places: Ceto's are picked by hand (Union Bridge, Alcyone Station, Nephtys Plains, Ceto
Orbit, Fort Cetus seen but not docked at, the G&B Mining Grounds and Ceto Outer Rim); the other sectors' come from ES2's own
data: the location with the sector's jumpgate, the places with stations that trade (`DataFiles/dockables.csv`: who runs
them, which sets the station's look and hangar, and the sector's owner, the faction running the most of them), then mining
places, hostile holds (seen, not docked at) and other landmarks; their tech levels and ores follow the places' ES2 levels.
Who raids each sector is a pick from ES2's story (ES2 spawns its enemies per encounter). Each place's sun and planet lie
where they do from it in ES2, and each sector sits on the star map where it does on ES2's. The skies are composed from ES2's
star and nebula textures in each sector's own nebula colours; the planets are drawn from ES2's planet textures in their own
colours (gas giants, earthlike and water worlds, deserts, ice, volcanic and Okkar city worlds; ES2 draws both with its
materials at runtime, so these are compositions, not copies). Each sector's music is its own (ES2's music sets). EVERSPACE
2's resources (Copper, Insidium, Baromite, Clygon, Glacit, Coruscate, Aetheum, Culver, Mallemite, Phazium) are new
commodities, mined from the sectors' asteroids and traded like ores; Iron and Titanium are the game's own. With the
locations' levels the stations are **ES2's own** (`tools/stations.py`): each place's station is the cluster of structure
pieces round its docks in ES2's level (each different piece once in `stations/<id>.glb`, placed as ES2 places it, with the
level's own material choices), and you dock as in ES2: the dock's marker shows in space, the Dock button inside ES2's dock
box lands the ship on ES2's pad under the dock's camera (its 1400 mm lens on its spring arm, its docking timeline, sway and
sounds), and the station's menu opens over the orbit; Launch takes off from the pad along ES2's path. Other pads close by
hold parked ships. ES2's stations have no Space Lounge. A place without a dock in its level keeps a Galaxy on Fire 2
station of its faction's look.

ES2's ships fly for **ES2's own factions** (`tools/factions.py`), not Galaxy on Fire 2's races: Grady & Brunt, the
Freelancers, the Coalition, the Okkar, Mr. Kato's Cartel, and the always-hostile Okkar Prime, Outlaws, Redeemers and
Ancients, each with ES2's relations to the others (from `DataFiles/faction_relations.csv`) and the player's starting
standing, an emblem from ES2's decal logos, and a reputation bar on the Status window (not the hostile ones). The sectors
belong to them and fly ES2's ships only: Ceto and Zharkov Grady & Brunt's, Union and the far sectors the Freelancers', Drake
the Coalition's, the Khaït and Okkar sectors the Okkar's, each with its local patrols, raiders and ES2's freighters. Their lounges hold
diplomats who make peace with a faction you are at war with.

**Everything the Supporter Pack adds** to the customization (and EVERSPACE 2's other skins): the **Kickstarter** and
**Alienware** skins (each a colour scheme and a livery), EVERSPACE 2's 35 **liveries** (`DT_ShipProjectionDecals`, patterns
projected onto the hull, with their own colour row), its 35 **decals** (`DT_ShipDecals`, the Supporter Pack's 13 among them:
insignia and lettering on each part's decal faces, with their colour rows), and the 13 **engine trails** (`tools/trails.py`,
`DT_ShipExhaustParticles`: Default, Stardust, Rings of Nerea, Ion Veils, Delta Surge, Tetragons, Thermal Blaze, Firestarter,
Voltaic Tendrils, Residuum, Raw Combustion, Coolant Leak, Void Reverb; the game rebuilds EVERSPACE 2's particle systems and
materials, research/engine_trails.md; these need `Assets/Vehicles/Effects/Particles` (Properties), `Assets/Shared/Textures/Effects`
(Textures: `T_Pattern_Barcode_001`, `T_Noise_012_M`, `T_Noise_020_M`, `T_SmokePuff_002_M`, `T_SmokeSeamless_001_H`,
`T_Sphere_001_N`) and `Assets/Shared/Meshes` (Models: `SM_CrossShape_Circle`, `_Square`, `_Triangle`) exported). The
Supporter Pack's colour for the Cybernetic glow (Emissive 3) and its intensity were already there. EVERSPACE 2 only shows
these to Supporter Pack owners; the mod shows them to everyone who built it from their own copy.

Without the weapons and the turret the ships still work: the guns fire from the ships' own weapon sockets, just without
weapon models on them. Without the noise texture the engine flames are smooth instead of streaked, and without the nozzle
mask the nozzles glow all over instead of in their rings and grilles.

## Building the mod

Open a terminal in this folder (Windows: in Explorer type `cmd` in this folder's address bar; macOS: Finder's
*Services > New Terminal at Folder*, or `cd` to it) and give it FModel's `Output/Exports` folder (dragging the folder onto
the terminal window types its path):

- Windows: `py import.py "C:\Tools\FModel\Output\Exports"`
- macOS / Linux: `python3 import.py ~/FModel/Output/Exports`

It checks the export first and lists anything missing, then writes the mod to `es2_ships` next to this script. Options:

- `--parts <list>`: what the mod holds. `all` (the default) builds everything; or pick, comma-separated:

  | Part | What it adds |
  |---|---|
  | `ships` | the nine customizable player ships and the Okkar Wraith (parts, colours, liveries, decals, engine trails, weapon and turret models, exhaust styles); brings `sounds` |
  | `weapons` | EVERSPACE 2's weapons as shop items |
  | `devices` | EVERSPACE 2's devices and consumables in the shops |
  | `fighters` | the enemy fighters and drones, flying for their factions |
  | `warships` | the warships and freighters in the orbits' traffic, and the Dreadnought's raids; brings `ships`, `weapons` and `fighters` (their hangars launch them, their turrets fire the weapons) |
  | `homebase` | the Mobile Homebase, a station you dock in that roams the sectors (or every system without them) |
  | `sectors` | the ten sectors as star systems with their stations, hangars and resources to mine; brings `fighters` (their traffic) |
  | `sounds` | the ships' engine, boost and weapon sounds |

  Shortcuts: `systems` = sectors, `items` = weapons + devices, `traffic` = fighters + warships, `world` = sectors + homebase.
  Examples: `--parts ships` (the ships only), `--parts systems`, `--parts ships,items`. `--list-parts` prints the list.
  A part the export has no files for is left out with a note, and the summary at the end says what the mod holds. The
  mod's id is `es2_ships` whatever it holds, so a later build with more parts replaces it.
- `--config <file>`: a settings file. Without it, `config.json` next to `import.py` is read when there is one: copy
  `config.example.json` to `config.json` and set your export folder, parts and other options there once; then
  `python3 import.py` alone builds with them. Keys are the options' names without the dashes (`"parts": ["ships",
  "sectors"]`, `"no-sounds": true`); an option given on the command line wins.

- `--no-preview`: skip rendering the mod's preview image (the Mods screen's card, 1280 x 720). By default, when Blender
  is found, it shows the Dreadnought with warships, freighters and the Mobile Homebase behind it, four player ships in
  front and a strip of item icons, over the remake's red nebula when `--remake` is given (`tools/preview_card.py`; the
  ships rendered by `tools/preview_blender.py` and `tools/preview_model_blender.py`, a few minutes); without Blender the
  card shows the ships' names only.
- `--no-icons`: skip the ships' shop icons. By default, when Blender is found, each ship's default build is rendered like
  the game's own ship icons (from its left, above and a little ahead, the nose dipping to the bottom left) and put on a
  ship frame (`icons/<ship>.png`, 180 x 88).
- `--remake <folder>`: a checkout of the remake's source (or its `Assets/Textures/textures/gof2_interface2_ipad_large.png`):
  the ships' and items' icons then use the game's own plates; without it they get drawn look-alikes.
- `--item-icons <folder>`: EVERSPACE 2's item icons as PNG from somewhere else than the export's `UI/Images/Items`.
- `--out <folder>`: write it somewhere else, for example straight into the game's Mods folder (`.../Mods/es2_ships`). An
  earlier build there is replaced; any other folder is never touched.
- `--zip`: also make `es2_ships.zip`.
- `--mobile`: also make a **phone version**, `es2_ships_phone.zip`: Blender reduces every model to a quarter of its
  triangles and the textures are halved (about 50 MB instead of 100 MB, and much lighter to draw). It has the same mod id, so
  saves move between your devices, and it joins multiplayer sessions with the PC version (see the notes below).
- `--ratio 0.4`: the share of triangles the phone version keeps (default 0.25).
- `--blender <path>`: Blender's executable (or `Blender.app` on a Mac), if it isn't found by itself.
- `--vgmstream <path>`: the `vgmstream-cli` that decodes raw `.binka` sounds, if it isn't found by itself.
- `--no-sounds`: build without EVERSPACE 2's sounds (the same as leaving `sounds` out of the parts).
- `--jobs 4`: how many things the build does at once (default: half your processor's cores, fewer when memory is short).
  The build also runs at a lower priority, so the computer stays usable meanwhile.

## Rebuilds and build records

The importer keeps verified snapshots in `<out>_work` by default. `--work <folder>` chooses another cache location;
`--fresh` rebuilds the stages in an existing importer-owned cache. These options also work in config.json. Keep the
work folder separate from your export, item-icon/remake inputs, and output folders. A nonempty unrelated work folder
is rejected, and only one importer can use a work folder at a time.

Each run hashes the export and external inputs with SHA-256, including file names and directory additions/removals.
A same-size edit is detected. Stage fingerprints also include converter/helper code, runtime/package versions, relevant
options and external tool identities. The stages are content conversion, ship icons, preview, mobile conversion, and
zip packaging. Content conversion remains one stage because its kits, weapons and world tables share data; changing a
material converter rebuilds that stage, while changing only the mobile ratio or decimator preserves the desktop stages.

Unchanged stages are restored from snapshots after their cached files are checked. Snapshots are separate copies, so
editing a built mod cannot change its cached inputs. The first build populates the cache. Hashing large exports still
requires reading their files on every run, and keeping desktop and mobile snapshots requires additional disk space.
Incomplete requested content and reported render failures are retried; skipped/missing-content diagnostics are saved.

Successful builds write `<out>.build-manifest.json` beside the desktop mod, a second copy in the work folder, and
`<out>_phone.build-manifest.json` when making a phone build. They record importer revision and source-code hashes, input
hashes, runtime/tool identities, resolved options, stage fingerprints and cache reuse, missing parts and diagnostics.
These records stay outside mod folders and zip archives to preserve the game's save and multiplayer hashes.
Zip entries use stable ordering and timestamps so equivalent files produce equivalent archives.

Run the cache tests without game files or Blender:

```
python3 -m unittest discover -s tests -v
```

The tests use deterministic conversion fixtures and cover clean/resumed output equivalence, same-size source edits,
selective invalidation, failed-stage retries, snapshot integrity, phone options, and repeatable packaging. They do not
verify the visual correctness of ship conversion or Blender renders.

## Performance without changing asset quality

A stage whose recipe changed discards its old snapshot without hashing that obsolete payload first. A matching recipe
still verifies every cached output byte. Desktop zip and mobile stages share one inventory of their unchanged desktop
input. Material parent JSON is parsed through a bounded 256-entry cache; configuring a source clears parsed and resolved
material caches so changing exports cannot reuse old material values. Shader math, texture sizes, filtering, mesh
precision and output quality are unchanged.

## Installing

- **PC**: copy the `es2_ships` folder (or `es2_ships.zip`) into the game's Mods folder (the main menu's Mods screen has
  *Open mods folder*) and turn it on there. Don't put this importer folder itself in the Mods folder.
- **Phone**: copy `es2_ships_phone.zip` to the phone, then in the game *Mods > Import mod* and pick it.

## In the game

- The `drives` part brings two cruise drives. The **Khador Slipstream** is sold in shops (tech level 7): hold the
  fast-forward button to cruise an orbit at x4 for energy cells. Its successor, the **Slipstream II**, is made from a
  blueprint and sold nowhere: find it in a wreck to hack at the GB Mining Grounds, or buy it from a bar visitor now and then
  (400,000), from story step 34 on or at once in free play. The recipe takes a Khador Slipstream, EVERSPACE 2's Glacit,
  Coruscate, Baromite, Clygon, Phazium and Mallemite and the Khador Drive's goods, and can't be autocompleted. Mounted, its
  quick menu entry leaves the system for the space between the stars, where the systems on your star map can be flown to
  through EVERSPACE 2's warp tunnel, about an energy cell per gate hop.
- The ships are sold by dealers at stations of tech level 5 and above (any race), now and then.
- NPC pilots of every race (Terran, Vossk, Nivelian, Midorian, pirates, the Void) fly them too, each in a random build
  (parts, tier, colour scheme, sometimes a skin), with the game's Gameplay option "Mod ships in traffic" (default 25 %).
- In the hangar, **Customize ship** (under Inspect ship) swaps the parts (body, rear, cockpit, wings), the wing extension
  tier and the colours, like EVERSPACE 2's ship modules. The parts change the ship's hull, cargo, handling and weapon slots.
- Weapons show EVERSPACE 2's weapon models on the ships' sockets, missile launchers its missile pod, and turrets its player
  turret.
- With the sounds exported: each ship type's engine as EVERSPACE 2 gives it (rising with the speed), EVERSPACE 2's boost
  (its ignition, the loop building up, its end) and the booster's recharge whine climbing as it refills; the weapons sound
  like the EVERSPACE 2 weapon they show (pulse laser, blaster, coil gun, railgun, flak, scatter gun, gauss cannon, thermo
  gun, the beam laser's ignition and hum; the pod's rocket, missile and mine launches). The volumes are set to the game's
  mix. NPCs flying the ships and other players hear the engines and shots too.
- The engines burn with EVERSPACE 2's flames and nozzle glow: the main flames with the thrust, the blue boost jets while
  boosting, the nozzles dim at idle and dark while parked in a hangar. Like in EVERSPACE 2, the Main thrusters, Booster and
  Side thrusters colours are set apart (the schemes bring EVERSPACE 2's own); the boost vents glow only while boosting,
  in the Booster colour. The lights take Emissive 1 (Lights) and 2 (Accent lights) as in EVERSPACE 2, and the Cybernetic
  glow (Emissive 3, with its intensity row) lights the thin strips along the panels.
- Each body carries its canopy and cockpit at its own socket, as in EVERSPACE 2, the wings' hologram projectors turn, the nozzle glow shimmers, and a damaged hull chars and then glows with embers.
- The small manoeuvring jets fire when you strafe, rise, sink or reverse, from each part's own thruster sockets.
- The Customize screen's Livery, Decal, Engine trail and Booster trail rows pick EVERSPACE 2's liveries, decals and trails
  (the trails run on the turntable while the engines run there, the booster trail while its row is selected); only your own
  ship shows its trails, as in EVERSPACE 2.
- Every other ship can burn EVERSPACE 2 thrusters too: the mod brings three exhaust styles (`exhausts.json`), the flames of
  three one-nozzle rear parts cut out on their own (`exhausts/`: EVERSPACE 2 thruster, heavy thruster and ring thruster).
  In the hangar's **Customize ship**, any ship (the game's own as well) gets an Exhaust row and its Main thrusters and
  Booster colours, from EVERSPACE 2's exhaust colours, and an Exhaust size row to fit them; the flames sit on that ship's own
  exhausts. Those ships have no boost jets, so there a boost turns the main flames to the Booster colour instead (the EVERSPACE
  2 ships keep their boost jets). Other mods'
  exhaust styles (the Galaxy on Fire 3 drives) can go on these ships the same way.
- In multiplayer the other players see your build too. Everyone in a modded session needs the same mod: each player builds
  their own from their own copy, and builds made with the same importer from the same EVERSPACE 2 version match. The phone
  version plays with the PC version: the mod's `mod.json` lists its models, textures, icons and preview under
  `multiplayerIgnore`, which the game leaves out of the session's check, so only the data (the ships, kits, colours and
  weapon models) has to match, and both versions share it. Each game shows the ships with its own models, so a phone player
  sees the lighter ones. Phone and PC need a game version with this check (the same version on every device, as always in
  multiplayer).

## License

The importer's scripts are under the MIT license (LICENSE). It covers this code only: the mod it builds holds the
game's own models, textures and data, which stay their owners' and are for your own use.
