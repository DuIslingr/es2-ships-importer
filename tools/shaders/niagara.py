# niagara.py <NS_*.json> [script name...]: disassembles a cooked Niagara system's VM scripts (UE 5.6's legacy VectorVM
# bytecode, CachedScriptVM.ByteCode; the JSON as FModel exports a NiagaraSystem) into readable lines. Operands: r<n> temp
# registers, constants as the script's own parameter (ScriptExecutionParamStore), a literal or an engine global, named
# where known. The constant table: a particle script's 640 bytes of engine globals, its parameters, then its literals; an
# interpolated spawn script's globals, parameters, the PREV_ globals and parameters, then its literals (1280 + 2 x the
# parameter size); a system script's 32 bytes of globals, its parameters, its literals. inputdata / outputdata of dataset 0
# name the particle attribute's component (floats and ints counted apart); dataset 1 (a system script's instance
# parameters) prints the raw index (see the system's UpdateInstanceParamsDataSetCompiledData). The only external function
# handled is a curve data interface (one input, one output).
import json, struct, sys

OPS = """done add sub mul div mad lerp rcp rsq sqrt neg abs exp exp2 log log2 sin cos tan asin acos atan atan2 ceil floor fmod
frac trunc clamp min max pow round sign step random noise cmplt cmple cmpgt cmpge cmpeq cmpneq select addi subi muli divi clampi
mini maxi absi negi signi randomi cmplti cmplei cmpgti cmpgei cmpeqi cmpneqi bit_and bit_or bit_xor bit_not bit_lshift
bit_rshift logic_and logic_or logic_xor logic_not f2i i2f f2b b2f i2b b2i inputdata_float inputdata_int32 inputdata_half
inputdata_noadvance_float inputdata_noadvance_int32 inputdata_noadvance_half outputdata_float outputdata_int32 outputdata_half
acquireindex external_func_call exec_index noise2D noise3D enter_stat_scope exit_stat_scope update_id acquire_id half_to_float
fasi iasf""".split()
ARITY = {}
for n in "rcp rsq sqrt neg abs exp exp2 log log2 sin cos tan asin acos atan ceil floor frac trunc round sign random absi negi signi randomi bit_not logic_not f2i i2f f2b b2f i2b b2i half_to_float fasi iasf".split(): ARITY[n] = 1
for n in "add sub mul div atan2 fmod min max pow step noise cmplt cmple cmpgt cmpge cmpeq cmpneq addi subi muli divi mini maxi cmplti cmplei cmpgti cmpgei cmpeqi cmpneqi bit_and bit_or bit_xor bit_lshift bit_rshift logic_and logic_or logic_xor noise2D".split(): ARITY[n] = 2
for n in "mad lerp clamp select clampi noise3D".split(): ARITY[n] = 3
GLOBALS = {0: "Engine.WorldDeltaTime", 4: "Engine.DeltaTime", 8: "Engine.InverseDeltaTime", 12: "Engine.Time", 16: "Engine.RealTime",
           20: "Engine.QualityLevel"}
COMPONENTS = {"NiagaraFloat": 1, "Vector2f": 2, "Vector3f": 3, "Vector4f": 4, "LinearColor": 4, "Quat4f": 4, "NiagaraPosition": 3,
              "NiagaraInt32": 1, "NiagaraBool": 1, "NiagaraID": 2, "Vector": 3, "Vector2D": 2, "Vector4": 4, "Quat": 4}
INTS = {"NiagaraInt32", "NiagaraBool", "NiagaraID"}

def tname(td):
    c = td.get("ClassStructOrEnum") or {}
    n = c.get("ObjectName", "")
    return n.split("'")[1] if "'" in n else n

def components(attrs):
    fl, it = [], []
    for a in attrs:
        t = tname(a["TypeDef"]); n = COMPONENTS.get(t, 1)
        if t == "NiagaraID": it += [a["Name"] + ".Index", a["Name"] + ".AcquireTag"]; continue
        lst = it if t in INTS else fl
        for k in range(n): lst.append(a["Name"] + ("" if n == 1 else "." + "xyzw"[k]))
    return fl, it

