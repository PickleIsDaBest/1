# In-Depth Technical Example: Steam Unlocking Mechanism

## Table of Contents
1. [Complete DLL Injection Process](#complete-dll-injection-process)
2. [Detailed Hook Implementation](#detailed-hook-implementation)
3. [Steam API Structures](#steam-api-structures)
4. [Lua Script Interpreter](#lua-script-interpreter)
5. [Memory Management](#memory-management)
6. [Complete Execution Flow](#complete-execution-flow)
7. [Real-World Code Examples](#real-world-code-examples)

---

## Complete DLL Injection Process

### Step 1: Process Enumeration

```cpp
// Finding Steam process
DWORD FindSteamProcess() {
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32 pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32);
    
    if (Process32First(hSnapshot, &pe32)) {
        do {
            if (_wcsicmp(pe32.szExeFile, L"steam.exe") == 0) {
                CloseHandle(hSnapshot);
                return pe32.th32ProcessID;
            }
        } while (Process32Next(hSnapshot, &pe32));
    }
    CloseHandle(hSnapshot);
    return 0;
}
```

### Step 2: DLL Injection via CreateRemoteThread

```cpp
bool InjectDLL(DWORD processId, const char* dllPath) {
    // Open target process
    HANDLE hProcess = OpenProcess(
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION |
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
        FALSE, processId
    );
    
    if (!hProcess) return false;
    
    // Calculate DLL path length
    size_t pathLen = strlen(dllPath) + 1;
    
    // Allocate memory in target process
    LPVOID pRemoteMemory = VirtualAllocEx(
        hProcess,
        NULL,
        pathLen,
        MEM_COMMIT | MEM_RESERVE,
        PAGE_READWRITE
    );
    
    if (!pRemoteMemory) {
        CloseHandle(hProcess);
        return false;
    }
    
    // Write DLL path to remote memory
    if (!WriteProcessMemory(hProcess, pRemoteMemory, dllPath, pathLen, NULL)) {
        VirtualFreeEx(hProcess, pRemoteMemory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }
    
    // Get LoadLibraryA address (same in all processes)
    HMODULE hKernel32 = GetModuleHandleA("kernel32.dll");
    LPTHREAD_START_ROUTINE pLoadLibrary = (LPTHREAD_START_ROUTINE)
        GetProcAddress(hKernel32, "LoadLibraryA");
    
    // Create remote thread to load DLL
    HANDLE hThread = CreateRemoteThread(
        hProcess,
        NULL,
        0,
        pLoadLibrary,
        pRemoteMemory,
        0,
        NULL
    );
    
    if (hThread) {
        WaitForSingleObject(hThread, INFINITE);
        CloseHandle(hThread);
    }
    
    VirtualFreeEx(hProcess, pRemoteMemory, 0, MEM_RELEASE);
    CloseHandle(hProcess);
    return hThread != NULL;
}
```

### Step 3: DLL Entry Point

```cpp
// In the injected DLL
BOOL APIENTRY DllMain(HMODULE hModule, DWORD dwReason, LPVOID lpReserved) {
    if (dwReason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
        
        // Initialize hook system
        InitializeHooks();
        
        // Load and parse Lua script
        LoadLuaScript("steamtools.lua");
        
        // Create thread for hook maintenance
        CreateThread(NULL, 0, HookMaintenanceThread, NULL, 0, NULL);
    }
    return TRUE;
}
```

---

## Detailed Hook Implementation

### Hook Installation Using Microsoft Detours

```cpp
#include <detours.h>

// Function pointers to original Steam API functions
typedef bool (WINAPI *BIsAppInstalled_t)(AppId_t appID);
typedef bool (WINAPI *BIsDlcInstalled_t)(AppId_t appID, AppId_t dlcAppID);
typedef int (WINAPI *GetAppInstallState_t)(AppId_t appID);
typedef uint64 (WINAPI *GetManifestId_t)(AppId_t appID, DepotId_t depotID);

BIsAppInstalled_t Original_BIsAppInstalled = NULL;
BIsDlcInstalled_t Original_BIsDlcInstalled = NULL;
GetAppInstallState_t Original_GetAppInstallState = NULL;
GetManifestId_t Original_GetManifestId = NULL;

// Data structures for fake ownership
struct FakeApp {
    AppId_t appID;
    uint64 manifestID;
    char depotKey[65];  // SHA-256 hex string (64 chars + null)
    bool hasDepotKey;
};

std::unordered_map<AppId_t, FakeApp> g_fakeApps;
std::mutex g_fakeAppsMutex;

// Hooked function implementations
bool WINAPI Hooked_BIsAppInstalled(AppId_t appID) {
    std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
    
    // Check if this AppID is in our fake list
    if (g_fakeApps.find(appID) != g_fakeApps.end()) {
        return true;  // Lie: "Yes, this app is installed!"
    }
    
    // Otherwise, call original function
    if (Original_BIsAppInstalled) {
        return Original_BIsAppInstalled(appID);
    }
    return false;
}

bool WINAPI Hooked_BIsDlcInstalled(AppId_t appID, AppId_t dlcAppID) {
    std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
    
    // Check if DLC is in our fake list
    if (g_fakeApps.find(dlcAppID) != g_fakeApps.end()) {
        return true;
    }
    
    if (Original_BIsDlcInstalled) {
        return Original_BIsDlcInstalled(appID, dlcAppID);
    }
    return false;
}

int WINAPI Hooked_GetAppInstallState(AppId_t appID) {
    std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
    
    if (g_fakeApps.find(appID) != g_fakeApps.end()) {
        // Return k_EAppInstallState_Installed
        return 1;
    }
    
    if (Original_GetAppInstallState) {
        return Original_GetAppInstallState(appID);
    }
    return 0;  // k_EAppInstallState_NotInstalled
}

uint64 WINAPI Hooked_GetManifestId(AppId_t appID, DepotId_t depotID) {
    std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
    
    auto it = g_fakeApps.find(appID);
    if (it != g_fakeApps.end() && it->second.manifestID != 0) {
        return it->second.manifestID;
    }
    
    if (Original_GetManifestId) {
        return Original_GetManifestId(appID, depotID);
    }
    return 0;
}
```

### Manual Hook Installation (Alternative Method)

```cpp
// Without using Detours library - manual patching
struct HookInfo {
    void* originalFunction;
    void* hookFunction;
    unsigned char originalBytes[5];  // Save original bytes
    bool isHooked;
};

bool InstallHook(void* targetFunction, void* hookFunction, HookInfo& info) {
    DWORD oldProtect;
    
    // Make memory writable
    if (!VirtualProtect(targetFunction, 5, PAGE_EXECUTE_READWRITE, &oldProtect)) {
        return false;
    }
    
    // Save original bytes
    memcpy(info.originalBytes, targetFunction, 5);
    
    // Calculate relative jump offset
    // jmp [relative offset] = E9 [4-byte offset]
    intptr_t offset = (intptr_t)hookFunction - ((intptr_t)targetFunction + 5);
    
    // Write jump instruction
    unsigned char jmpInstruction[5];
    jmpInstruction[0] = 0xE9;  // JMP opcode
    *(int32_t*)(jmpInstruction + 1) = (int32_t)offset;
    
    // Write to target function
    memcpy(targetFunction, jmpInstruction, 5);
    
    // Restore protection
    VirtualProtect(targetFunction, 5, oldProtect, &oldProtect);
    
    info.originalFunction = targetFunction;
    info.hookFunction = hookFunction;
    info.isHooked = true;
    
    return true;
}

// Trampoline function to call original
bool Trampoline_BIsAppInstalled(AppId_t appID) {
    // Restore original bytes temporarily
    HookInfo& info = g_hookInfo_BIsAppInstalled;
    DWORD oldProtect;
    VirtualProtect(info.originalFunction, 5, PAGE_EXECUTE_READWRITE, &oldProtect);
    memcpy(info.originalFunction, info.originalBytes, 5);
    
    // Call original function
    bool result = ((BIsAppInstalled_t)info.originalFunction)(appID);
    
    // Reinstall hook
    InstallHook(info.originalFunction, Hooked_BIsAppInstalled, info);
    VirtualProtect(info.originalFunction, 5, oldProtect, &oldProtect);
    
    return result;
}
```

### Finding Steam API Functions

```cpp
// Steam API is accessed through interfaces
// We need to find the ISteamApps interface

struct ISteamApps {
    virtual bool BIsAppInstalled(AppId_t appID) = 0;
    virtual bool BIsDlcInstalled(AppId_t appID, AppId_t dlcAppID) = 0;
    virtual int GetAppInstallState(AppId_t appID) = 0;
    virtual uint64 GetManifestId(AppId_t appID, DepotId_t depotID) = 0;
    // ... more virtual functions
};

// Steam client interface
struct ISteamClient {
    virtual void* GetISteamApps(HSteamUser hSteamUser, HSteamPipe hSteamPipe, const char* version) = 0;
    // ... more virtual functions
};

ISteamApps* GetSteamAppsInterface() {
    // SteamAPI_Init() creates the client
    // We hook after Steam initializes
    
    typedef ISteamClient* (*SteamClient_t)();
    typedef ISteamApps* (*SteamApps_t)(HSteamUser, HSteamPipe, const char*);
    
    // Get SteamClient function
    HMODULE hSteamAPI = GetModuleHandleA("steam_api.dll");
    if (!hSteamAPI) return NULL;
    
    SteamClient_t SteamClient = (SteamClient_t)GetProcAddress(hSteamAPI, "SteamClient");
    if (!SteamClient) return NULL;
    
    ISteamClient* pSteamClient = SteamClient();
    if (!pSteamClient) return NULL;
    
    // Get ISteamApps interface
    HSteamUser hSteamUser = SteamAPI_GetHSteamUser();
    HSteamPipe hSteamPipe = SteamAPI_GetHSteamPipe();
    
    ISteamApps* pSteamApps = (ISteamApps*)pSteamClient->GetISteamApps(
        hSteamUser, hSteamPipe, STEAMAPPS_INTERFACE_VERSION
    );
    
    return pSteamApps;
}

void InitializeHooks() {
    ISteamApps* pSteamApps = GetSteamAppsInterface();
    if (!pSteamApps) return;
    
    // Get vtable (virtual function table)
    void** vtable = *(void***)pSteamApps;
    
    // Hook vtable entries
    // vtable[0] = BIsAppInstalled
    // vtable[1] = BIsDlcInstalled
    // etc.
    
    DWORD oldProtect;
    VirtualProtect(&vtable[0], sizeof(void*), PAGE_READWRITE, &oldProtect);
    
    Original_BIsAppInstalled = (BIsAppInstalled_t)vtable[0];
    vtable[0] = (void*)Hooked_BIsAppInstalled;
    
    Original_BIsDlcInstalled = (BIsDlcInstalled_t)vtable[1];
    vtable[1] = (void*)Hooked_BIsDlcInstalled;
    
    VirtualProtect(&vtable[0], sizeof(void*), oldProtect, &oldProtect);
}
```

---

## Steam API Structures

### AppID and Manifest Structures

```cpp
typedef uint32 AppId_t;
typedef uint32 DepotId_t;

// Steam manifest structure (simplified)
struct ManifestEntry {
    char filename[260];
    uint64 size;
    uint32 flags;
    uint32 crc;
    uint64 chunksOffset;
    uint32 chunksCount;
};

struct DepotManifest {
    uint32 magic;  // "VSMD" = 0x444D5356
    uint32 version;
    DepotId_t depotID;
    uint64 manifestGID;  // This is what setManifestid() sets
    uint32 creationTime;
    uint32 fileCount;
    ManifestEntry files[];
};

// Depot key structure
struct DepotKey {
    AppId_t appID;
    DepotId_t depotID;
    unsigned char key[32];  // 256-bit key (SHA-256)
};
```

### Content Server Communication

```cpp
// When Steam downloads content, it queries content servers
struct ContentServerRequest {
    uint32 protocolVersion;
    uint32 messageType;  // k_EMsgClientGetDepotDecryptionKey
    AppId_t appID;
    DepotId_t depotID;
};

struct ContentServerResponse {
    uint32 result;
    DepotId_t depotID;
    unsigned char depotKey[32];
    uint64 manifestGID;
};

// Hook the content server communication
bool Hooked_GetDepotDecryptionKey(AppId_t appID, DepotId_t depotID, 
                                   unsigned char* keyOut, uint32 keyOutLen) {
    std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
    
    auto it = g_fakeApps.find(appID);
    if (it != g_fakeApps.end() && it->second.hasDepotKey) {
        // Convert hex string to binary
        HexStringToBinary(it->second.depotKey, keyOut, 32);
        return true;
    }
    
    // Call original
    if (Original_GetDepotDecryptionKey) {
        return Original_GetDepotDecryptionKey(appID, depotID, keyOut, keyOutLen);
    }
    return false;
}
```

---

## Lua Script Interpreter

### Complete Lua Parser Implementation

```cpp
#include <regex>
#include <fstream>
#include <sstream>

void HexStringToBinary(const char* hex, unsigned char* out, size_t len) {
    for (size_t i = 0; i < len; i++) {
        char hexByte[3] = {hex[i*2], hex[i*2+1], 0};
        out[i] = (unsigned char)strtoul(hexByte, NULL, 16);
    }
}

uint64 ParseManifestID(const std::string& str) {
    return std::stoull(str);
}

void ParseLuaScript(const std::string& filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        return;
    }
    
    std::string line;
    int lineNum = 0;
    
    std::regex addAppRegex(
        R"(addappid\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*,\s*["']?([a-fA-F0-9]{64})["']?)?\s*\))"
    );
    
    std::regex manifestRegex(
        R"(setManifestid\s*\(\s*(\d+)\s*,\s*["']?(\d+)["']?\s*\))"
    );
    
    while (std::getline(file, line)) {
        lineNum++;
        
        // Remove comments
        size_t commentPos = line.find("--");
        if (commentPos != std::string::npos) {
            line = line.substr(0, commentPos);
        }
        
        // Trim whitespace
        line.erase(0, line.find_first_not_of(" \t\r\n"));
        line.erase(line.find_last_not_of(" \t\r\n") + 1);
        
        if (line.empty()) continue;
        
        std::smatch match;
        
        // Parse addappid()
        if (std::regex_match(line, match, addAppRegex)) {
            AppId_t appID = std::stoul(match[1].str());
            int flags = match[2].matched ? std::stoi(match[2].str()) : 0;
            std::string depotKey = match[3].matched ? match[3].str() : "";
            
            std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
            
            FakeApp& app = g_fakeApps[appID];
            app.appID = appID;
            app.manifestID = 0;  // Will be set by setManifestid()
            
            if (!depotKey.empty()) {
                if (depotKey.length() == 64) {
                    strncpy_s(app.depotKey, depotKey.c_str(), 64);
                    app.hasDepotKey = true;
                }
            }
            
            printf("[Lua] Added AppID %u (flags=%d, hasKey=%s)\n", 
                   appID, flags, app.hasDepotKey ? "yes" : "no");
        }
        // Parse setManifestid()
        else if (std::regex_match(line, match, manifestRegex)) {
            AppId_t appID = std::stoul(match[1].str());
            uint64 manifestID = ParseManifestID(match[2].str());
            
            std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
            
            auto it = g_fakeApps.find(appID);
            if (it != g_fakeApps.end()) {
                it->second.manifestID = manifestID;
                printf("[Lua] Set manifest for AppID %u: %llu\n", appID, manifestID);
            } else {
                // AppID not added yet, create entry
                FakeApp& app = g_fakeApps[appID];
                app.appID = appID;
                app.manifestID = manifestID;
                app.hasDepotKey = false;
                printf("[Lua] Created AppID %u with manifest %llu\n", appID, manifestID);
            }
        }
    }
    
    file.close();
    
    printf("[Lua] Loaded %zu fake apps\n", g_fakeApps.size());
}
```

### Example Lua Script Processing

```cpp
// Input Lua script:
/*
addappid(500)
addappid(1660740)
addappid(501, 0, "7a0b21eed084464fd2efb03ecc44116224b150f9377551ca7901ead966f21c26")
setManifestid(501, "8134324683205569669")
*/

// After parsing, g_fakeApps contains:
/*
g_fakeApps[500] = {
    appID: 500,
    manifestID: 0,
    depotKey: "",
    hasDepotKey: false
}

g_fakeApps[1660740] = {
    appID: 1660740,
    manifestID: 0,
    depotKey: "",
    hasDepotKey: false
}

g_fakeApps[501] = {
    appID: 501,
    manifestID: 8134324683205569669,
    depotKey: "7a0b21eed084464fd2efb03ecc44116224b150f9377551ca7901ead966f21c26",
    hasDepotKey: true
}
*/
```

---

## Memory Management

### Memory Layout in Steam Process

```
Steam Process Address Space (simplified):
┌─────────────────────────────────────────┐
│ 0x00400000 - Steam.exe                 │
│  - Main executable code                │
│  - Original Steam API functions        │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ 0x10000000 - steam_api.dll             │
│  - ISteamApps vtable                   │
│  - Original function implementations    │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ 0x20000000 - Injected Hook DLL         │
│  - Hooked function implementations      │
│  - Lua parser                           │
│  - g_fakeApps map                      │
│  - Thread local storage                │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ 0x30000000 - Heap (allocated memory)   │
│  - Game manifests                      │
│  - Depot keys cache                    │
│  - File download buffers               │
└─────────────────────────────────────────┘
```

### Thread Safety

```cpp
// Critical sections for thread-safe access
std::mutex g_fakeAppsMutex;
std::mutex g_hookMutex;

// Steam may call hooks from multiple threads
DWORD WINAPI HookMaintenanceThread(LPVOID lpParam) {
    while (true) {
        Sleep(1000);
        
        // Verify hooks are still installed
        std::lock_guard<std::mutex> lock(g_hookMutex);
        VerifyHooksInstalled();
        
        // Log statistics
        {
            std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
            printf("[Hook] Active fake apps: %zu\n", g_fakeApps.size());
        }
    }
    return 0;
}
```

---

## Complete Execution Flow

### Detailed Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Injection                                          │
└─────────────────────────────────────────────────────────────┘

1. User launches SteamTools/GreenLuma
   ↓
2. Tool enumerates processes: FindSteamProcess()
   ↓
3. Tool injects DLL: InjectDLL(steamPID, "hook.dll")
   ↓
4. DLL loads in Steam process: DllMain() called
   ↓
5. DLL initializes: InitializeHooks() called

┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Hook Installation                                 │
└─────────────────────────────────────────────────────────────┘

6. Get Steam API interface: GetSteamAppsInterface()
   ↓
7. Locate vtable: *(void***)pSteamApps
   ↓
8. Save original function pointers
   ↓
9. Replace vtable entries with hook functions
   ↓
10. Hooks are now active

┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Lua Script Loading                                │
└─────────────────────────────────────────────────────────────┘

11. DLL reads "steamtools.lua" file
    ↓
12. Parse each line with regex
    ↓
13. For each addappid():
    - Create FakeApp entry
    - Store AppID
    - Store depot key (if provided)
    ↓
14. For each setManifestid():
    - Find existing FakeApp entry
    - Set manifestID
    ↓
15. g_fakeApps map populated

┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: Game Launch Attempt                               │
└─────────────────────────────────────────────────────────────┘

16. User double-clicks game in Steam library
    ↓
17. Steam calls: pSteamApps->BIsAppInstalled(501)
    ↓
18. Hook intercepts: Hooked_BIsAppInstalled(501)
    ↓
19. Hook checks: g_fakeApps.find(501) != g_fakeApps.end()
    ↓
20. Hook returns: TRUE (fake ownership)
    ↓
21. Steam thinks: "User owns this game, proceed"

┌─────────────────────────────────────────────────────────────┐
│ PHASE 5: Content Download                                  │
└─────────────────────────────────────────────────────────────┘

22. Steam calls: GetAppInstallState(501)
    ↓
23. Hook returns: k_EAppInstallState_Installed
    ↓
24. Steam calls: GetManifestId(501, depotID)
    ↓
25. Hook returns: 8134324683205569669 (from setManifestid)
    ↓
26. Steam queries content server: "Give me manifest 8134324683205569669"
    ↓
27. Content server responds with manifest data
    ↓
28. Steam calls: GetDepotDecryptionKey(501, depotID, keyOut)
    ↓
29. Hook returns: depot key from addappid() call
    ↓
30. Steam downloads encrypted files from CDN
    ↓
31. Steam decrypts files using depot key
    ↓
32. Game files installed to disk

┌─────────────────────────────────────────────────────────────┐
│ PHASE 6: Game Execution                                    │
└─────────────────────────────────────────────────────────────┘

33. Steam launches game executable
    ↓
34. Game calls Steam API: SteamAPI_Init()
    ↓
35. Game queries: BIsAppInstalled(501)
    ↓
36. Hook still active, returns TRUE
    ↓
37. Game proceeds normally
    ↓
38. Game runs (offline features work, online features may fail)
```

---

## Real-World Code Examples

### Complete Hook DLL Example

```cpp
// hook_dll.cpp - Complete example

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <unordered_map>
#include <mutex>
#include <string>
#include <regex>
#include <fstream>

typedef uint32_t AppId_t;
typedef uint32_t DepotId_t;
typedef uint32_t HSteamUser;
typedef uint32_t HSteamPipe;

struct FakeApp {
    AppId_t appID;
    uint64_t manifestID;
    char depotKey[65];
    bool hasDepotKey;
};

std::unordered_map<AppId_t, FakeApp> g_fakeApps;
std::mutex g_fakeAppsMutex;

HMODULE g_hSteamAPI = NULL;
void* g_pSteamAppsVTable = NULL;

typedef bool (*BIsAppInstalled_t)(AppId_t);
BIsAppInstalled_t Original_BIsAppInstalled = NULL;

bool Hooked_BIsAppInstalled(AppId_t appID) {
    std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
    
    if (g_fakeApps.find(appID) != g_fakeApps.end()) {
        return true;
    }
    
    if (Original_BIsAppInstalled) {
        return Original_BIsAppInstalled(appID);
    }
    return false;
}

void ParseLuaScript(const char* filename) {
    std::ifstream file(filename);
    if (!file.is_open()) return;
    
    std::string line;
    std::regex addAppRegex(R"(addappid\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*,\s*["']?([a-fA-F0-9]{64})["']?)?\s*\))");
    std::regex manifestRegex(R"(setManifestid\s*\(\s*(\d+)\s*,\s*["']?(\d+)["']?\s*\))");
    
    while (std::getline(file, line)) {
        size_t commentPos = line.find("--");
        if (commentPos != std::string::npos) {
            line = line.substr(0, commentPos);
        }
        
        std::smatch match;
        if (std::regex_match(line, match, addAppRegex)) {
            AppId_t appID = std::stoul(match[1].str());
            std::string depotKey = match[3].matched ? match[3].str() : "";
            
            std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
            FakeApp& app = g_fakeApps[appID];
            app.appID = appID;
            
            if (!depotKey.empty() && depotKey.length() == 64) {
                strncpy_s(app.depotKey, depotKey.c_str(), 64);
                app.hasDepotKey = true;
            }
        }
        else if (std::regex_match(line, match, manifestRegex)) {
            AppId_t appID = std::stoul(match[1].str());
            uint64_t manifestID = std::stoull(match[2].str());
            
            std::lock_guard<std::mutex> lock(g_fakeAppsMutex);
            FakeApp& app = g_fakeApps[appID];
            app.appID = appID;
            app.manifestID = manifestID;
        }
    }
}

void InstallHooks() {
    g_hSteamAPI = GetModuleHandleA("steam_api.dll");
    if (!g_hSteamAPI) return;
    
    typedef void* (*SteamClient_t)();
    SteamClient_t SteamClient = (SteamClient_t)GetProcAddress(g_hSteamAPI, "SteamClient");
    if (!SteamClient) return;
    
    void* pSteamClient = SteamClient();
    if (!pSteamClient) return;
    
    typedef void* (*GetISteamApps_t)(void*, HSteamUser, HSteamPipe, const char*);
    GetISteamApps_t GetISteamApps = (GetISteamApps_t)GetProcAddress(
        g_hSteamAPI, "SteamAPI_ISteamClient_GetISteamApps"
    );
    if (!GetISteamApps) return;
    
    void* pSteamApps = GetISteamApps(pSteamClient, 0, 0, "STEAMAPPS_INTERFACE_VERSION001");
    if (!pSteamApps) return;
    
    void** vtable = *(void***)pSteamApps;
    g_pSteamAppsVTable = vtable;
    
    DWORD oldProtect;
    VirtualProtect(&vtable[0], sizeof(void*), PAGE_READWRITE, &oldProtect);
    
    Original_BIsAppInstalled = (BIsAppInstalled_t)vtable[0];
    vtable[0] = (void*)Hooked_BIsAppInstalled;
    
    VirtualProtect(&vtable[0], sizeof(void*), oldProtect, &oldProtect);
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD dwReason, LPVOID lpReserved) {
    if (dwReason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);
        
        ParseLuaScript("steamtools.lua");
        InstallHooks();
    }
    return TRUE;
}
```

### Injector Tool Example

```cpp
// injector.cpp - Tool that injects the DLL

#include <windows.h>
#include <tlhelp32.h>
#include <iostream>

DWORD FindSteamProcess() {
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE) return 0;
    
    PROCESSENTRY32W pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32W);
    
    if (!Process32FirstW(hSnapshot, &pe32)) {
        CloseHandle(hSnapshot);
        return 0;
    }
    
    do {
        if (_wcsicmp(pe32.szExeFile, L"steam.exe") == 0) {
            CloseHandle(hSnapshot);
            return pe32.th32ProcessID;
        }
    } while (Process32NextW(hSnapshot, &pe32));
    
    CloseHandle(hSnapshot);
    return 0;
}

