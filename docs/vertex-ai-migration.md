# Vertex AI SDK Migration Notes

## Current Status

The project currently uses `google-cloud-aiplatform` version 1.128.0 with the `vertexai.generative_models` module.

## Deprecation Warning

Google has deprecated the Generative AI module in the Vertex AI SDK:
- **Deprecated**: `vertexai.generative_models` (and related modules)
- **Deprecation Date**: June 24, 2025
- **Removal Date**: June 24, 2026
- **Replacement**: `google-genai` SDK

## Migration Plan

**Priority**: LOW (working until June 2026)

**Steps**:
1. Monitor `google-genai` SDK maturity and feature parity
2. Create migration branch when ready (before Q2 2026)
3. Replace `google-cloud-aiplatform` with `google-genai` in pyproject.toml
4. Update imports in `src/llm/gemini_client.py`:
   - FROM: `from vertexai.generative_models import GenerativeModel, GenerationConfig`
   - TO: TBD (check google-genai documentation)
5. Test all LLM functionality (e2e tests should catch issues)
6. Update authentication if needed

## Resources

- [Deprecation Notice](https://cloud.google.com/vertex-ai/generative-ai/docs/deprecations/genai-vertexai-sdk)
- [Migration Guide](https://cloud.google.com/vertex-ai/generative-ai/docs/migrate/migrate-google-gen-ai)

## Temporary Workaround

To suppress warnings in tests (optional):
```python
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="vertexai")
```
