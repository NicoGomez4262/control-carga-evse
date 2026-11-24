// Usa include/secrets.h si existe (no se sube a git); si no, los valores vacíos de secrets.example.h.
#pragma once
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif
