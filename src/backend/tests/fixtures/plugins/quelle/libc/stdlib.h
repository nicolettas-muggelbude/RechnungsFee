#pragma once
#include <stddef.h>
void *malloc(size_t n);
void *realloc(void *p, size_t n);
void free(void *p);
void abort(void) __attribute__((noreturn));
