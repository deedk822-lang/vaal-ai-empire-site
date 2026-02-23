# CodeRabbitAI Issues and Fixes Summary

## 1. agents/lib/perplexity_financial_client.py

### Issue: Missing ClassVar annotations for mutable class attributes
- **Lines**: Top of file (constants)
- **Problem**: Module-level constants like `SEC_ALLOWLIST` and `NEWS_DENYLIST` are mutable lists
- **Fix**: Add `ClassVar` type hints to prevent instance shadowing
- **Action**: Add imports for `ClassVar` and `List` from typing, then annotate the constants

## 2. agents/sentient_swarm/agents/multilingual_voice_agent.py

### Issue 1: Mutable class attributes without ClassVar annotations
- **Lines**: 63-79
- **Problem**: `SUPPORTED_LANGUAGES` and `COMMON_MIXES` are mutable class-level attributes
- **Fix**: Add `ClassVar` annotations with proper typing
- **Action**: Import `ClassVar`, `Dict`, `List`, `Tuple` from typing and annotate both attributes

### Issue 2: Context parameter is accepted but ignored
- **Lines**: 424-436 (_get_llm_response function)
- **Problem**: `context` parameter is passed but never used in the LLM call
- **Fix**: Either use the context in the LLM prompt or remove the parameter
- **Action**: Incorporate context into system_prompt before passing to LLM

### Issue 3: Broad exception handlers with str(e)
- **Lines**: 146, 207, 233, 291
- **Problem**: Catching generic `Exception` and using `str(e)` instead of `{e!s}`
- **Fix**: Replace with specific exception types and use `{e!s}` in f-strings
- **Action**: Identify specific exceptions (ValueError, OSError, etc.) and update handlers

## 3. ml/african_languages/training/train_multilingual_asr.py

### Issue 1: Unused batch_size parameter
- **Lines**: 166-205 (create_dataloaders method)
- **Problem**: `batch_size` parameter is accepted but never used
- **Fix**: Remove the unused parameter
- **Action**: Delete `batch_size: int = 16` from function signature

### Issue 2: Ambiguous variable name 'l'
- **Lines**: 188
- **Problem**: Single-letter variable name `l` in list comprehension
- **Fix**: Rename to `lab` or `label`
- **Action**: Change `max(len(l) for l in labels)` to `max(len(lab) for lab in labels)`

## 4. ml/african_languages/training/train_multilingual_tts.py

### Issue 1: Redundant local imports in __init__
- **Lines**: 221-231
- **Problem**: Importing `Vits`, `AudioProcessor`, `json` inside the method
- **Fix**: Move imports to top of file or use proper config deserialization
- **Action**: Remove local imports and use proper VitsConfig deserialization

### Issue 2: Ambiguous variable name 'l' in demo
- **Lines**: 342-345
- **Problem**: Using `l` as loop variable and naive substring matching
- **Fix**: Rename variable to `code` and use proper word-boundary matching
- **Action**: Replace `[l for l in ['zu', 'xh', 'af', 'en'] if l in text.lower()]` with proper matching

## 5. ml/african_languages/data/download_common_voice.py

### Issue 1: Missing integrity check in download_file
- **Lines**: 51-76
- **Problem**: No verification that downloaded file size matches Content-Length
- **Fix**: Add size verification before returning True
- **Action**: Track bytes written and compare with total_size

### Issue 2: Silent failure when duration column is missing
- **Lines**: 160-193 (verify_dataset function)
- **Problem**: Returns total_hours=0 without warning if duration column is absent
- **Fix**: Add warning when duration column is missing
- **Action**: Check if "duration" in reader.fieldnames and log warning if absent

## 6. server/models/User.js

### Issue: Inconsistent token access pattern
- **Lines**: 351-363 (generateVerificationToken method)
- **Problem**: Pre-save hook sets `_rawVerificationToken` but method only returns it
- **Fix**: Already fixed - method now sets `_rawVerificationToken` property
- **Status**: ALREADY IMPLEMENTED - No changes needed

## Summary of Changes Required

| File | Type | Priority | Status |
|------|------|----------|--------|
| perplexity_financial_client.py | Type hints | Medium | TODO |
| multilingual_voice_agent.py | Type hints + Logic | High | TODO |
| train_multilingual_asr.py | Code cleanup | Low | TODO |
| train_multilingual_tts.py | Code cleanup | Low | TODO |
| download_common_voice.py | Error handling | Medium | TODO |
| User.js | Already fixed | N/A | DONE |
