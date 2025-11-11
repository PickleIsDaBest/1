# Steam Unlocking Tools - Technical Analysis

This repository contains an in-depth technical analysis of how tools like SteamTools and GreenLuma unlock games on Steam.

## Files Overview

### 📚 Documentation Files

1. **`steam-unlock-mechanism.md`** - High-level overview
   - How API hooking/DLL injection works
   - Explanation of `.lua` script functions
   - Role of depot keys and manifest IDs
   - Limitations and detection methods

2. **`in-depth-example.md`** - Detailed technical implementation
   - Complete DLL injection code
   - Hook implementation with Detours
   - Manual hook installation (alternative method)
   - Steam API structures
   - Complete Lua script parser
   - Memory management
   - Step-by-step execution flow
   - Real-world code examples

3. **`visual-diagram.md`** - Visual representations
   - Memory layout diagrams
   - Function call flow diagrams
   - Data structure visualizations
   - Hook installation process
   - VTable hooking visualization
   - Content download flow

4. **`hooking-example.md`** - Conceptual examples
   - Simplified hook flow
   - DLL injection process
   - Memory layout
   - Lua script parsing concepts

### 🐍 Demonstration

5. **`demo-script.py`** - Python simulator
   - Simulates the hooking mechanism
   - Parses Lua scripts
   - Demonstrates API interception
   - Shows game launch flow

## Quick Start

### Understanding the Mechanism

1. Start with `steam-unlock-mechanism.md` for a high-level overview
2. Read `in-depth-example.md` for detailed code examples
3. Review `visual-diagram.md` for visual understanding
4. Run `demo-script.py` to see it in action

### Running the Demo

```bash
python demo-script.py
```

The demo will:
- Parse a sample Lua script
- Simulate hooking Steam API calls
- Show how fake ownership is checked
- Demonstrate manifest and depot key retrieval
- Simulate a game launch flow

## Key Concepts

### 1. DLL Injection
Tools inject a DLL into the Steam process that intercepts API calls.

### 2. API Hooking
Steam's API functions are replaced with custom implementations that return fake data.

### 3. Lua Scripts
Scripts define which games to unlock:
- `addappid()` - Registers a game as "owned"
- `setManifestid()` - Sets which version to download

### 4. Depot Keys
Encryption keys that allow Steam to decrypt downloaded game content.

### 5. Manifest IDs
Identifiers that tell Steam which specific build/version to download.

## Technical Flow

```
1. Tool injects DLL into Steam process
   ↓
2. DLL hooks Steam API functions (vtable patching)
   ↓
3. DLL loads and parses .lua script
   ↓
4. Script populates fake ownership database
   ↓
5. User tries to launch game
   ↓
6. Steam calls BIsAppInstalled()
   ↓
7. Hook intercepts and returns TRUE (fake ownership)
   ↓
8. Steam proceeds with download/launch
   ↓
9. Hooks provide manifest IDs and depot keys
   ↓
10. Game launches successfully
```

## Important Notes

⚠️ **Educational Purpose Only**

This documentation is provided for:
- Security research
- Understanding Steam's architecture
- Educational purposes
- Developing legitimate tools

❌ **Not For**
- Piracy
- Violating Steam's Terms of Service
- Unauthorized game unlocking

**Using such tools may result in:**
- Steam account bans
- VAC (Valve Anti-Cheat) bans
- Legal consequences
- Violation of terms of service

## How It Works (Summary)

### The Core Trick

Steam checks game ownership **client-side** before launching games. Tools exploit this by:

1. **Intercepting** Steam's API calls before they reach Steam's code
2. **Returning fake data** that makes Steam think you own games
3. **Providing valid manifest IDs** so Steam knows what to download
4. **Supplying depot keys** so Steam can decrypt the content

### Why It Works

- Steam trusts its own API responses
- Initial ownership checks are client-side
- Content servers serve based on manifest IDs (not ownership)
- Offline mode reduces server verification

### Why It Fails

- Online multiplayer requires server verification
- VAC can detect modified Steam processes
- Achievements/cloud saves are server-validated
- Some games require online activation

## Code Examples

See `in-depth-example.md` for complete implementations of:

- DLL injection (`InjectDLL()`)
- Hook installation (`InstallHooks()`)
- Lua script parsing (`ParseLuaScript()`)
- API interception (`Hooked_BIsAppInstalled()`)
- VTable patching
- Memory management

## Visual Aids

See `visual-diagram.md` for:

- Memory layout diagrams
- Function call flows
- Data structure visualizations
- Hook installation process
- Content download flow

## Further Reading

- Steam API documentation (public)
- Windows API documentation (DLL injection)
- Reverse engineering resources
- VTable hooking techniques
- Process memory manipulation

## Disclaimer

This analysis is provided for educational and research purposes only. The author does not condone or encourage the use of these techniques to violate terms of service or engage in piracy. Understanding how these mechanisms work helps with:

- Security research
- Anti-cheat development
- Legitimate tool development
- Educational purposes

Use this knowledge responsibly and ethically.
