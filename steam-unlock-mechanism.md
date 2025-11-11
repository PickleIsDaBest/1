# How Steam Unlocking Tools Work (Technical Analysis)

## Overview

Tools like SteamTools and GreenLuma work by intercepting Steam's API calls and manipulating the client's perception of game ownership and content manifests. They don't modify Steam's servers - instead, they hook into the Steam client process to return modified data.

## Core Mechanism

### 1. **API Hooking / DLL Injection**

These tools inject a DLL (Dynamic Link Library) into the Steam process that intercepts key Steam API functions:

- `ISteamApps::BIsDlcInstalled()` - Checks if DLC is installed
- `ISteamApps::GetAppInstallState()` - Gets installation state
- `ISteamApps::BIsAppInstalled()` - Checks if app is installed
- `ISteamClient::GetISteamApps()` - Gets the apps interface
- Content server manifest queries

### 2. **The .lua Script Format**

The `.lua` files you showed contain instructions that the tool interprets:

```lua
addappid(500)  -- Adds AppID 500 to the "owned" list
addappid(1660740)  -- Adds AppID 1660740

addappid(501, 0, "7a0b21eed084464fd2efb03ecc44116224b150f9377551ca7901ead966f21c26")
-- Parameters:
--   501: AppID
--   0: Unknown flag (possibly DLC flag or ownership type)
--   "7a0b21...": Depot key/decryption key (SHA-256 hash)

setManifestid(501, "8134324683205569669")
-- Sets the manifest ID for AppID 501
-- Manifest ID identifies a specific version/build of the game's content
```

### 3. **What Each Function Does**

#### `addappid(appid, flags, depot_key)`
- Registers an AppID as "owned" in the tool's internal database
- The `depot_key` is a decryption key for the game's content depots
- When Steam queries "Do I own this game?", the hook returns `true` for these AppIDs

#### `setManifestid(appid, manifest_id)`
- Associates a specific manifest ID with an AppID
- Manifests describe what files/versions are available for download
- Steam uses manifest IDs to determine which version of content to download
- The tool intercepts manifest queries and returns these IDs

### 4. **The .manifest Files**

`.manifest` files contain detailed information about game content:

- File lists and checksums
- Depot information
- Download URLs (pointing to Steam's CDN)
- File sizes and compression info

These are typically downloaded from Steam's content servers. The tool may:
- Cache legitimate manifests it downloads
- Modify manifests to point to accessible content
- Use manifests to tell Steam what files exist

## Technical Flow

```
1. Steam Client starts
   ↓
2. Tool DLL injected into Steam process
   ↓
3. Tool loads .lua script
   ↓
4. Tool hooks Steam API functions
   ↓
5. User tries to launch game
   ↓
6. Steam calls: "Is AppID 501 installed?"
   ↓
7. Hook intercepts → Returns TRUE (because addappid(501) was called)
   ↓
8. Steam calls: "Get manifest for AppID 501"
   ↓
9. Hook intercepts → Returns manifest ID from setManifestid()
   ↓
10. Steam downloads content using manifest
    ↓
11. Game launches (if content is available)
```

## Key Technical Details

### Depot Keys
The long hex strings (like `"7a0b21eed084464fd2efb03ecc44116224b150f9377551ca7901ead966f21c26"`) are:
- SHA-256 hashes used as decryption keys
- Steam encrypts game content in depots
- These keys decrypt the content when downloading
- Obtained from Steam's content servers (requires access to the depot)

### Manifest IDs
- Unique identifiers for specific builds/versions
- Format: Large integers (e.g., `"8134324683205569669"`)
- Steam uses these to determine which version to download
- Must match a valid manifest on Steam's CDN

### Why This Works
1. **Client-Side Validation**: Steam client trusts its own API responses
2. **No Server Verification**: Initial ownership checks happen client-side
3. **Content Server Access**: Steam's CDN serves content based on manifest IDs, not ownership
4. **Offline Mode**: Some functionality works offline, making hooks easier

## Limitations & Detection

### What Doesn't Work:
- Online multiplayer (VAC-protected games)
- Achievements/leaderboards (server-validated)
- Cloud saves (server-validated)
- Games requiring online activation
- Steam Workshop content (server-validated)

### Detection Methods:
- VAC (Valve Anti-Cheat) can detect modified Steam processes
- Server-side ownership verification for online features
- Behavioral analysis of API call patterns

## Legal & Ethical Considerations

**Important**: This information is provided for educational purposes only. Using such tools may:
- Violate Steam's Terms of Service
- Result in account bans
- Be illegal in some jurisdictions
- Harm game developers

Understanding the mechanism helps with:
- Security research
- Understanding Steam's architecture
- Developing legitimate tools
- Educational purposes

## References

- Steam API documentation (public)
- Reverse engineering research
- Steam content delivery system architecture
