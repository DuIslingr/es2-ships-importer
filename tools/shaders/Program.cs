// ShaderDump: a material's compiled shaders out of EVERSPACE 2's IoStore archives (CUE4Parse), for reading how its effects
// are drawn. Environment: ES2_GAME (the install folder), ES2_USMAP (the type mappings, e.g. Dumper-7's), ES2_AES_KEY (0x...).
//   material <package path.object> <outdir>: each shader platform's shader map: the shaders per vertex factory, their code
//     (Oodle-decompressed; a DXBC container inside each, disassemble with disasm.exe) and uniforms.json (the material's
//     preshaders: which parameters fill which slot of its uniform buffer).
using Serilog;
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Assets.Exports.Material;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using CUE4Parse.UE4.IO;
using CUE4Parse.UE4.IO.Objects;
using CUE4Parse.UE4.Readers;
using CUE4Parse.UE4.Shaders;
using CUE4Parse.UE4.Assets.Exports.Material;

Serilog.Log.Logger = new Serilog.LoggerConfiguration().MinimumLevel.Debug().WriteTo.Console().CreateLogger();
var game = Environment.GetEnvironmentVariable("ES2_GAME") ?? throw new Exception("set ES2_GAME to EVERSPACE 2's install folder");
OodleHelper.Initialize(Path.Combine(AppContext.BaseDirectory, OodleHelper.OodleFileName));
var provider = new DefaultFileProvider(game, SearchOption.AllDirectories, new VersionContainer(EGame.GAME_UE5_6), StringComparer.OrdinalIgnoreCase);
provider.MappingsContainer = new FileUsmapTypeMappingsProvider(Environment.GetEnvironmentVariable("ES2_USMAP") ?? throw new Exception("set ES2_USMAP to the game's .usmap"));
provider.ReadShaderMaps = true;
provider.ReadScriptData = true;
provider.Initialize();
provider.SubmitKey(new FGuid(), new FAesKey(Environment.GetEnvironmentVariable("ES2_AES_KEY") ?? throw new Exception("set ES2_AES_KEY to the game's AES key (0x...)")));
provider.PostMount();
if (args[0] == "list")
{
    Console.WriteLine($"files {provider.Files.Count} vfs {provider.MountedVfs.Count}/{provider.UnloadedVfs.Count}");
    string filter = args.Length > 1 ? args[1] : null;
    foreach (var f in provider.Files.Keys)
        if (filter != null ? System.Text.RegularExpressions.Regex.IsMatch(f, filter, System.Text.RegularExpressions.RegexOptions.IgnoreCase) : f.Contains("shader", StringComparison.OrdinalIgnoreCase) && !f.Contains("/Content/Assets/")) Console.WriteLine(f);
    return;
}
if (args[0] == "export")
{
    // export <list file> <out dir> [all]: each line an object path (/Game/... or ES2/Content/..., with or without ".Name"):
    // static and skeletal meshes as .glb with their materials (FModel's resolved .json form) and textures (.png), textures
    // and material instances on their own; laid out like FModel's export (<out>/ES2/Content/...). 'all': a material's
    // parameters through its whole parent chain (the default stops at the instance's own).
    CUE4Parse_Conversion.Textures.TextureDecoder.UseAssetRipperTextureDecoder = true;
    var session = new CUE4Parse_Conversion.ExportSession { MaxDegreeOfParallelism = Math.Max(1, Environment.ProcessorCount / 2) };
    int queued = 0, missing = 0;
    foreach (var raw in File.ReadAllLines(args[1]))
    {
        var line = raw.Trim();
        if (line.Length == 0 || line.StartsWith("#")) continue;
        if (line.StartsWith("/Game/")) line = "ES2/Content/" + line.Substring(6);
        if (!line.Contains('.')) line = line + "." + line.Split('/').Last();
        try { session.Add(provider.LoadPackageObject(line)); queued++; }
        catch (Exception e) { missing++; Console.WriteLine($"MISSING {line}: {e.Message}"); }
    }
    Console.WriteLine($"queued {queued}, missing {missing}");
    var options = new CUE4Parse_Conversion.Options.ExportOptions(meshFormat: CUE4Parse_Conversion.Options.EMeshFormat.Gltf2,
        meshQuality: CUE4Parse_Conversion.Options.EMeshQuality.Highest, textureFormat: CUE4Parse_Conversion.Options.ETextureFormat.Png,
        materialDepth: args.Length > 3 && args[3] == "all" ? EMaterialDepth.AllLayers : EMaterialDepth.TopLayerOnly);
    var results = session.RunAsync(args[2], options).GetAwaiter().GetResult();
    int ok = 0;
    foreach (var r in results)
        if (r.Success) ok++;
        else Console.WriteLine($"FAILED {r.ObjectPath}: {r.Error?.Message}");
    Console.WriteLine($"exported {ok} of {results.Count}");
    return;
}
if (args[0] == "blueprint")
{
    // a blueprint's exports with their Kismet bytecode, as JSON (args: package path without extension, out file)
    var pkg = provider.LoadPackage(args[1] + ".uasset");
    var all = pkg.GetExports().ToList();
    File.WriteAllText(args[2], Newtonsoft.Json.JsonConvert.SerializeObject(all, Newtonsoft.Json.Formatting.Indented));
    Console.WriteLine($"{all.Count} exports -> {args[2]}");
    return;
}
if (args[0] == "material")
{
    var m = provider.LoadPackageObject<UMaterialInterface>(args[1]);
    Console.WriteLine($"{m.Name}: {m.LoadedMaterialResources.Count} resources");
    // the parent chain (an instance without static switches of its own has no shaders: its parent's are drawn)
    for (UMaterialInterface? p = m; p is UMaterialInstance mi && mi.Parent?.Load<UMaterialInterface>() is { } up; p = up)
        Console.WriteLine($" parent {up.GetPathName()}");
    foreach (var r in m.LoadedMaterialResources)
    {
        var sm = r.LoadedShaderMap;
        if (sm == null) { Console.WriteLine(" no shader map"); continue; }
        Console.WriteLine($" platform {sm.ShaderPlatform} hash {sm.ResourceHash} shaders {sm.Content?.Shaders?.Length}");
        var dir = Path.Combine(args[2], sm.ShaderPlatform.ToString());
        Directory.CreateDirectory(dir);
        void List(string label, CUE4Parse.UE4.Assets.Exports.Material.FShaderMapContent c)
        {
            foreach (var s in c.Shaders) Console.WriteLine($"  [{label}] {s.Type} freq {s.Target.Frequency} res {s.ResourceIndex} instr {s.NumInstructions}");
        }
        if (sm.Content != null) List("material", sm.Content);
        if (sm.Content is FMaterialShaderMapContent mc0)
            File.WriteAllText(Path.Combine(dir, "uniforms.json"), Newtonsoft.Json.JsonConvert.SerializeObject(mc0.MaterialCompilationOutput, Newtonsoft.Json.Formatting.Indented));
        if (sm.Content is FMaterialShaderMapContent mc && mc.OrderedMeshShaderMaps != null)
            foreach (var vf in mc.OrderedMeshShaderMaps) List(vf.VertexFactoryTypeName.ToString(), vf);
        if (sm.Code != null)
        {
            Console.WriteLine($"  code: {sm.Code.ShaderCodeResources.Length} resources");
            for (int i = 0; i < sm.Code.ShaderCodeResources.Length; i++)
            {
                var cr = sm.Code.ShaderCodeResources[i];
                var data = cr.Code.Data;
                byte[] code = data;
                if (cr.Header.UncompressedSize > data.Length)
                {
                    code = new byte[cr.Header.UncompressedSize];
                    OodleHelper.Decompress(data, 0, data.Length, code, 0, code.Length);
                }
                File.WriteAllBytes(Path.Combine(dir, $"{i:D3}_{cr.Header.Frequency}.bin"), code);
                Console.WriteLine($"   {i:D3} {cr.Header.Frequency} {data.Length} -> {code.Length} (code {cr.Header.ShaderCodeSize})");
            }
        }
        if (sm.ResourceHash != null) Dump(sm.ResourceHash.ToString(), args[2]);
    }
}

