# Deep Dive: How Steam Unlocking Tools Work Internally

## Table of Contents
1. [Steam Client Architecture](#steam-client-architecture)
2. [API Hooking Mechanisms](#api-hooking-mechanisms)
3. [Ownership Verification Flow](#ownership-verification-flow)
4. [Content Delivery System](#content-delivery-system)
5. [Manifest System Deep Dive](#manifest-system-deep-dive)
6. [Depot Encryption System](#depot-encryption-system)
7. [Implementation Details](#implementation-details)

---

## Steam Client Architecture

### Steam Process Structure

```
Steam.exe
├── steamclient.dll (Core Steam API)
│   ├── ISteamClient interface
│   ├── ISteamApps interface
│   ├── ISteamUser interface
│   └── ISteamUtils interface
├── steam_api.dll (Game API)
├── Content servers communication
└── Local cache/database
    ├── appinfo.vdf (App metadata)
    ├── config.vdf (User config)
    └── appcache/ (Downloaded manifests)
```

### Key Interfaces

**ISteamApps** - The primary interface for game ownership checks:

```cpp
class ISteamApps {
    virtual bool BIsAppInstalled(AppId_t appID);
    virtual bool BIsDlcInstalled(AppId_t appID, AppId_t dlcAppID);
    virtual uint32 GetAppInstallState(AppId_t appID);
    virtual bool GetAppInstallDir(AppId_t appID, char* pchFolder, uint32 cchFolderBufferSize);
    virtual bool GetCurrentGameLanguage(char* pchLanguage, int cchLanguage);
    virtual AppId_t GetInstalledDepots(AppId_t appID, DepotId_t* pvecDepots, uint32 cMaxDepots);
    virtual uint64 GetAppOwner();
    virtual const char* GetLaunchQueryParam(const char* pchKey);
    virtual bool GetDlcDownloadProgress(AppId_t appID, uint64* punBytesDownloaded, uint64* punBytesTotal);
    virtual int GetAppBuildId(AppId_t appID);
    virtual void RequestAppProofOfPurchaseKey(AppId_t appID);
    virtual bool GetFileDetails(const char* pszFileName, AppId_t appID, uint64* punFileSize, SHA1Digest_t* pFileSHA1, uint32* punFlags);
    virtual int GetLaunchCommandLine(int nAppID, char* pchCommandLine, int cubCommandLine);
    virtual bool BIsSubscribedApp(AppId_t appID);
    virtual bool BIsLowViolence();
    virtual bool BIsCybercafe();
    virtual bool BIsVACBanned();
    virtual const char* GetCurrentGameLanguage();
    virtual bool BIsSubscribedFromFreeWeekend();
    virtual int GetDLCCount();
    virtual bool BGetDLCDataByIndex(int iDLC, AppId_t* pAppID, bool* pbAvailable, char* pchName, int cchNameBufferSize);
    virtual void InstallDLC(AppId_t nAppID);
    virtual void UninstallDLC(AppId_t nAppID);
    virtual void RequestAppProofOfPurchaseKey(AppId_t nAppID);
    virtual bool GetCurrentBetaName(char* pchName, int cchNameBufferSize);
    virtual bool MarkContentCorrupt(bool bMissingFilesOnly);
    virtual uint32 GetInstalledDepots(AppId_t appID, DepotId_t* pvecDepots, uint32 cMaxDepots);
    virtual uint64 GetAppInstallDir(AppId_t appID, char* pchFolder, uint32 cMaxFolderBufferSize, uint32* punTimeStamp);
    virtual bool BIsAppInstalled(AppId_t appID);
    virtual CSteamID GetAppOwner();
    virtual const char* GetLaunchQueryParam(const char* pchKey);
    virtual bool GetDlcDownloadProgress(AppId_t appID, uint64* punBytesDownloaded, uint64* punBytesTotal);
    virtual int GetAppBuildId(AppId_t appID);
    virtual void RequestAppProofOfPurchaseKey(AppId_t appID);
    virtual bool GetFileDetails(const char* pszFileName, AppId_t appID, uint64* punFileSize, SHA1Digest_t* pFileSHA1, uint32* punFlags);
    virtual int GetLaunchCommandLine(int nAppID, char* pchCommandLine, int cubCommandLine);
    virtual bool BIsSubscribedApp(AppId_t appID);
    virtual bool BIsLowViolence();
    virtual bool BIsCybercafe();
    virtual bool BIsVACBanned();
    virtual const char* GetCurrentGameLanguage();
    virtual bool BIsSubscribedFromFreeWeekend();
    virtual int GetDLCCount();
    virtual bool BGetDLCDataByIndex(int iDLC, AppId_t* pAppID, bool* pbAvailable, char* pchName, int cchNameBufferSize);
    virtual void InstallDLC(AppId_t nAppID);
    virtual void UninstallDLC(AppId_t nAppID);
    virtual void RequestAppProofOfPurchaseKey(AppId_t nAppID);
    virtual bool GetCurrentBetaName(char* pchName, int cchNameBufferSize);
    virtual bool MarkContentCorrupt(bool bMissingFilesOnly);
    virtual uint32 GetInstalledDepots(AppId_t appID, DepotId_t* pvecDepots, uint32 cMaxDepots);
};
```

The critical functions that tools hook:
- `BIsAppInstalled()` - Returns true if app is installed
- `BIsSubscribedApp()` - Returns true if user owns/subscribes to app
- `GetInstalledDepots()` - Returns list of installed depot IDs
- `GetAppInstallDir()` - Returns installation directory

---

## API Hooking Mechanisms

### Method 1: Import Address Table (IAT) Hooking

**How it works:**
1. Windows PE executables have an Import Address Table
2. This table stores addresses of functions from DLLs
3. Hook replaces the address in the IAT with your function

```cpp
// Simplified IAT hooking concept
struct IMAGE_IMPORT_DESCRIPTOR {
    DWORD OriginalFirstThunk;
    DWORD TimeDateStamp;
    DWORD ForwarderChain;
    DWORD Name;
    DWORD FirstThunk;  // Points to array of function pointers
};

void HookViaIAT(HMODULE hModule, const char* dllName, const char* funcName, void* newFunc) {
    // Find IAT entry for steamclient.dll
    IMAGE_IMPORT_DESCRIPTOR* importDesc = FindImportDescriptor(hModule, dllName);
    
    // Find function in IAT
    void** funcPtr = FindFunctionInIAT(importDesc, funcName);
    
    // Save original
    void* originalFunc = *funcPtr;
    
    // Replace with hook (disable page protection first)
    DWORD oldProtect;
    VirtualProtect(funcPtr, sizeof(void*), PAGE_READWRITE, &oldProtect);
    *funcPtr = newFunc;
    VirtualProtect(funcPtr, sizeof(void*), oldProtect, &oldProtect);
    
    return originalFunc;
}
```

### Method 2: Detours / Function Patching

**How it works:**
1. Overwrite first bytes of function with JMP instruction
2. Jump to your hook function
3. Your hook calls original function (after restoring bytes)

```cpp
// x86-64 example
struct Hook {
    void* originalFunc;
    void* hookFunc;
    uint8_t originalBytes[14];  // Enough for JMP + address
    bool isHooked;
};

void InstallHook(void* targetFunc, void* hookFunc, Hook* hook) {
    hook->originalFunc = targetFunc;
    hook->hookFunc = hookFunc;
    
    // Save original bytes
    memcpy(hook->originalBytes, targetFunc, 14);
    
    // Create JMP instruction
    // x64: FF 25 00 00 00 00 [8-byte address]
    uint8_t jmpCode[14] = {
        0xFF, 0x25, 0x00, 0x00, 0x00, 0x00,  // JMP [RIP+0]
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00  // Address
    };
    
    // Set address to hook function
    *(uint64_t*)(jmpCode + 6) = (uint64_t)hookFunc;
    
    // Write hook
    DWORD oldProtect;
    VirtualProtect(targetFunc, 14, PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy(targetFunc, jmpCode, 14);
    VirtualProtect(targetFunc, 14, oldProtect, &oldProtect);
    
    hook->isHooked = true;
}

// Hooked function
bool Hooked_BIsAppInstalled(AppId_t appID) {
    // Check fake ownership first
    if (g_fakeOwnershipDB.IsOwned(appID)) {
        return true;
    }
    
    // Temporarily restore original function
    RestoreOriginalBytes(g_hook);
    
    // Call original
    bool result = ((bool(*)(AppId_t))g_hook->originalFunc)(appID);
    
    // Re-install hook
    InstallHook(g_hook->originalFunc, Hooked_BIsAppInstalled, g_hook);
    
    return result;
}
```

### Method 3: VTable Hooking (C++ Interfaces)

**How it works:**
1. C++ interfaces use virtual function tables (vtables)
2. Each object has a pointer to its vtable
3. Replace vtable entries with your functions

```cpp
// Steam uses COM-style interfaces
class ISteamApps {
public:
    virtual bool BIsAppInstalled(AppId_t appID) = 0;
    // ... more virtual functions
};

// Hook vtable
void HookVTable(ISteamApps* steamApps) {
    // Get vtable pointer (first member of object)
    void** vtable = *(void***)steamApps;
    
    // Save original
    void* originalBIsAppInstalled = vtable[0];  // Assuming index 0
    
    // Replace
    DWORD oldProtect;
    VirtualProtect(&vtable[0], sizeof(void*), PAGE_READWRITE, &oldProtect);
    vtable[0] = Hooked_BIsAppInstalled;
    VirtualProtect(&vtable[0], sizeof(void*), oldProtect, &oldProtect);
}
```

---

## Ownership Verification Flow

### Normal Steam Flow (Without Hooks)

```
Game Launch Request
    ↓
Steam Client
    ↓
ISteamApps::BIsSubscribedApp(appID)
    ↓
Steam Client checks:
    1. Local cache (appinfo.vdf)
    2. If not found → Steam Web API call
       GET https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/
    ↓
Steam Server Response:
    {
        "response": {
            "players": [{
                "steamid": "...",
                "gameid": "501",  // Currently playing
                "games": {
                    "owned": [500, 501, 502, ...]  // Owned games
                }
            }]
        }
    }
    ↓
Steam Client caches result locally
    ↓
If owned → Check installation
    ↓
If installed → Launch game
```

### Hooked Flow (With Tool)

```
Game Launch Request
    ↓
Steam Client
    ↓
ISteamApps::BIsSubscribedApp(appID)
    ↓
HOOK INTERCEPTS HERE
    ↓
Hook checks:
    1. Fake ownership database (from .lua)
    2. If found → Return TRUE immediately
    3. If not found → Call original function
    ↓
If hook returns TRUE:
    Steam thinks game is owned
    ↓
Steam checks installation:
    ISteamApps::BIsAppInstalled(appID)
    ↓
HOOK INTERCEPTS AGAIN
    ↓
Hook can return TRUE (fake installed)
    OR check if files actually exist
    ↓
If "installed" → Check depots
    ↓
ISteamApps::GetInstalledDepots(appID)
    ↓
HOOK INTERCEPTS
    ↓
Hook returns fake depot list from .lua
    ↓
Steam checks manifest IDs
    ↓
Hook provides manifest IDs from setManifestid()
    ↓
Steam downloads content using manifest
    ↓
Game launches
```

### Detailed Hook Implementation

```cpp
// Ownership database structure
struct FakeApp {
    AppId_t appID;
    bool isOwned;
    bool isInstalled;
    std::string depotKey;  // SHA-256 hash
    std::string manifestID;
    std::vector<DepotId_t> depots;
    std::string installPath;
};

class FakeOwnershipDB {
private:
    std::unordered_map<AppId_t, FakeApp> apps;
    
public:
    void AddApp(AppId_t appID, const std::string& depotKey = "") {
        FakeApp app;
        app.appID = appID;
        app.isOwned = true;
        app.isInstalled = false;  // Will be set when files exist
        app.depotKey = depotKey;
        apps[appID] = app;
    }
    
    void SetManifestID(AppId_t appID, const std::string& manifestID) {
        if (apps.find(appID) != apps.end()) {
            apps[appID].manifestID = manifestID;
        }
    }
    
    bool IsOwned(AppId_t appID) {
        auto it = apps.find(appID);
        return it != apps.end() && it->second.isOwned;
    }
    
    bool IsInstalled(AppId_t appID) {
        auto it = apps.find(appID);
        if (it == apps.end()) return false;
        
        // Check if files actually exist
        if (!it->second.installPath.empty()) {
            return std::filesystem::exists(it->second.installPath);
        }
        
        return it->second.isInstalled;
    }
    
    std::string GetDepotKey(AppId_t appID) {
        auto it = apps.find(appID);
        return (it != apps.end()) ? it->second.depotKey : "";
    }
    
    std::string GetManifestID(AppId_t appID) {
        auto it = apps.find(appID);
        return (it != apps.end()) ? it->second.manifestID : "";
    }
};

// Global instance
FakeOwnershipDB g_fakeDB;

// Hook implementations
bool WINAPI Hooked_BIsSubscribedApp(AppId_t appID) {
    // Check fake database first
    if (g_fakeDB.IsOwned(appID)) {
        return true;
    }
    
    // Call original function
    typedef bool (WINAPI *OriginalFunc)(AppId_t);
    OriginalFunc original = (OriginalFunc)g_originalBIsSubscribedApp;
    return original(appID);
}

bool WINAPI Hooked_BIsAppInstalled(AppId_t appID) {
    if (g_fakeDB.IsOwned(appID)) {
        // Return true if files exist, or if we want to fake it
        return g_fakeDB.IsInstalled(appID) || g_fakeDB.GetManifestID(appID) != "";
    }
    
    typedef bool (WINAPI *OriginalFunc)(AppId_t);
    OriginalFunc original = (OriginalFunc)g_originalBIsAppInstalled;
    return original(appID);
}
```

---

## Content Delivery System

### Steam CDN Architecture

```
Steam Client
    ↓
Content Server Selection
    ↓
cdn.steamcontent.com / cdn[1-5].steamcontent.com
    ↓
Request: GET /depot/<depotID>/chunk/<chunkID>
    Headers:
        - If-None-Match: <etag>
        - Range: bytes=0-1048575
    ↓
CDN responds with:
    - Encrypted chunk data
    - Content-Length
    - ETag for caching
    ↓
Steam Client receives chunk
    ↓
Decrypts using depot key
    ↓
Validates checksum
    ↓
Writes to disk
```

### Manifest Structure

Manifests are stored in binary format but can be parsed:

```
Manifest Header:
- Magic number (identifies format)
- Version
- Depot ID
- Manifest ID
- Creation time
- File count

File Entries:
For each file:
- File path (relative to game directory)
- File size
- File flags (executable, etc.)
- SHA-1 hash
- Chunk list:
  - Chunk ID
  - Chunk size
  - Chunk SHA-1

Chunk Mapping:
- Maps chunks to CDN locations
- Compression info
- Encryption info
```

### How Tools Use Manifests

```cpp
// When Steam requests manifest
ManifestID_t GetManifestForDepot(DepotId_t depotID, AppId_t appID) {
    // Hook intercepts this
    std::string manifestID = g_fakeDB.GetManifestID(appID);
    
    if (!manifestID.empty()) {
        // Convert string to ManifestID_t (uint64)
        return std::stoull(manifestID);
    }
    
    // Call original
    return Original_GetManifestForDepot(depotID, appID);
}

// Manifest download hook
bool DownloadManifest(ManifestID_t manifestID, void* buffer, size_t* size) {
    // Steam requests manifest from content server
    // URL: https://cdn.steamcontent.com/depot/<depotID>/manifest/<manifestID>
    
    // Tool can:
    // 1. Let Steam download it normally (if valid manifest ID)
    // 2. Intercept and modify it
    // 3. Provide cached manifest
    
    return Original_DownloadManifest(manifestID, buffer, size);
}
```

---

## Manifest System Deep Dive

### Manifest File Format (Simplified)

```
struct ManifestHeader {
    uint32 magic;           // 0x07 0x44 0x53 0x54 (DST)
    uint32 version;         // Format version
    DepotId_t depotID;      // Which depot this is for
    ManifestID_t manifestID; // Unique manifest ID
    uint64 creationTime;    // Unix timestamp
    uint32 fileCount;       // Number of files
    uint32 chunkCount;      // Number of chunks
};

struct FileEntry {
    char fileName[260];     // File path
    uint64 fileSize;        // Total file size
    uint32 fileFlags;       // Executable, etc.
    SHA1Digest_t fileHash;  // SHA-1 of entire file
    uint32 chunkCount;      // Number of chunks
    ChunkEntry chunks[];    // Chunk list
};

struct ChunkEntry {
    ChunkID_t chunkID;      // Unique chunk ID
    uint32 chunkSize;       // Size of chunk
    SHA1Digest_t chunkHash; // SHA-1 of chunk
    uint32 compressionType; // Compression method
};

struct ChunkMapping {
    ChunkID_t chunkID;
    uint64 offset;          // Offset in depot file
    uint32 size;
    uint32 compressedSize;
};
```

### Manifest ID Resolution

```
User wants to play AppID 501
    ↓
Tool's setManifestid(501, "8134324683205569669")
    ↓
Steam: "What depots does AppID 501 need?"
    ↓
Hook: Returns depot list (from appinfo or fake data)
    ↓
Steam: "What manifest ID for depot X?"
    ↓
Hook: Returns "8134324683205569669"
    ↓
Steam downloads manifest from CDN:
    GET /depot/<depotID>/manifest/8134324683205569669
    ↓
CDN responds with manifest binary
    ↓
Steam parses manifest:
    - Gets list of files
    - Gets chunk IDs for each file
    - Gets chunk locations on CDN
    ↓
Steam downloads chunks:
    GET /depot/<depotID>/chunk/<chunkID>
    ↓
Chunks are encrypted
    ↓
Steam decrypts using depot key
    ↓
Steam assembles files from chunks
    ↓
Files written to disk
```

### Why Manifest IDs Work

Manifest IDs are **content-agnostic** - Steam's CDN serves content based on manifest ID, not ownership:

1. **CDN doesn't verify ownership** - It's a content delivery network
2. **Manifest IDs are public** - They're just version identifiers
3. **Depot keys are the real protection** - Without the key, content is useless

However, getting valid manifest IDs and depot keys requires:
- Access to Steam's internal APIs (requires account with game)
- Reverse engineering Steam client
- Or obtaining them from other sources

---

## Depot Encryption System

### Depot Key Format

The hex strings in `addappid()` are **SHA-256 hashes**:

```
"7a0b21eed084464fd2efb03ecc44116224b150f9377551ca7901ead966f21c26"
```

This is 64 hex characters = 32 bytes = 256 bits = SHA-256 output

### Encryption Process

```
Original File Data
    ↓
Split into chunks (typically 1MB)
    ↓
Each chunk encrypted with AES-256
    Key: Derived from depot key + chunk ID
    ↓
Encrypted chunks stored on CDN
    ↓
Manifest contains:
    - Chunk IDs
    - Encrypted chunk hashes
    - But NOT the decryption keys
```

### Decryption Process

```
Download encrypted chunk from CDN
    ↓
Get depot key (from addappid() call)
    ↓
Derive decryption key:
    key = SHA256(depot_key + chunk_id + salt)
    ↓
Decrypt chunk using AES-256
    ↓
Verify chunk hash matches manifest
    ↓
If valid → Use chunk
If invalid → Re-download or fail
```

### Key Derivation (Simplified)

```cpp
std::vector<uint8_t> DeriveChunkKey(
    const std::string& depotKeyHex,
    ChunkID_t chunkID
) {
    // Convert hex depot key to bytes
    std::vector<uint8_t> depotKey = HexToBytes(depotKeyHex);
    
    // Combine with chunk ID
    std::vector<uint8_t> input;
    input.insert(input.end(), depotKey.begin(), depotKey.end());
    
    uint64_t chunkIDBE = SwapEndian(chunkID);  // Big-endian
    input.insert(input.end(), 
                 (uint8_t*)&chunkIDBE, 
                 (uint8_t*)&chunkIDBE + sizeof(chunkIDBE));
    
    // SHA-256 hash to get final key
    return SHA256(input);
}

void DecryptChunk(
    const std::vector<uint8_t>& encryptedChunk,
    const std::string& depotKeyHex,
    ChunkID_t chunkID,
    std::vector<uint8_t>& decryptedChunk
) {
    std::vector<uint8_t> key = DeriveChunkKey(depotKeyHex, chunkID);
    
    // AES-256 decryption
    AESDecrypt(encryptedChunk, key, decryptedChunk);
}
```

### Why Depot Keys Are Critical

Without the correct depot key:
- Downloaded chunks are encrypted gibberish
- Cannot decrypt and verify chunks
- Game files cannot be assembled
- Game won't launch

The depot key is essentially the "password" for the game's content. Steam only provides it to:
- Users who own the game
- Through encrypted communication
- Tied to account ownership

Tools obtain depot keys through:
1. Extracting from legitimate Steam client (when you own the game)
2. Sharing between users (risky, may be account-specific)
3. Reverse engineering Steam's key distribution

---

## Implementation Details

### DLL Injection Process

```cpp
// Step-by-step injection
bool InjectDLL(DWORD processID, const char* dllPath) {
    // 1. Open target process
    HANDLE hProcess = OpenProcess(
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION |
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
        FALSE, processID
    );
    if (!hProcess) return false;
    
    // 2. Allocate memory in target process
    size_t pathLen = strlen(dllPath) + 1;
    LPVOID pRemoteMem = VirtualAllocEx(
        hProcess, NULL, pathLen,
        MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
    );
    if (!pRemoteMem) {
        CloseHandle(hProcess);
        return false;
    }
    
    // 3. Write DLL path to remote memory
    if (!WriteProcessMemory(
        hProcess, pRemoteMem, dllPath, pathLen, NULL
    )) {
        VirtualFreeEx(hProcess, pRemoteMem, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }
    
    // 4. Get address of LoadLibraryA
    HMODULE hKernel32 = GetModuleHandleA("kernel32.dll");
    LPTHREAD_START_ROUTINE pLoadLibrary = 
        (LPTHREAD_START_ROUTINE)GetProcAddress(hKernel32, "LoadLibraryA");
    
    // 5. Create remote thread to load DLL
    HANDLE hThread = CreateRemoteThread(
        hProcess, NULL, 0,
        pLoadLibrary, pRemoteMem,
        0, NULL
    );
    if (!hThread) {
        VirtualFreeEx(hProcess, pRemoteMem, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }
    
    // 6. Wait for thread to complete
    WaitForSingleObject(hThread, INFINITE);
    
    // 7. Cleanup
    CloseHandle(hThread);
    VirtualFreeEx(hProcess, pRemoteMem, 0, MEM_RELEASE);
    CloseHandle(hProcess);
    
    return true;
}
```

### Lua Script Parser

```cpp
class LuaScriptParser {
private:
    FakeOwnershipDB* db;
    
    // Regex patterns
    std::regex addAppIDRegex{
        R"(addappid\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*,\s*["']?([a-fA-F0-9]{64})["']?)?\s*\))"
    };
    std::regex setManifestRegex{
        R"(setManifestid\s*\(\s*(\d+)\s*,\s*["']?([0-9]+)["']?\s*\))"
    };
    
public:
    LuaScriptParser(FakeOwnershipDB* database) : db(database) {}
    
    bool ParseFile(const std::string& filename) {
        std::ifstream file(filename);
        if (!file.is_open()) {
            return false;
        }
        
        std::string line;
        int lineNum = 0;
        
        while (std::getline(file, line)) {
            lineNum++;
            
            // Remove comments
            size_t commentPos = line.find("--");
            if (commentPos != std::string::npos) {
                line = line.substr(0, commentPos);
            }
            
            // Trim whitespace
            line = Trim(line);
            if (line.empty()) continue;
            
            // Parse addappid
            std::smatch match;
            if (std::regex_match(line, match, addAppIDRegex)) {
                AppId_t appID = std::stoul(match[1].str());
                int flags = match[2].matched ? std::stoi(match[2].str()) : 0;
                std::string depotKey = match[3].matched ? match[3].str() : "";
                
                db->AddApp(appID, depotKey);
                continue;
            }
            
            // Parse setManifestid
            if (std::regex_match(line, match, setManifestRegex)) {
                AppId_t appID = std::stoul(match[1].str());
                std::string manifestID = match[2].str();
                
                db->SetManifestID(appID, manifestID);
                continue;
            }
        }
        
        return true;
    }
    
private:
    std::string Trim(const std::string& str) {
        size_t first = str.find_first_not_of(" \t\n\r");
        if (first == std::string::npos) return "";
        size_t last = str.find_last_not_of(" \t\n\r");
        return str.substr(first, (last - first + 1));
    }
};
```

### Hook Installation on Steam Startup

```cpp
// DLL Entry Point
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
        // Initialize when DLL is loaded
        DisableThreadLibraryCalls(hModule);
        
        // Create thread to avoid blocking Steam startup
        CreateThread(NULL, 0, InitializeHooks, hModule, 0, NULL);
        break;
        
    case DLL_PROCESS_DETACH:
        // Cleanup on unload
        UninstallHooks();
        break;
    }
    return TRUE;
}

DWORD WINAPI InitializeHooks(LPVOID lpParam) {
    // Wait for Steam to fully initialize
    Sleep(2000);
    
    // Load Lua script
    LuaScriptParser parser(&g_fakeDB);
    parser.ParseFile("unlock.lua");
    
    // Get Steam module
    HMODULE hSteamClient = GetModuleHandleA("steamclient.dll");
    if (!hSteamClient) {
        return 1;
    }
    
    // Get function addresses
    void* pBIsSubscribedApp = GetProcAddress(hSteamClient, "SteamAPI_ISteamApps_BIsSubscribedApp");
    void* pBIsAppInstalled = GetProcAddress(hSteamClient, "SteamAPI_ISteamApps_BIsAppInstalled");
    // ... more functions
    
    // Install hooks
    InstallHook(pBIsSubscribedApp, Hooked_BIsSubscribedApp, &g_hookBIsSubscribedApp);
    InstallHook(pBIsAppInstalled, Hooked_BIsAppInstalled, &g_hookBIsAppInstalled);
    // ... more hooks
    
    return 0;
}
```

### Memory Protection Bypass

```cpp
// Steam may have memory protection - need to bypass
bool BypassMemoryProtection(void* address, size_t size) {
    DWORD oldProtect;
    
    // Change protection to allow writing
    if (!VirtualProtect(address, size, PAGE_EXECUTE_READWRITE, &oldProtect)) {
        return false;
    }
    
    // Also need to flush instruction cache (for code modifications)
    FlushInstructionCache(GetCurrentProcess(), address, size);
    
    return true;
}

// Restore protection
bool RestoreMemoryProtection(void* address, size_t size, DWORD originalProtect) {
    DWORD dummy;
    return VirtualProtect(address, size, originalProtect, &dummy);
}
```

---

## Advanced Techniques

### Bypassing VAC Detection

VAC (Valve Anti-Cheat) can detect:
- Modified Steam processes
- Injected DLLs
- Hooked functions

**Evasion techniques** (for educational understanding):

1. **Hide DLL from module list**
   ```cpp
   // Remove DLL from PEB (Process Environment Block)
   // Makes it invisible to module enumeration
   ```

2. **Hook at lower level**
   ```cpp
   // Hook kernel-level functions instead of user-level
   // Harder to detect
   ```

3. **Legitimate-looking hooks**
   ```cpp
   // Make hooks look like legitimate Steam code
   // Match calling conventions exactly
   ```

4. **Timing attacks**
   ```cpp
   // Add delays to avoid pattern detection
   // Randomize hook behavior
   ```

### Handling Steam Updates

Steam updates can break hooks:

```cpp
// Version detection
struct SteamVersion {
    uint32 major;
    uint32 minor;
    uint32 build;
};

SteamVersion GetSteamVersion() {
    // Read from steam.dll version info
    // Or from registry
    // Or from file timestamps
}

// Hook compatibility check
bool IsHookCompatible(SteamVersion version) {
    // Check if hooks work with this version
    // May need different offsets for different versions
    return version.major == 3 && version.minor >= 0;
}

// Auto-update hook offsets
void UpdateHookOffsets(SteamVersion version) {
    // Different Steam versions have different function addresses
    // Need to recalculate offsets
}
```

---

## Security Implications

### Why This Works

1. **Client-side trust**: Steam client trusts its own API responses
2. **Offline capability**: Many checks happen offline
3. **CDN accessibility**: Content servers don't verify ownership
4. **Legacy architecture**: Steam's architecture predates modern security practices

### Why It's Risky

1. **VAC detection**: Can result in permanent ban
2. **Account termination**: Violates Terms of Service
3. **Legal issues**: May violate copyright laws
4. **Malware risk**: Such tools often contain malware
5. **Game updates**: Updates can break functionality

### Detection Methods

**Server-side:**
- Online play requires server verification
- Achievements/leaderboards check ownership
- Cloud saves verify account
- Purchase verification for online features

**Client-side:**
- VAC scans process memory
- Checksums of Steam files
- Behavioral analysis
- Module enumeration

---

## Conclusion

Steam unlocking tools work by:

1. **Injecting a DLL** into the Steam process
2. **Hooking API functions** that check ownership
3. **Returning fake data** from a database built from `.lua` scripts
4. **Providing manifest IDs** so Steam knows what to download
5. **Supplying depot keys** so Steam can decrypt content

The `.lua` scripts are essentially configuration files that tell the tool:
- Which AppIDs to fake ownership for
- What manifest IDs to use
- What depot keys to provide

This is a **client-side attack** on Steam's trust model - it doesn't hack Steam's servers, but rather makes the Steam client believe false information about game ownership.

**Important**: This information is for educational and security research purposes only. Using such tools violates Steam's Terms of Service and can result in permanent account bans.
