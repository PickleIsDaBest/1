#!/usr/bin/env python3

class FakeApp:
    def __init__(self, app_id, manifest_id=0, depot_key=None):
        self.app_id = app_id
        self.manifest_id = manifest_id
        self.depot_key = depot_key
        self.has_depot_key = depot_key is not None

class SteamHookSimulator:
    def __init__(self):
        self.fake_apps = {}
        self.original_ownership = {100, 200, 300}
        self.call_log = []
    
    def parse_lua_script(self, script_content):
        import re
        
        addapp_regex = r'addappid\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*,\s*["\']?([a-fA-F0-9]{64})["\']?)?\s*\)'
        manifest_regex = r'setManifestid\s*\(\s*(\d+)\s*,\s*["\']?(\d+)["\']?\s*\)'
        
        for line in script_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            match = re.match(addapp_regex, line)
            if match:
                app_id = int(match.group(1))
                depot_key = match.group(3) if match.group(3) else None
                
                if app_id not in self.fake_apps:
                    self.fake_apps[app_id] = FakeApp(app_id, depot_key=depot_key)
                else:
                    if depot_key:
                        self.fake_apps[app_id].depot_key = depot_key
                        self.fake_apps[app_id].has_depot_key = True
                
                print(f"[Lua] Added AppID {app_id}" + 
                      (f" with depot key: {depot_key[:16]}..." if depot_key else ""))
                continue
            
            match = re.match(manifest_regex, line)
            if match:
                app_id = int(match.group(1))
                manifest_id = int(match.group(2))
                
                if app_id not in self.fake_apps:
                    self.fake_apps[app_id] = FakeApp(app_id, manifest_id=manifest_id)
                else:
                    self.fake_apps[app_id].manifest_id = manifest_id
                
                print(f"[Lua] Set manifest for AppID {app_id}: {manifest_id}")
    
    def b_is_app_installed(self, app_id):
        self.call_log.append(f"BIsAppInstalled({app_id})")
        
        if app_id in self.fake_apps:
            print(f"[Hook] BIsAppInstalled({app_id}) → TRUE (fake ownership)")
            return True
        
        original_result = app_id in self.original_ownership
        print(f"[Hook] BIsAppInstalled({app_id}) → {original_result} (original check)")
        return original_result
    
    def get_manifest_id(self, app_id, depot_id):
        self.call_log.append(f"GetManifestId({app_id}, {depot_id})")
        
        if app_id in self.fake_apps and self.fake_apps[app_id].manifest_id != 0:
            manifest_id = self.fake_apps[app_id].manifest_id
            print(f"[Hook] GetManifestId({app_id}, {depot_id}) → {manifest_id}")
            return manifest_id
        
        print(f"[Hook] GetManifestId({app_id}, {depot_id}) → 0 (no manifest set)")
        return 0
    
    def get_depot_key(self, app_id, depot_id):
        self.call_log.append(f"GetDepotDecryptionKey({app_id}, {depot_id})")
        
        if app_id in self.fake_apps and self.fake_apps[app_id].has_depot_key:
            depot_key = self.fake_apps[app_id].depot_key
            print(f"[Hook] GetDepotDecryptionKey({app_id}, {depot_id}) → {depot_key[:32]}...")
            return depot_key
        
        print(f"[Hook] GetDepotDecryptionKey({app_id}, {depot_id}) → NULL (no key)")
        return None
    
    def simulate_game_launch(self, app_id):
        print(f"\n{'='*60}")
        print(f"SIMULATING GAME LAUNCH FOR AppID {app_id}")
        print(f"{'='*60}\n")
        
        print("Step 1: Check if app is installed...")
        is_installed = self.b_is_app_installed(app_id)
        
        if not is_installed:
            print("❌ Game not owned/installed. Launch cancelled.")
            return False
        
        print("✓ Game is installed. Proceeding...\n")
        
        print("Step 2: Get manifest ID for content download...")
        manifest_id = self.get_manifest_id(app_id, 1)
        
        if manifest_id == 0:
            print("⚠ No manifest ID set. Game may not download properly.")
        else:
            print(f"✓ Manifest ID: {manifest_id}\n")
        
        print("Step 3: Get depot decryption key...")
        depot_key = self.get_depot_key(app_id, 1)
        
        if depot_key:
            print(f"✓ Depot key available: {depot_key[:32]}...")
            print("✓ Steam can decrypt downloaded content.\n")
        else:
            print("⚠ No depot key. Content will be encrypted.\n")
        
        print("Step 4: Simulating content download...")
        print("  → Querying content server for manifest...")
        print("  → Downloading encrypted chunks...")
        if depot_key:
            print("  → Decrypting files...")
            print("  → Installing to disk...")
            print("✓ Installation complete!\n")
        
        print("Step 5: Launching game executable...")
        print("  → game.exe starts")
        print("  → game.exe calls SteamAPI_Init()")
        print("  → game.exe calls BIsAppInstalled()")
        is_installed_check = self.b_is_app_installed(app_id)
        if is_installed_check:
            print("✓ Game verified ownership. Proceeding...")
            print("✓ Game launched successfully!")
        else:
            print("❌ Ownership check failed. Game may exit.")
        
        return True
    
    def print_summary(self):
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Fake apps registered: {len(self.fake_apps)}")
        for app_id, app in self.fake_apps.items():
            print(f"  AppID {app_id}: manifest={app.manifest_id}, has_key={app.has_depot_key}")
        print(f"\nTotal API calls intercepted: {len(self.call_log)}")
        for call in self.call_log:
            print(f"  - {call}")

def main():
    print("Steam Hook Simulator - Educational Demonstration\n")
    
    lua_script = """
addappid(500)
addappid(1660740)
addappid(501,0,"7a0b21eed084464fd2efb03ecc44116224b150f9377551ca7901ead966f21c26")
setManifestid(501,"8134324683205569669")
addappid(502,0,"54d51378fea25647cfe0c7d77804f29abd538c2606e4bf27b972d02816f34487")
setManifestid(502,"1451893850733299565")
"""
    
    simulator = SteamHookSimulator()
    
    print("Parsing Lua script...")
    print("-" * 60)
    simulator.parse_lua_script(lua_script)
    print("-" * 60)
    
    print("\nSimulating launch of AppID 501 (fake game)...")
    simulator.simulate_game_launch(501)
    
    print("\nSimulating launch of AppID 100 (legitimately owned)...")
    simulator.simulate_game_launch(100)
    
    print("\nSimulating launch of AppID 999 (not owned)...")
    simulator.simulate_game_launch(999)
    
    simulator.print_summary()

if __name__ == "__main__":
    main()
