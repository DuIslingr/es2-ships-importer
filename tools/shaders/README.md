# Reading EVERSPACE 2's shaders

Research tools (not used by the importer): how EVERSPACE 2's effects are drawn, from its compiled shaders. See
`../../research/engine_exhaust.md`.

- `ShaderDump` (needs the .NET 10 SDK and CUE4Parse cloned next to it: `git clone --recursive
  https://github.com/FabianFG/CUE4Parse.git`): `ES2_GAME=<install> ES2_USMAP=<.usmap> ES2_AES_KEY=0x... dotnet run -c
  Release -- material "ES2/Content/<path>.<Object>" <outdir>`: a material's shaders per platform (`<n>_<frequency>.bin`)
  and `uniforms.json`. The AES key and mappings are the ones FModel needs (see the main README).
- `disasm.c`: `x86_64-w64-mingw32-gcc -O2 -o disasm.exe disasm.c`, then `wine disasm.exe <shader.bin> <out.asm>` (Wine's
  `d3dcompiler_47` disassembles the DXBC container inside).
- `blueprint` mode: `... dotnet run -c Release -- blueprint "ES2/Content/<path>.<Object>" <out.json>` writes a blueprint
  with its Kismet bytecode (the per-tick logic, e.g. `BP_ShipBase`'s engine effects).
- `niagara.py <NS_*.json> [script ...]`: disassembles a Niagara system's VM scripts from FModel's JSON export of it (the
  emitters' spawn and update logic: rates, lifetimes, velocities, colours; see the file's header for the constant layout).
