# Visual Diagrams: Steam Unlocking Mechanism

## Memory Layout Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEAM PROCESS MEMORY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Steam.exe (0x00400000)                                  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ Main()                                             │  │  │
│  │  │  └─> SteamAPI_Init()                               │  │  │
│  │  │      └─> Creates ISteamClient                      │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  steam_api.dll (0x10000000)                             │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ ISteamApps Interface                                │  │  │
│  │  │  ┌──────────────────────────────────────────────┐  │  │  │
│  │  │  │ VTable (Function Pointers)                  │  │  │  │
│  │  │  │ [0] BIsAppInstalled ──┐                      │  │  │  │
│  │  │  │ [1] BIsDlcInstalled   │                      │  │  │  │
│  │  │  │ [2] GetAppInstallState│                      │  │  │  │
│  │  │  │ [3] GetManifestId     │                      │  │  │  │
│  │  │  │ [4] GetDepotKey       │                      │  │  │  │
│  │  │  └───────────────────────┼──────────────────────┘  │  │  │
│  │  │                          │                         │  │  │
│  │  │                          │ HOOKED!                │  │  │
│  │  │                          │                        │  │  │
│  │  │                          ▼                        │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  hook.dll (0x20000000) - INJECTED                       │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ Hooked Functions                                    │  │  │
│  │  │  ┌──────────────────────────────────────────────┐  │  │  │
│  │  │  │ Hooked_BIsAppInstalled()                     │  │  │  │
│  │  │  │  1. Check g_fakeApps map                     │  │  │  │
│  │  │  │  2. If found → return TRUE                   │  │  │  │
│  │  │  │  3. Else → call original                     │  │  │  │
│  │  │  └──────────────────────────────────────────────┘  │  │  │
│  │  │                                                    │  │  │
│  │  │  ┌──────────────────────────────────────────────┐  │  │  │
│  │  │  │ g_fakeApps Map (std::unordered_map)         │  │  │  │
│  │  │  │ ┌──────┬──────────────────────────────────┐ │  │  │  │
│  │  │  │ │ 500  │ {appID:500, manifestID:0, ...} │ │  │  │  │
│  │  │  │ ├──────┼──────────────────────────────────┤ │  │  │  │
│  │  │  │ │ 501  │ {appID:501, manifestID:8134..., │ │  │  │  │
│  │  │  │ │      │  depotKey:"7a0b21ee..."}         │ │  │  │  │
│  │  │  │ ├──────┼──────────────────────────────────┤ │  │  │  │
│  │  │  │ │ 502  │ {appID:502, manifestID:1451..., │ │  │  │  │
│  │  │  │ │      │  depotKey:"54d51378..."}         │ │  │  │  │
│  │  │  │ └──────┴──────────────────────────────────┘ │  │  │  │
│  │  │  └──────────────────────────────────────────────┘  │  │  │
│  │  │                                                    │  │  │
│  │  │  ┌──────────────────────────────────────────────┐  │  │  │
│  │  │  │ Lua Parser                                   │  │  │  │
│  │  │  │ - Reads steamtools.lua                       │  │  │  │
│  │  │  │ - Parses addappid() calls                    │  │  │  │
│  │  │  │ - Parses setManifestid() calls               │  │  │  │
│  │  │  │ - Populates g_fakeApps map                   │  │  │  │
│  │  │  └──────────────────────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Function Call Flow Diagram