def disasm(script, out=print):
    p = script["Properties"]; vm = p["CachedScriptVM"]
    bc = vm["ByteCode"]["Data"]; lit = bytes(vm.get("ScriptLiterals") or [])
    store = p.get("ScriptExecutionParamStore") or {}
    psize = store.get("ParameterSize", 0)
    interp = "Interpolated" in (p.get("Usage") or "")
    half = psize   # (ParameterSize counts the current half only)
    # interpolated spawn: [globals 640][params, current][PREV globals 640][PREV params], then the literals
    # (system scripts see only the 32-byte global block before their parameters)
    gb = 32 if "System" in (p.get("Usage") or "") else 640
    lbase = 1280 + 2 * psize if interp else gb + psize
    params = {}
    for x in store.get("SortedParameterOffsets", []):
        o = x["Offset"]
        params[(gb + o) if o < half else (1280 + o)] = x["Name"]
    prev = 640 + half
    fl, it = components(vm.get("Attributes") or [])
    ntemp = vm.get("NumTempRegisters", 1 << 16)
    def opnd(x, isconst): return const(x) if isconst or x >= ntemp else f"r{x}"
    def const(o):
        if o in params: return params[o]
        lower = [b for b in params if b < o < lbase]
        if lower: b = max(lower); return f"{params[b]}+{o-b}"
        if lbase <= o < lbase + len(lit):
            v = struct.unpack_from("<f", lit, o - lbase)[0]; i = struct.unpack_from("<i", lit, o - lbase)[0]
            return f"{i}" if abs(i) < 1 << 20 else f"{v:.6g}"
        if interp and prev <= o < prev + 640: return "PREV_" + GLOBALS.get(o - prev, f"G{o - prev}")
        return GLOBALS.get(o, f"G{o}")
    i = 0
    def u8():
        nonlocal i; v = bc[i]; i += 1; return v
    def u16():
        nonlocal i; v = bc[i] | bc[i + 1] << 8; i += 2; return v
    depth = 0
    while i < len(bc):
        at = i; op = u8()
        name = OPS[op] if op < len(OPS) else f"op{op}"
        if name == "done": out(f"{at:5}: done"); break
        if name in ARITY:
            t = u8(); srcs = [u16() for _ in range(ARITY[name])]; d = u16()
            s = ", ".join(opnd(x, t >> k & 1) for k, x in enumerate(srcs))
            out(f"{at:5}: {'  '*depth}r{d} = {name}({s})")
        elif name.startswith("inputdata"):
            ds = u16(); idx = u16(); d = u16()
            src = (it if "int" in name else fl); a = (src[idx] if idx < len(src) else f"#{idx}") if ds == 0 else f"param{'i' if 'int' in name else 'f'}{idx}"
            out(f"{at:5}: {'  '*depth}r{d} = {name}[{ds}] {a}")
        elif name.startswith("outputdata"):
            t = u8(); ds = u16(); ir = u16(); s = u16(); dst = u16()
            src = (it if "int" in name else fl); a = src[dst] if dst < len(src) else f"#{dst}"
            out(f"{at:5}: {'  '*depth}out[{ds}] {a} = {opnd(s, False)}")
        elif name == "acquireindex":
            t = u8(); ds = u16(); s = u16(); d = u16()
            out(f"{at:5}: {'  '*depth}r{d} = acquireindex[{ds}]({opnd(s, t & 1)})")
        elif name == "exec_index":
            out(f"{at:5}: {'  '*depth}r{u16()} = exec_index")
        elif name == "enter_stat_scope":
            out(f"{at:5}: {'  '*depth}{{ scope {const(u16())}"); depth += 1
        elif name == "exit_stat_scope":
            depth = max(0, depth - 1); out(f"{at:5}: {'  '*depth}}}")
        elif name == "external_func_call":
            # (the only data interface these systems call: a float curve, one input and one output; an input with bit 15
            # set is a register, else a constant)
            f = u8(); a = u16(); d = u16()
            src = f"r{a & 0x7fff}" if a & 0x8000 else const(a)
            out(f"{at:5}: {'  '*depth}r{d} = curve#{f}({src})")
        elif name in ("update_id", "acquire_id"):
            a = u16(); b = u16(); out(f"{at:5}: {'  '*depth}{name}({a}, {b})")
        else:
            out(f"{at:5}: {name} ??? next {bc[i:i+12]}"); return

if __name__ == "__main__":
    d = json.load(open(sys.argv[1])); want = sys.argv[2:]
    for e in d:
        if e.get("Type") != "NiagaraScript" or (want and e["Name"] not in want): continue
        p = e["Properties"]
        print(f"===== {e['Name']} {p.get('Usage')}")
        sc = json.loads(p["CachedScriptVM"].get("StatScopes") or "[]") if isinstance(p["CachedScriptVM"].get("StatScopes"), str) else p["CachedScriptVM"].get("StatScopes")
        print("  scopes:", [s.get("FriendlyName") for s in sc or []])
        disasm(e)
