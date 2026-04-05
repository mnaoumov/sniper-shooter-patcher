"""
Sniper Shooter APK Patcher

Takes the original Sniper Shooter Free v2.9.2 APK and patches it to run on modern Android.
See CLAUDE.md for full documentation of all patches applied.

Usage:
    py patch.py <input.apk> [output.apk]
    py patch.py --help
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
PATCHES_DIR = SCRIPT_DIR / "patches"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def find_tool(name: str) -> str:
    """Find a .jar tool in the working directory, script directory, or PATH."""
    for search_dir in [Path.cwd(), SCRIPT_DIR]:
        candidate = search_dir / name
        if candidate.exists():
            return str(candidate)
    # Try PATH
    which = shutil.which(name)
    if which:
        return which
    raise FileNotFoundError(
        f"Cannot find {name}. Place it in the working directory or script directory."
    )


# ---------------------------------------------------------------------------
# P1: apktool.yml - SDK versions
# ---------------------------------------------------------------------------
def patch_apktool_yml(decoded_dir: Path) -> None:
    print("[P1] Patching apktool.yml (SDK versions)...")
    path = decoded_dir / "apktool.yml"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"minSdkVersion: '?\d+'?", "minSdkVersion: '23'", text)
    text = re.sub(r"targetSdkVersion: '?\d+'?", "targetSdkVersion: '30'", text)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P2: AndroidManifest.xml
# ---------------------------------------------------------------------------
def patch_manifest(decoded_dir: Path) -> None:
    print("[P2] Patching AndroidManifest.xml...")
    path = decoded_dir / "AndroidManifest.xml"
    text = path.read_text(encoding="utf-8")

    # Add networkSecurityConfig and usesCleartextTraffic to <application>
    if "networkSecurityConfig" not in text:
        text = text.replace(
            'android:largeHeap="true"',
            'android:largeHeap="true" android:networkSecurityConfig="@xml/network_security_config"',
        )
    if "usesCleartextTraffic" not in text:
        text = text.replace(
            'android:largeHeap="true"',
            'android:largeHeap="true" android:usesCleartextTraffic="true"',
        )

    # Add uses-library for Apache HTTP legacy (removed in SDK 28+)
    if "org.apache.http.legacy" not in text:
        text = text.replace(
            "<application ",
            '<application ',
        )
        # Insert uses-library right after the <application> opening tag
        text = re.sub(
            r"(<application\b[^>]*>)",
            r'\1\n        <uses-library android:name="org.apache.http.legacy" android:required="false"/>',
            text,
        )

    # Add android:exported to components that lack it
    # Activities/receivers with intent-filters get exported="true"
    # Others get exported="false"
    lines = text.split("\n")
    result_lines = []
    for i, line in enumerate(lines):
        if re.search(r"<(activity|receiver|service|provider)\b", line) and "android:exported" not in line:
            # Check if this component has an intent-filter (look ahead)
            has_intent_filter = False
            for j in range(i + 1, min(i + 10, len(lines))):
                if "<intent-filter" in lines[j]:
                    has_intent_filter = True
                    break
                if re.search(r"</(activity|receiver|service|provider)|/>", lines[j]):
                    break
            exported_value = "true" if has_intent_filter else "false"
            # Insert exported attribute after the tag name
            line = re.sub(
                r"(<(?:activity|receiver|service|provider)\b)",
                rf'\1 android:exported="{exported_value}"',
                line,
            )
        result_lines.append(line)

    path.write_text("\n".join(result_lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# P3: Network security config (new file)
# ---------------------------------------------------------------------------
def patch_network_security_config(decoded_dir: Path) -> None:
    print("[P3] Adding network_security_config.xml...")
    xml_dir = decoded_dir / "res" / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    src = PATCHES_DIR / "network_security_config.xml"
    shutil.copy2(src, xml_dir / "network_security_config.xml")


# ---------------------------------------------------------------------------
# P4: BaseGameActivity stub (full file replacement)
# ---------------------------------------------------------------------------
def patch_base_game_activity(decoded_dir: Path) -> None:
    print("[P4] Replacing BaseGameActivity with stub...")
    src = PATCHES_DIR / "base_game_activity.smali"
    dst = decoded_dir / "smali" / "com" / "google" / "b" / "a" / "a" / "a.smali"
    shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# P5: GameHelper stubs
# ---------------------------------------------------------------------------
def patch_game_helper(decoded_dir: Path) -> None:
    print("[P5] Patching GameHelper (dialog + getGamesClient stubs)...")
    path = decoded_dir / "smali" / "com" / "google" / "b" / "a" / "a" / "b.smali"
    text = path.read_text(encoding="utf-8")

    # Stub the a(String, String) dialog method - replace body with return-void
    # Match the method signature and replace up to .end method
    text = _stub_method(
        text,
        r"\.method public a\(Ljava/lang/String;Ljava/lang/String;\)V",
        """\
