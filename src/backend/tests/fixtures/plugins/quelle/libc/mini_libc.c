// Minimaler Ersatz fuer die libc-Funktionen, die der von wit-bindgen erzeugte C-Code braucht.
// Bump-Allocator: Speicher wird nie freigegeben - fuer ein Test-Plugin, das pro Aufruf neu
// instanziiert wird, ausreichend.
#include <stddef.h>
#include <stdint.h>
extern unsigned char __heap_base;
static uintptr_t naechster = 0;

void *malloc(size_t n) {
    if (!naechster) naechster = (uintptr_t)&__heap_base;
    naechster = (naechster + 7) & ~(uintptr_t)7;
    uintptr_t ende = naechster + n;
    size_t seiten = __builtin_wasm_memory_size(0);
    if (ende > seiten * 65536) {
        size_t mehr = (ende - seiten * 65536 + 65535) / 65536;
        if (__builtin_wasm_memory_grow(0, mehr) == (size_t)-1) __builtin_trap();
    }
    void *p = (void *)naechster;
    naechster = ende;
    return p;
}
void free(void *p) { (void)p; }
void *memcpy(void *d, const void *s, size_t n) { unsigned char *a = d; const unsigned char *b = s; while (n--) *a++ = *b++; return d; }
void *memset(void *d, int c, size_t n) { unsigned char *a = d; while (n--) *a++ = (unsigned char)c; return d; }
void *realloc(void *p, size_t n) { void *q = malloc(n); if (p && q) memcpy(q, p, n); return q; }
size_t strlen(const char *s) { size_t n = 0; while (s[n]) n++; return n; }
void abort(void) { __builtin_trap(); }
