// disasm <in.bin> <out.asm>: the DXBC container inside a UE shader blob, disassembled with d3dcompiler_47's D3DDisassemble
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef struct ID3DBlobVtbl { HRESULT (WINAPI *QI)(void*, REFIID, void**); ULONG (WINAPI *AddRef)(void*); ULONG (WINAPI *Release)(void*);
  void* (WINAPI *GetBufferPointer)(void*); SIZE_T (WINAPI *GetBufferSize)(void*); } ID3DBlobVtbl;
typedef struct { ID3DBlobVtbl *v; } ID3DBlob;
typedef HRESULT (WINAPI *Dis)(const void*, SIZE_T, UINT, const char*, ID3DBlob**);
int main(int argc, char **argv) {
  FILE *f = fopen(argv[1], "rb"); fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
  unsigned char *b = malloc(n); fread(b, 1, n, f); fclose(f);
  long i = 0; for (; i + 4 <= n; i++) if (!memcmp(b + i, "DXBC", 4)) break;
  if (i + 32 > n) { printf("no DXBC\n"); return 1; }
  unsigned size = *(unsigned*)(b + i + 24);
  HMODULE m = LoadLibraryA("d3dcompiler_47.dll"); Dis d = (Dis)GetProcAddress(m, "D3DDisassemble");
  ID3DBlob *out = 0; HRESULT hr = d(b + i, size, 0, 0, &out);
  if (FAILED(hr) || !out) { printf("D3DDisassemble failed %lx\n", hr); return 2; }
  FILE *o = fopen(argv[2], "wb"); fwrite(out->v->GetBufferPointer(out), 1, out->v->GetBufferSize(out), o); fclose(o);
  printf("%s: %u bytes of DXBC -> %s\n", argv[1], size, argv[2]); return 0;
}