void Dump(string mapHash, string outDir)
{
    Directory.CreateDirectory(outDir);
    var readers = provider.MountedVfs.OfType<IoStoreReader>().ToList();
    foreach (var lr in readers)
        foreach (var id in lr.TocResource.ChunkIds)
        {
            if (id.ChunkType != (byte) EIoChunkType5.ShaderCodeLibrary) continue;
            var bytes = lr.Read(id);
            var lib = new FShaderCodeArchive(new FByteArchive("lib", bytes, provider.Versions));
            if (lib.SerializedShaders is not FIoStoreShaderCodeArchive a) continue;
            int mi = Array.FindIndex(a.ShaderMapHashes, h => h.ToString() == mapHash);
            Console.WriteLine($"library in {lr.Name}: {a.ShaderMapHashes.Length} maps, {a.ShaderEntries.Length} shaders; ours {mi}");
            if (mi < 0) continue;
            var me = a.ShaderMapEntries[mi];
            var groups = new Dictionary<uint, byte[]>();
            for (uint k = 0; k < me.NumShaders; k++)
            {
                uint si = a.ShaderIndices[me.ShaderIndicesOffset + k];
                var se = a.ShaderEntries[si];
                var g = a.ShaderGroupEntries[se.ShaderGroupIndex];
                if (!groups.TryGetValue(se.ShaderGroupIndex, out var code))
                {
                    var gid = a.ShaderGroupIoHashes[se.ShaderGroupIndex];
                    byte[] raw = null;
                    foreach (var r in readers) { try { raw = r.Read(gid); break; } catch { } }
                    if (raw == null) { Console.WriteLine($"  group {se.ShaderGroupIndex} not found"); continue; }
                    if (g.CompressedSize < g.UncompressedSize)
                    {
                        code = new byte[g.UncompressedSize];
                        OodleHelper.Decompress(raw, 0, raw.Length, code, 0, code.Length);
                    }
                    else code = raw;
                    groups[se.ShaderGroupIndex] = code;
                }
                // its size: up to the next shader of the group
                long start = (long) se.UncompressedOffsetInGroup, end = g.UncompressedSize;
                for (uint j = 0; j < g.NumShaders; j++)
                {
                    var o = (long) a.ShaderEntries[a.ShaderIndices[g.ShaderIndicesOffset + j]].UncompressedOffsetInGroup;
                    if (o > start && o < end) end = o;
                }
                var blob = code.AsSpan((int) start, (int) (end - start)).ToArray();
                var name = $"{k:D3}_{se.Frequency}_{si}.bin";
                File.WriteAllBytes(Path.Combine(outDir, name), blob);
                Console.WriteLine($"  {name} {blob.Length} bytes");
            }
            return;
        }
}
