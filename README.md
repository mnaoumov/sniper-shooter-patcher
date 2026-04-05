# Sniper Shooter APK Patcher

Patches the original **Sniper Shooter Free - Fun Game v2.9.2** APK to run on modern Android (6.0+).

The original APK was built for Android 2.2 (SDK 8) and crashes on anything above Android 10 due to
deprecated APIs, removed SDK features, and stricter security policies.

## Original APK

`original.apk` - Sniper Shooter Free v2.9.2, sourced from https://www.apksum.com/app/sniper-shooter/com.fungamesforfree.snipershooter.free

## Prerequisites

- Java 11+
- Python 3.8+
- [`apktool.jar`](https://apktool.org/) (v2.11.1+)
- [`uber-apk-signer.jar`](https://github.com/nicehash/uber-apk-signer)

Place the `.jar` files in the same directory as `patch.py`, or pass paths via `--apktool` / `--signer`.

## Usage

```bash
py patch.py original.apk patched.apk
```

Or with explicit tool paths:

```bash
py patch.py original.apk patched.apk --apktool /path/to/apktool.jar --signer /path/to/uber-apk-signer.jar
```

Then install on device:

```bash
adb install patched.apk
```

## What it does

See [CLAUDE.md](CLAUDE.md) for detailed documentation of all 12 patches applied.

Summary:
- Updates SDK version targets (8/18 -> 23/30)
- Adds network security config for cleartext HTTP
- Stubs out dead ad SDKs (Heyzap, InMobi, Chartboost, PlayHaven, Flurry)
- Stubs out dead analytics (Crashlytics, Google Analytics)
- Stubs out Google Play Games Services
- Fixes PendingIntent flags for Android 12+
- Fixes SharedPreferences security modes
- Fixes NTP time sync (uses system time instead)
- Fixes MainActivity fragment transaction error handling