.method public a(Ljava/lang/String;Ljava/lang/String;)V
    .locals 0

    .prologue
    return-void
.end method""",
    )

    # Stub c() to return null instead of throwing
    text = _stub_method(
        text,
        r"\.method public c\(\)Lcom/google/android/gms/games/b;",
        """\
.method public c()Lcom/google/android/gms/games/b;
    .locals 1

    .prologue
    const/4 v0, 0x0

    return-object v0
.end method""",
    )

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P6: Crashlytics stub
# ---------------------------------------------------------------------------
def patch_crashlytics(decoded_dir: Path) -> None:
    print("[P6] Patching Crashlytics (stub init)...")
    path = decoded_dir / "smali" / "com" / "b" / "a" / "d.smali"
    if not path.exists():
        print("  [skip] Crashlytics file not found")
        return
    text = path.read_text(encoding="utf-8")

    # Stub a(Context)V - init method
    text = _stub_method(
        text,
        r"\.method public static a\(Landroid/content/Context;\)V",
        """\
.method public static a(Landroid/content/Context;)V
    .locals 0

    .prologue
    return-void
.end method""",
    )

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P7: Flurry Analytics stub
# ---------------------------------------------------------------------------
def patch_flurry(decoded_dir: Path) -> None:
    print("[P7] Patching FlurryAgent (stub network methods)...")
    path = decoded_dir / "smali" / "com" / "flurry" / "android" / "FlurryAgent.smali"
    if not path.exists():
        print("  [skip] FlurryAgent file not found")
        return
    text = path.read_text(encoding="utf-8")

    for method_sig in [
        r"\.method public static setUseHttps\(Z\)V",
        r"\.method public static onStartSession\(Landroid/content/Context;Ljava/lang/String;\)V",
        r"\.method public static onEndSession\(Landroid/content/Context;\)V",
        r"\.method public static logEvent\(Ljava/lang/String;\)V",
    ]:
        # Extract the method declaration line for the stub
        m = re.search(method_sig, text)
        if m:
            method_decl = m.group(0).replace("\\", "")
            text = _stub_method(
                text,
                method_sig,
                f"""\
{method_decl}
    .locals 0

    .prologue
    return-void
.end method""",
            )

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P8: AdsManager stub
# ---------------------------------------------------------------------------
def patch_ads_manager(decoded_dir: Path) -> None:
    print("[P8] Patching AdsManager (stub ad display)...")
    path = decoded_dir / "smali" / "com" / "fungamesforfree" / "snipershooter" / "r" / "a.smali"
    if not path.exists():
        print("  [skip] AdsManager file not found")
        return
    text = path.read_text(encoding="utf-8")

    text = _stub_method(
        text,
        r"\.method public a\(Landroid/app/Activity;Landroid/view/ViewGroup;\)V",
        """\
.method public a(Landroid/app/Activity;Landroid/view/ViewGroup;)V
    .locals 0

    .prologue
    return-void
.end method""",
    )

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P9: MainActivity fixes (StrictMode + setContentView + fragment)
# ---------------------------------------------------------------------------
def patch_main_activity(decoded_dir: Path) -> None:
    print("[P9] Patching MainActivity (StrictMode + setContentView + fragment fix)...")
    path = (
        decoded_dir
        / "smali"
        / "com"
        / "fungamesforfree"
        / "snipershooter"
        / "activities"
        / "MainActivity.smali"
    )
    text = path.read_text(encoding="utf-8")

    # --- 9a: Add StrictMode.permitAll() at start of onCreate ---
    # Find the .prologue in onCreate and insert StrictMode setup after it
    oncreate_pattern = r"(\.method protected onCreate\(Landroid/os/Bundle;\)V\s*\.locals \d+\s*\.prologue)"
    strictmode_code = """\