bool InjectDLL(DWORD processId, const char* dllPath) {
    HANDLE hProcess = OpenProcess(
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION |
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
        FALSE, processId
    );
    
    if (!hProcess) {
        std::cerr << "Failed to open process. Error: " << GetLastError() << std::endl;
        return false;
    }
    
    size_t pathLen = strlen(dllPath) + 1;
    LPVOID pRemoteMemory = VirtualAllocEx(
        hProcess, NULL, pathLen, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
    );
    
    if (!pRemoteMemory) {
        std::cerr << "Failed to allocate memory. Error: " << GetLastError() << std::endl;
        CloseHandle(hProcess);
        return false;
    }
    
    if (!WriteProcessMemory(hProcess, pRemoteMemory, dllPath, pathLen, NULL)) {
        std::cerr << "Failed to write memory. Error: " << GetLastError() << std::endl;
        VirtualFreeEx(hProcess, pRemoteMemory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }
    
    HMODULE hKernel32 = GetModuleHandleA("kernel32.dll");
    LPTHREAD_START_ROUTINE pLoadLibrary = (LPTHREAD_START_ROUTINE)
        GetProcAddress(hKernel32, "LoadLibraryA");
    
    HANDLE hThread = CreateRemoteThread(
        hProcess, NULL, 0, pLoadLibrary, pRemoteMemory, 0, NULL
    );
    
    if (!hThread) {
        std::cerr << "Failed to create thread. Error: " << GetLastError() << std::endl;
        VirtualFreeEx(hProcess, pRemoteMemory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }
    
    WaitForSingleObject(hThread, INFINITE);
    
    DWORD exitCode;
    GetExitCodeThread(hThread, &exitCode);
    
    CloseHandle(hThread);
    VirtualFreeEx(hProcess, pRemoteMemory, 0, MEM_RELEASE);
    CloseHandle(hProcess);
    
    if (exitCode == 0) {
        std::cerr << "LoadLibrary failed in remote process" << std::endl;
        return false;
    }
    
    std::cout << "DLL injected successfully!" << std::endl;
    return true;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <path_to_dll>" << std::endl;
        return 1;
    }
    
    char dllPath[MAX_PATH];
    if (!GetFullPathNameA(argv[1], MAX_PATH, dllPath, NULL)) {
        std::cerr << "Invalid DLL path" << std::endl;
        return 1;
    }
    
    std::cout << "Looking for Steam process..." << std::endl;
    DWORD steamPID = FindSteamProcess();
    
    if (steamPID == 0) {
        std::cerr << "Steam process not found!" << std::endl;
        return 1;
    }
    
    std::cout << "Found Steam process (PID: " << steamPID << ")" << std::endl;
    std::cout << "Injecting DLL: " << dllPath << std::endl;
    
    if (InjectDLL(steamPID, dllPath)) {
        std::cout << "Injection successful!" << std::endl;
        return 0;
    } else {
        std::cerr << "Injection failed!" << std::endl;
        return 1;
    }
}
```

---

## Advanced Topics

### Bypassing VAC Detection

```cpp
// VAC (Valve Anti-Cheat) detection evasion techniques
// (Educational purposes only)

// 1. Hide DLL from module list
void HideDLLFromPEB(HMODULE hModule) {
    PPEB peb = (PPEB)__readgsqword(0x60);  // x64
    PPEB_LDR_DATA ldr = peb->Ldr;
    
    for (PLIST_ENTRY entry = ldr->InMemoryOrderModuleList.Flink;
         entry != &ldr->InMemoryOrderModuleList;
         entry = entry->Flink) {
        PLDR_DATA_TABLE_ENTRY module = CONTAINING_RECORD(
            entry, LDR_DATA_TABLE_ENTRY, InMemoryOrderLinks
        );
        
        if (module->DllBase == hModule) {
            entry->Flink->Blink = entry->Blink;
            entry->Blink->Flink = entry->Flink;
            break;
        }
    }
}

// 2. Unhook API functions that VAC might check
void UnhookNtQueryInformationProcess() {
    HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
    void* originalFunc = GetProcAddress(hNtdll, "NtQueryInformationProcess");
    
    // Restore original bytes from disk
    // (VAC might hook this to detect injection)
}
```

### Manifest File Structure

```cpp
// Steam manifest file format (depotcache_*.manifest)
struct ManifestHeader {
    uint32 magic;           // "VSMD"
    uint32 version;         // Usually 1
    DepotId_t depotID;
    uint64 manifestGID;     // Global ID
    uint32 creationTime;
    uint32 fileCount;
    uint32 nameCount;
    uint32 nameSize;
    uint32 fileSize;
    uint32 hashSize;
    uint32 blockSize;
};

struct ManifestFileEntry {
    char* filename;
    uint64 totalSize;
    uint32 flags;
    uint32 crc;
    uint16 chunksCount;
    ManifestChunk chunks[];
};

struct ManifestChunk {
    uint64 offset;
    uint64 compressedSize;
    uint64 uncompressedSize;
    uint8 sha[20];  // SHA-1 hash
};
```

This completes the in-depth technical example showing exactly how Steam unlocking tools work at the code level.