```
USER ACTION: Double-click game in Steam library
│
├─> Steam.exe: LaunchGame(AppID 501)
│   │
│   ├─> Steam.exe: Check if user owns game
│   │   │
│   │   └─> steam_api.dll: pSteamApps->BIsAppInstalled(501)
│   │       │
│   │       └─> [VTable Entry 0] ──┐
│   │                               │
│   │                               ▼
│   │                       hook.dll: Hooked_BIsAppInstalled(501)
│   │                               │
│   │                               ├─> Check g_fakeApps[501]
│   │                               │   │
│   │                               │   └─> FOUND! ✓
│   │                               │
│   │                               └─> Return TRUE
│   │
│   ├─> Steam.exe: "User owns game, proceed"
│   │   │
│   │   ├─> Steam.exe: Check installation state
│   │   │   │
│   │   │   └─> steam_api.dll: GetAppInstallState(501)
│   │   │       │
│   │   │       └─> hook.dll: Hooked_GetAppInstallState(501)
│   │   │           │
│   │   │           └─> Return: k_EAppInstallState_Installed
│   │   │
│   │   ├─> Steam.exe: Get manifest for download
│   │   │   │
│   │   │   └─> steam_api.dll: GetManifestId(501, depotID)
│   │   │       │
│   │   │       └─> hook.dll: Hooked_GetManifestId(501, depotID)
│   │   │           │
│   │   │           └─> Return: 8134324683205569669
│   │   │
│   │   ├─> Steam.exe: Query content server
│   │   │   │
│   │   │   └─> HTTP Request: GET /depot/501/manifest/8134324683205569669
│   │   │       │
│   │   │       └─> Content Server: Returns manifest file
│   │   │
│   │   ├─> Steam.exe: Get decryption key
│   │   │   │
│   │   │   └─> steam_api.dll: GetDepotDecryptionKey(501, depotID)
│   │   │       │
│   │   │       └─> hook.dll: Hooked_GetDepotDecryptionKey(501, depotID)
│   │   │           │
│   │   │           └─> Return: "7a0b21eed084464fd2efb03ecc44116224b150f9377551ca7901ead966f21c26"
│   │   │
│   │   ├─> Steam.exe: Download encrypted files from CDN
│   │   │   │
│   │   │   └─> HTTP Request: GET /depot/501/chunk/...
│   │   │
│   │   ├─> Steam.exe: Decrypt files using depot key
│   │   │
│   │   └─> Steam.exe: Install game files to disk
│   │
│   └─> Steam.exe: Launch game executable
│       │
│       └─> game.exe: SteamAPI_Init()
│           │
│           └─> steam_api.dll: BIsAppInstalled(501)
│               │
│               └─> hook.dll: Hooked_BIsAppInstalled(501)
│                   │
│                   └─> Return TRUE → Game proceeds
```

## Data Structure Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Lua Script File                          │
│                  (steamtools.lua)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  addappid(500)                                             │
│  addappid(1660740)                                         │
│  addappid(501, 0, "7a0b21eed084464fd2efb03ecc44116224b...")│
│  setManifestid(501, "8134324683205569669")                │
│  addappid(502, 0, "54d51378fea25647cfe0c7d77804f29abd5...")│
│  setManifestid(502, "1451893850733299565")                │
│  ...                                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ Parse
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              g_fakeApps (std::unordered_map)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Key: AppId_t (uint32)                                     │
│  Value: FakeApp struct                                     │
│                                                             │
│  ┌──────┬────────────────────────────────────────────────┐ │
│  │ 500  │ FakeApp {                                      │ │
│  │      │   appID: 500                                   │ │
│  │      │   manifestID: 0                                │ │
│  │      │   depotKey: ""                                 │ │
│  │      │   hasDepotKey: false                           │ │
│  │      │ }                                              │ │
│  ├──────┼────────────────────────────────────────────────┤ │
│  │ 501  │ FakeApp {                                      │ │
│  │      │   appID: 501                                   │ │
│  │      │   manifestID: 8134324683205569669              │ │
│  │      │   depotKey: "7a0b21eed084464fd2efb03ecc4411..."│ │
│  │      │   hasDepotKey: true                            │ │
│  │      │ }                                              │ │
│  ├──────┼────────────────────────────────────────────────┤ │
│  │ 502  │ FakeApp {                                      │ │
│  │      │   appID: 502                                   │ │
│  │      │   manifestID: 1451893850733299565              │ │
│  │      │   depotKey: "54d51378fea25647cfe0c7d77804f2..."│ │
│  │      │   hasDepotKey: true                            │ │
│  │      │ }                                              │ │
│  └──────┴────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Hook Installation Process

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Find Steam Process                                  │
└─────────────────────────────────────────────────────────────┘
        │
        │ CreateToolhelp32Snapshot()
        │ Process32First() / Process32Next()
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Open Process                                        │
└─────────────────────────────────────────────────────────────┘
        │
        │ OpenProcess(PROCESS_ALL_ACCESS)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Allocate Memory in Steam Process                    │