\\1
    # Disable StrictMode NetworkOnMainThread enforcement for legacy code
    new-instance v0, Landroid/os/StrictMode$ThreadPolicy$Builder;

    invoke-direct {v0}, Landroid/os/StrictMode$ThreadPolicy$Builder;-><init>()V

    invoke-virtual {v0}, Landroid/os/StrictMode$ThreadPolicy$Builder;->permitAll()Landroid/os/StrictMode$ThreadPolicy$Builder;

    move-result-object v0

    invoke-virtual {v0}, Landroid/os/StrictMode$ThreadPolicy$Builder;->build()Landroid/os/StrictMode$ThreadPolicy;

    move-result-object v0

    invoke-static {v0}, Landroid/os/StrictMode;->setThreadPolicy(Landroid/os/StrictMode$ThreadPolicy;)V
"""
    text = re.sub(oncreate_pattern, strictmode_code, text)

    # --- 9b: Move setContentView before try_start_2 ---
    # Find the pattern: :goto_1\n    :try_start_2\n    invoke-static {p0}, ...ag;->a(...)
    # Insert setContentView + window flags between :goto_1 and :try_start_2
    set_content_view_block = """\
    :goto_1
    const v0, 0x7f030012

    invoke-virtual {p0, v0}, Lcom/fungamesforfree/snipershooter/activities/MainActivity;->setContentView(I)V

    const/4 v0, 0x3

    invoke-virtual {p0, v0}, Lcom/fungamesforfree/snipershooter/activities/MainActivity;->setVolumeControlStream(I)V

    invoke-virtual {p0}, Lcom/fungamesforfree/snipershooter/activities/MainActivity;->getWindow()Landroid/view/Window;

    move-result-object v0

    const/16 v1, 0x80

    invoke-virtual {v0, v1}, Landroid/view/Window;->addFlags(I)V

    :try_start_2"""

    text = re.sub(
        r"    :goto_1\s*\n\s*:try_start_2",
        set_content_view_block,
        text,
    )

    # --- 9c: Change catch_4 handler to jump to fragment transaction ---
    # Find: goto/16 :goto_3  (after the catch_4 error logging)
    # The catch_4 handler logs the exception then jumps to goto_3 (skipping fragment).
    # Change it to jump to cond_5 (which runs the fragment transaction).
    # We need to target the specific goto after the onCreate catch handler.
    # Pattern: invoke-virtual {v1, v2, v3, v0}, .../c;->a(String,String,Throwable)V\n\n    goto/16 :goto_3\n\n    .line 289\n    :catch_5
    text = re.sub(
        r"(invoke-virtual \{v1, v2, v3, v0\}, Lcom/fungamesforfree/snipershooter/c;->a\(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;\)V\s*\n\s*)goto/16 :goto_3(\s*\n\s*\.line \d+\s*\n\s*:catch_5)",
        r"\1goto/16 :cond_5\2",
        text,
    )

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P10: NtpTime fix
# ---------------------------------------------------------------------------
def patch_ntp_time(decoded_dir: Path) -> None:
    print("[P10] Patching NtpTime (return system date instead of NTP)...")
    path = decoded_dir / "smali" / "com" / "fungamesforfree" / "e" / "a.smali"
    if not path.exists():
        print("  [skip] NtpTime file not found")
        return
    text = path.read_text(encoding="utf-8")

    text = _stub_method(
        text,
        r"\.method public static a\(\)Ljava/util/Date;",
        """\
.method public static a()Ljava/util/Date;
    .locals 1

    .prologue
    new-instance v0, Ljava/util/Date;

    invoke-direct {v0}, Ljava/util/Date;-><init>()V

    return-object v0
