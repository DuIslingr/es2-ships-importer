# EVERSPACE 2 ships importer

Builds the **es2_ships** mod for the Galaxy on Fire 2 Unity Remake from **your own copy of EVERSPACE 2**: nine customizable
ships (Light: Vanguard, Scout, Stinger; Medium: Interceptor, Sentinel, Striker; Heavy: Bomber, Vindicator, Gunship) that you
put together in the hangar from EVERSPACE 2's ship modules, in its colour schemes, with its weapon and turret models.

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
   | `ES2/Content/Assets/Turrets/Meshes` | Models (all of them: the warships' turrets) |
   | `ES2/Content/Assets/Vehicles/Shared`, `ES2/Content/Assets/Environment/Structures`, `ES2/Content/Assets/Effects/Materials`, `ES2/Content/Assets/Blockouts/Materials` | Properties (.json), Textures (the warships' materials) |
   | `ES2/Content/Audio` | Properties (.json) and Audio (optional: the engine, boost and weapon sounds). Turn on Settings > **Convert audio on bulk export** first: the sounds then come out playable (`.ogg` / `.wav`) and the importer needs no other tool |
   | `ES2/Content/Assets/Vehicles/Shared/Textures` | Textures (optional: `T_Vehicles_Floaters_Emissive_M`, the glow pattern of the engine nozzles, `T_ShipModules_FX_001_M_A`, the pattern of the wings' hologram discs, the damage maps and `T_Vehicles_Okkar_Techdetail_001_*`, the Wraith's plating) |

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
Okkar frigate's weak spots; pirate and Void warships hostile), EVERSPACE 2's weapons in the shops (every primary and
secondary, the Okkar and legendary variants, with their own colours, sounds and models), and the Outlaw Dreadnought at
Herjaza once the Valkyrie add-on's story is over. Without them the mod is just the ships.

Without the weapons and the turret the ships still work: the guns fire from the ships' own weapon sockets, just without
weapon models on them. Without the noise texture the engine flames are smooth instead of streaked, and without the nozzle
mask the nozzles glow all over instead of in their rings and grilles.

## Building the mod

Open a terminal in this folder (Windows: in Explorer type `cmd` in this folder's address bar; macOS: Finder's
*Services > New Terminal at Folder*, or `cd` to it) and give it FModel's `Output/Exports` folder (dragging the folder onto
the terminal window types its path):

- Windows: `py import.py "C:\Tools\FModel\Output\Exports"`
- macOS / Linux: `python3 import.py ~/FModel/Output/Exports`

It checks the export first and lists anything missing, then
writes the mod to `es2_ships` next to this script (about 20 seconds). Options:

- `--no-preview`: skip rendering the mod's preview image (the Mods screen's card). By default, when Blender is found, the
  ships are rendered in their default builds and colours for it (`tools/preview_blender.py`, about a minute);
  without Blender the card shows their names only.
- `--no-icons`: skip the ships' shop icons. By default, when Blender is found, each ship's default build is rendered like
  the game's own ship icons (from its left, above and a little ahead, the nose dipping to the bottom left) and put on a
  ship frame (`icons/<ship>.png`, 180 x 88).
- `--remake <folder>`: a checkout of the remake's source (or its `Assets/Textures/textures/gof2_interface2_ipad_large.png`):
  the icons then use the game's own ship frame; without it they get a drawn look-alike.
- `--out <folder>`: write it somewhere else, for example straight into the game's Mods folder (`.../Mods/es2_ships`). An
  earlier build there is replaced; any other folder is never touched.
- `--zip`: also make `es2_ships.zip`.
- `--mobile`: also make a **phone version**, `es2_ships_phone.zip`: Blender reduces every model to a quarter of its
  triangles and the textures are halved (about 50 MB instead of 100 MB, and much lighter to draw). It has the same mod id, so
  saves move between your devices, and it joins multiplayer sessions with the PC version (see the notes below).
- `--ratio 0.4`: the share of triangles the phone version keeps (default 0.25).
- `--blender <path>`: Blender's executable (or `Blender.app` on a Mac), if it isn't found by itself.
- `--vgmstream <path>`: the `vgmstream-cli` that decodes raw `.binka` sounds, if it isn't found by itself.
- `--no-sounds`: build without EVERSPACE 2's sounds.

## Installing

- **PC**: copy the `es2_ships` folder (or `es2_ships.zip`) into the game's Mods folder (the main menu's Mods screen has
  *Open mods folder*) and turn it on there. Don't put this importer folder itself in the Mods folder.
- **Phone**: copy `es2_ships_phone.zip` to the phone, then in the game *Mods > Import mod* and pick it.

## In the game

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