└─────────────────────────────────────────────────────────────┘
        │
        │ VirtualAllocEx()
        │ - Allocate space for DLL path string
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Write DLL Path to Remote Memory                     │
└─────────────────────────────────────────────────────────────┘
        │
        │ WriteProcessMemory()
        │ - Write "C:\path\to\hook.dll"
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Get LoadLibraryA Address                           │
└─────────────────────────────────────────────────────────────┘
        │
        │ GetModuleHandle("kernel32.dll")
        │ GetProcAddress("LoadLibraryA")
        │ - Same address in all processes
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Create Remote Thread                               │
└─────────────────────────────────────────────────────────────┘
        │
        │ CreateRemoteThread()
        │ - Thread function: LoadLibraryA
        │ - Parameter: Address of DLL path string
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: DLL Loads in Steam Process                          │
└─────────────────────────────────────────────────────────────┘
        │
        │ DllMain() called with DLL_PROCESS_ATTACH
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Install Hooks                                       │
└─────────────────────────────────────────────────────────────┘
        │
        │ GetSteamAppsInterface()
        │ - Get ISteamApps vtable pointer
        │
        │ Modify vtable entries:
        │ - Save original function pointers
        │ - Replace with hook function pointers
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 9: Load Lua Script                                     │
└─────────────────────────────────────────────────────────────┘
        │
        │ ParseLuaScript("steamtools.lua")
        │ - Parse addappid() calls
        │ - Parse setManifestid() calls
        │ - Populate g_fakeApps map
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ READY: Hooks Active, Script Loaded                          │
└─────────────────────────────────────────────────────────────┘
```

## VTable Hooking Visualization

```
BEFORE HOOKING:
┌─────────────────────────────────────────┐
│ ISteamApps VTable                       │
├─────────────────────────────────────────┤
│ [0] → 0x10001234 (Original_BIsAppInstalled) │
│ [1] → 0x10001567 (Original_BIsDlcInstalled) │
│ [2] → 0x10001890 (Original_GetAppInstallState) │
│ [3] → 0x10001ABC (Original_GetManifestId) │
└─────────────────────────────────────────┘

AFTER HOOKING:
┌─────────────────────────────────────────┐
│ ISteamApps VTable                       │
├─────────────────────────────────────────┤
│ [0] → 0x20001000 (Hooked_BIsAppInstalled) ← CHANGED! │
│ [1] → 0x20001333 (Hooked_BIsDlcInstalled) ← CHANGED! │
│ [2] → 0x20001666 (Hooked_GetAppInstallState) ← CHANGED! │
│ [3] → 0x20001999 (Hooked_GetManifestId) ← CHANGED! │
└─────────────────────────────────────────┘

Original functions still exist at:
┌─────────────────────────────────────────┐
│ Saved Function Pointers                 │
├─────────────────────────────────────────┤
│ Original_BIsAppInstalled = 0x10001234   │
│ Original_BIsDlcInstalled = 0x10001567   │
│ Original_GetAppInstallState = 0x10001890│
│ Original_GetManifestId = 0x10001ABC     │
└─────────────────────────────────────────┘
```

## Content Download Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Steam Client                                                │
└─────────────────────────────────────────────────────────────┘
        │
        │ 1. User clicks "Install" for AppID 501
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Hook: BIsAppInstalled(501)                                  │
│ Returns: TRUE (fake ownership)                              │
└─────────────────────────────────────────────────────────────┘
        │
        │ 2. Steam proceeds with installation
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Hook: GetManifestId(501, depotID)                          │
│ Returns: 8134324683205569669                                │
└─────────────────────────────────────────────────────────────┘
        │
        │ 3. Steam queries content server
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP GET: https://cdn.steamcontent.com/depot/501/           │
│           manifest/8134324683205569669                      │
└─────────────────────────────────────────────────────────────┘
        │
        │ 4. Content server responds
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Manifest File Received                                      │
│ - File list with checksums                                 │
│ - Chunk information                                         │
│ - Download URLs                                             │
└─────────────────────────────────────────────────────────────┘
        │
        │ 5. Steam requests decryption key
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Hook: GetDepotDecryptionKey(501, depotID)                  │
│ Returns: "7a0b21eed084464fd2efb03ecc44116224b150f9377551..."│
└─────────────────────────────────────────────────────────────┘
        │
        │ 6. Steam downloads encrypted chunks
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP GET: https://cdn.steamcontent.com/depot/501/chunk/... │
│ - Encrypted file data                                       │
└─────────────────────────────────────────────────────────────┘
        │
        │ 7. Steam decrypts using depot key
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Decrypted Files                                             │
│ - game.exe                                                  │
│ - data.pak                                                  │
│ - ...                                                       │
└─────────────────────────────────────────────────────────────┘
        │
        │ 8. Files written to disk
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ C:\Program Files (x86)\Steam\steamapps\common\GameName\    │
│ ✓ Installation Complete                                     │
└─────────────────────────────────────────────────────────────┘
```