.end method""",
    )

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P11: Heyzap SharedPreferences mode
# ---------------------------------------------------------------------------
def patch_heyzap_prefs(decoded_dir: Path) -> None:
    print("[P11] Patching Heyzap SharedPreferences mode...")
    path = decoded_dir / "smali" / "com" / "heyzap" / "b" / "ae.smali"
    if not path.exists():
        print("  [skip] Heyzap ae.smali not found")
        return
    text = path.read_text(encoding="utf-8")

    # Change MODE_WORLD_READABLE|WRITEABLE (0x3) to MODE_PRIVATE (0x0) in constructor
    # Pattern: const/4 v1, 0x3 followed by getSharedPreferences
    text = re.sub(
        r"(const/4 v1, )0x3(\s*\n\s*invoke-virtual \{p1, v0, v1\}, Landroid/content/Context;->getSharedPreferences)",
        r"\g<1>0x0\2",
        text,
    )

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P12: PendingIntent FLAG_IMMUTABLE fixes
# ---------------------------------------------------------------------------
def patch_pending_intents(decoded_dir: Path) -> None:
    print("[P12] Patching PendingIntent flags (FLAG_IMMUTABLE)...")
    smali = decoded_dir / "smali"

    # P12a: localnotification/a.smali - getActivity flag 0x0 -> 0x4000000
    _patch_file_replace(
        smali / "com" / "fungamesforfree" / "snipershooter" / "localnotification" / "a.smali",
        "const/high16 v4, 0x0",
        "const/high16 v4, 0x4000000",
        context_after="PendingIntent;->getActivity",
    )

    # P12b: localnotification/b.smali - getBroadcast flag 0x8000000 -> 0xc000000
    _patch_file_replace(
        smali / "com" / "fungamesforfree" / "snipershooter" / "localnotification" / "b.smali",
        "const/high16 v1, 0x8000000",
        "const/high16 v1, 0xc000000",
        replace_all=True,
    )

    # P12c: o/a.smali - getBroadcast flag 0x8000000 -> 0xc000000
    _patch_file_replace(
        smali / "com" / "fungamesforfree" / "snipershooter" / "o" / "a.smali",
        "const/high16 v1, 0x8000000",
        "const/high16 v1, 0xc000000",
        replace_all=True,
    )

    # P12d: InMobi ActivityRecognitionManager$b.smali - getService flag 0x8000000 -> 0xc000000
    _patch_file_replace(
        smali / "com" / "inmobi" / "commons" / "internal" / "ActivityRecognitionManager$b.smali",
        "const/high16 v3, 0x8000000",
        "const/high16 v3, 0xc000000",
    )

    # P12e: PlayHaven GCMRegistrationRequest.smali
    # Need to add a new register for the flag since v4 is reused as both index and flag
    path = smali / "com" / "playhaven" / "android" / "push" / "GCMRegistrationRequest.smali"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        # Bump .locals 5 to .locals 6
        text = text.replace(".locals 5", ".locals 6", 1)
        # Add flag register before getBroadcast and use v5 for flags
        text = text.replace(
            "    invoke-static {p1, v4, v3, v4}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;",
            "    const/high16 v5, 0x4000000\n\n    invoke-static {p1, v4, v3, v5}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;",
        )
        path.write_text(text, encoding="utf-8")

    # P12f: PlayHaven PushReceiver.smali
    path = smali / "com" / "playhaven" / "android" / "push" / "PushReceiver.smali"
    if path.exists():
        text = path.read_text(encoding="utf-8")

        # First getBroadcast: change v3 from 0x0 to FLAG_IMMUTABLE
        text = text.replace(
            "    const/4 v3, 0x0\n\n    invoke-static {v1, v2, v0, v3}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;",
            "    const/high16 v3, 0x4000000\n\n    invoke-static {v1, v2, v0, v3}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;",
        )

        # Second getBroadcast: set v6 to FLAG_IMMUTABLE before call, reset after
        text = text.replace(
            "    invoke-static {v4, v5, v3, v6}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;\n\n    move-result-object v3",
            "    const/high16 v6, 0x4000000\n\n    invoke-static {v4, v5, v3, v6}, Landroid/app/PendingIntent;->getBroadcast(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;\n\n    move-result-object v3\n\n    const/4 v6, 0x0",
        )

        path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# P13: Background image scale fix for modern aspect ratios
# ---------------------------------------------------------------------------
def patch_background_scale(decoded_dir: Path) -> None:
    print("[P13] Patching main_fragment.xml (background scale for wide screens)...")
    path = decoded_dir / "res" / "layout" / "main_fragment.xml"
    if not path.exists():
        print("  [skip] main_fragment.xml not found")
        return
    text = path.read_text(encoding="utf-8")
    # Change centerCrop to fitCenter so the full image (including logo) is visible
    text = text.replace('android:scaleType="centerCrop"', 'android:scaleType="fitCenter"')
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _stub_method(text: str, method_pattern: str, replacement: str) -> str:
    """Replace a smali method body (from .method to .end method) with a stub."""
    # Find the method start
    m = re.search(method_pattern, text)
    if not m:
        print(f"  [warn] Method pattern not found: {method_pattern}")
        return text

    start = m.start()
    # Find the matching .end method
    end_pos = text.find("\n.end method", start)
    if end_pos == -1:
        print(f"  [warn] Could not find .end method for: {method_pattern}")
        return text
    end_pos += len("\n.end method")

    return text[:start] + replacement + text[end_pos:]


def _patch_file_replace(
    path: Path,
    old: str,
    new: str,
    replace_all: bool = False,
    context_after: str | None = None,
) -> None:
    """Replace a string in a file, optionally only when followed by context_after."""
    if not path.exists():
        print(f"  [skip] {path.name} not found")
        return

    text = path.read_text(encoding="utf-8")

    if context_after:
        # Only replace the occurrence that is followed (within ~200 chars) by context_after
        pattern = re.escape(old) + r"(.{0,200})" + re.escape(context_after)
        m = re.search(pattern, text, re.DOTALL)
        if m:
            text = text[:m.start()] + new + m.group(0)[len(old):] + text[m.end():]
    elif replace_all:
        text = text.replace(old, new)
    else:
        text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Patch Sniper Shooter APK for modern Android compatibility"
    )
    parser.add_argument("input_apk", help="Path to the original APK file")
    parser.add_argument(
        "output_apk",
        nargs="?",
        default=None,
        help="Output APK path (default: <input>_patched.apk)",
    )
    parser.add_argument(
        "--apktool",
        default=None,
        help="Path to apktool.jar",
    )
    parser.add_argument(
        "--signer",
        default=None,
        help="Path to uber-apk-signer.jar",
    )
    args = parser.parse_args()

    input_apk = Path(args.input_apk).resolve()
    if not input_apk.exists():
        print(f"Error: Input APK not found: {input_apk}")
        sys.exit(1)

    output_apk = (
        Path(args.output_apk).resolve()
        if args.output_apk
        else input_apk.with_name(input_apk.stem + "_patched.apk")
    )

    apktool = args.apktool or find_tool("apktool.jar")
    signer = args.signer or find_tool("uber-apk-signer.jar")

    decoded_dir = input_apk.parent / "decoded_tmp"

    print(f"Input:  {input_apk}")
    print(f"Output: {output_apk}")
    print()

    # Step 1: Decompile
    print("=== Step 1: Decompiling APK ===")
    if decoded_dir.exists():
        shutil.rmtree(decoded_dir)
    run(["java", "-jar", str(apktool), "d", str(input_apk), "-o", str(decoded_dir)])
    print()

    # Step 2: Apply patches
    print("=== Step 2: Applying patches ===")
    patch_apktool_yml(decoded_dir)
    patch_manifest(decoded_dir)
    patch_network_security_config(decoded_dir)
    patch_base_game_activity(decoded_dir)
    patch_game_helper(decoded_dir)
    patch_crashlytics(decoded_dir)
    patch_flurry(decoded_dir)
    patch_ads_manager(decoded_dir)
    patch_main_activity(decoded_dir)
    patch_ntp_time(decoded_dir)
    patch_heyzap_prefs(decoded_dir)
    patch_pending_intents(decoded_dir)
    patch_background_scale(decoded_dir)
    print()

    # Step 3: Rebuild
    print("=== Step 3: Rebuilding APK ===")
    run(["java", "-jar", str(apktool), "b", str(decoded_dir), "-o", str(output_apk)])
    print()

    # Step 4: Sign
    print("=== Step 4: Signing APK ===")
    run(["java", "-jar", str(signer), "-a", str(output_apk), "--overwrite"])
    print()

    # Cleanup
    print("=== Cleanup ===")
    shutil.rmtree(decoded_dir)
    print(f"Removed temporary directory: {decoded_dir}")
    print()

    print(f"Done! Patched APK: {output_apk}")


if __name__ == "__main__":
    main()
