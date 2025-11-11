# Conceptual Hook Implementation Example

This demonstrates the **concept** of how API hooking works - this is pseudocode for educational purposes only.

## Simplified Hook Flow

```cpp
// Pseudo-code showing the concept

// Original Steam API function (what Steam calls)
bool ISteamApps_BIsAppInstalled(AppId_t appID) {
    // Check Steam's internal ownership database
    return steam_ownership_db.contains(appID);
}

// Hooked version (what the tool replaces it with)
bool Hooked_BIsAppInstalled(AppId_t appID) {
    // First check our fake ownership list
    if (fake_owned_apps.contains(appID)) {
        return true;  // Lie to Steam: "Yes, you own this!"
    }
    
    // Otherwise, call original function
    return Original_BIsAppInstalled(appID);
}

// When .lua script calls: addappid(501)
void addappid(AppId_t appID, int flags, const char* depot_key) {
    fake_owned_apps.add(appID);
    depot_keys[appID] = depot_key;  // Store decryption key
}

// When Steam asks: "What manifest should I use for AppID 501?"
ManifestID_t GetManifestForApp(AppId_t appID) {
    if (manifest_map.contains(appID)) {
        return manifest_map[appID];  // Return fake manifest ID
    }
    return Original_GetManifest(appID);
}

// When .lua script calls: setManifestid(501, "8134324683205569669")
void setManifestid(AppId_t appID, const char* manifest_id) {
    manifest_map[appID] = parse_manifest_id(manifest_id);
}
```

## How DLL Injection Works

```
1. Tool process starts
   ↓
2. Tool finds Steam.exe process ID
   ↓
3. Tool calls Windows API:
   - OpenProcess() - Get handle to Steam process
   - VirtualAllocEx() - Allocate memory in Steam process
   - WriteProcessMemory() - Write hook DLL path
   - CreateRemoteThread() - Load DLL in Steam process
   ↓
4. DLL loads in Steam's address space
   ↓
5. DLL's DllMain() function runs
   ↓
6. DllMain() installs hooks using:
   - Detours library, or
   - Manual function patching (jmp instructions), or
   - Import Address Table (IAT) hooking
   ↓
7. Hooks redirect Steam API calls to custom functions
   ↓
8. Custom functions check .lua script data and return modified results
```

## Memory Layout Example

```
Steam Process Memory:
┌─────────────────────────┐
│ Steam.exe code          │
│  - Original functions   │
│  - API calls            │
└─────────────────────────┘
┌─────────────────────────┐
│ Injected DLL            │
│  - Hook functions        │
│  - Lua interpreter      │
│  - Fake ownership list  │
└─────────────────────────┘
┌─────────────────────────┐
│ Hooked Function Table   │
│  BIsAppInstalled → Hook │
│  GetManifest → Hook      │
└─────────────────────────┘
```

## Lua Script Parsing

The tool reads the `.lua` file and builds internal data structures:

```python
# Conceptual parsing (pseudocode)

fake_apps = {}
manifest_ids = {}
depot_keys = {}

def parse_lua_script(filename):
    with open(filename) as f:
        for line in f:
            if line.startswith('addappid('):
                # Parse: addappid(501, 0, "key...")
                match = re.match(r'addappid\((\d+)(?:,(\d+),"?([^"]+)"?)?\)', line)
                appid = int(match.group(1))
                flags = int(match.group(2)) if match.group(2) else 0
                key = match.group(3) if match.group(3) else None
                
                fake_apps[appid] = True
                if key:
                    depot_keys[appid] = key
                    
            elif line.startswith('setManifestid('):
                # Parse: setManifestid(501, "8134324683205569669")
                match = re.match(r'setManifestid\((\d+),"?([^"]+)"?\)', line)
                appid = int(match.group(1))
                manifest_id = match.group(2)
                
                manifest_ids[appid] = manifest_id
```

## Why Depot Keys Matter

Steam encrypts game content. When downloading:

```
1. Steam requests: "Give me files for manifest 8134324683205569669"
   ↓
2. Steam CDN responds with encrypted files
   ↓
3. Steam needs decryption key to decrypt files
   ↓
4. Hook intercepts: "What's the key for AppID 501?"
   ↓
5. Hook returns depot key from addappid() call
   ↓
6. Steam decrypts and installs game
```

Without the correct depot key, the downloaded files would be encrypted gibberish.

## Manifest ID Purpose

Manifests tell Steam:
- Which files to download
- File sizes and checksums
- Download URLs on CDN
- Dependencies between depots

By setting a manifest ID, you're telling Steam: "Download THIS specific version/build of the game."
