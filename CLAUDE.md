# Sniper Shooter APK Patcher

## Project Purpose

Automated patcher that takes the original **Sniper Shooter Free - Fun Game v2.9.2** APK
(built for Android 2.2+ / SDK 8, targeting SDK 18) and patches it to run on modern
Android (6.0+ / SDK 23, targeting SDK 30).

The original APK crashes or fails to install on Android 11+ due to deprecated APIs,
removed SDK features, and stricter security policies introduced over many Android versions.

## How It Works

1. Decompiles the APK with `apktool`
2. Applies a series of smali bytecode patches and manifest/config changes
3. Rebuilds the APK with `apktool`
4. Signs with `uber-apk-signer` (v1+v2+v3 signatures)

## Prerequisites

- Java 11+ (for apktool and uber-apk-signer)
- Python 3.8+
- `apktool.jar` (v2.11.1+) in working directory or PATH
- `uber-apk-signer.jar` in working directory or PATH
- `debug.keystore` in working directory (auto-generated if missing)

## Patches Applied (in order)

### P1. SDK Version Update (`apktool.yml`)
- `minSdkVersion`: 8 -> 23
- `targetSdkVersion`: 18 -> 30
- **Why**: SDK 23 is minimum for modern devices; SDK 30 avoids SDK 31+ strict requirements
  (exported attributes, PendingIntent flags, registerReceiver flags) while still being
  installable on Android 14+.

### P2. AndroidManifest.xml
- Add `android:networkSecurityConfig="@xml/network_security_config"` to `<application>`
- Add `android:usesCleartextTraffic="true"` to `<application>`
- Add `<uses-library android:name="org.apache.http.legacy" android:required="false"/>` inside `<application>`
- Add `android:exported="true"` to all activities/receivers with intent-filters
- Add `android:exported="false"` to all activities/receivers without intent-filters
- **Why**: SDK 28+ blocks cleartext HTTP by default; SDK 28+ removed Apache HTTP classes
  (Heyzap SDK uses `org.apache.http.conn.scheme.SchemeRegistry`); SDK 31+ requires explicit `exported`.

### P3. Network Security Config (new file: `res/xml/network_security_config.xml`)
- Allows cleartext (HTTP) traffic with system certificate trust
- **Why**: Game servers and ad SDKs use HTTP URLs.

### P4. BaseGameActivity Stub (`com/google/b/a/a/a.smali`)
- Replace entire file with a stub that:
  - Extends `android/support/v4/app/i` (FragmentActivity)
  - Initializes GameHelper field in constructor
  - Makes all lifecycle methods (onCreate, onStart, onStop, onActivityResult) just call super
  - Returns null/false for all helper methods
- **Why**: Google Play Games Services SDK is too old and crashes on modern devices.

### P5. GameHelper Stub (`com/google/b/a/a/b.smali`)
- Stub `a(String, String)` dialog method to return immediately (was showing AlertDialog that crashed)
- Stub `c()` to return null instead of throwing (returns GamesClient)
- **Why**: These methods reference removed Play Games APIs.

### P6. Crashlytics Stub (`com/b/a/d.smali`)
- Stub `a(Context)` init method to return immediately
- Stub `a(Throwable)` logException to no-op
- **Why**: Old Fabric Crashlytics SDK is defunct.

### P7. Flurry Analytics Stub (`com/flurry/android/FlurryAgent.smali`)
- Stub `setUseHttps(Z)V` to return immediately
- Stub `onStartSession(Context, String)V` to return immediately
- Stub `onEndSession(Context)V` to return immediately
- Stub `logEvent(String)V` to return immediately
- **Why**: Old Flurry SDK makes network calls that fail.

### P8. AdsManager Stub (`com/fungamesforfree/snipershooter/r/a.smali`)
- Stub `a(Activity, ViewGroup)V` to return immediately
- **Why**: All ad SDKs (Heyzap, InMobi, Chartboost, PlayHaven) are defunct.

### P9. MainActivity Fixes (`com/fungamesforfree/snipershooter/activities/MainActivity.smali`)
- **StrictMode**: Add `StrictMode.ThreadPolicy.Builder().permitAll()` at start of `onCreate`
  - **Why**: Legacy code does network I/O on main thread (NTP sync, ad fetches)
- **setContentView before try**: Move `setContentView`, `setVolumeControlStream`, and
  `addFlags(FLAG_KEEP_SCREEN_ON)` out of the try-catch block that wraps SDK initialization
  - **Why**: When ad/analytics SDKs throw, the catch handler skipped setContentView -> black screen
- **Fragment transaction on exception**: Change catch_4 handler to jump to fragment transaction
  (`goto cond_5`) instead of skipping it (`goto goto_3`)
  - **Why**: Even if SDK init fails, the game fragment must still be added to the UI

### P10. NtpTime Fix (`com/fungamesforfree/e/a.smali`)
- Replace `a()Date` method body: instead of connecting to `0.pool.ntp.org`, just return `new Date()`
- **Why**: NTP network call on main thread causes NetworkOnMainThreadException.

### P11. Heyzap SharedPreferences Fix (`com/heyzap/b/ae.smali`)
- Change SharedPreferences mode from `0x3` (MODE_WORLD_READABLE|MODE_WORLD_WRITEABLE) to `0x0` (MODE_PRIVATE)
- **Why**: MODE_WORLD_READABLE/WRITEABLE throw SecurityException on SDK 24+.

### P12. PendingIntent FLAG_IMMUTABLE (6 files)
All PendingIntent creation calls need FLAG_IMMUTABLE (0x4000000) on SDK 31+.
Even though we target SDK 30, adding them is harmless and future-proofs.

Files patched:
- `com/fungamesforfree/snipershooter/localnotification/a.smali` - getActivity: 0x0 -> 0x4000000
- `com/fungamesforfree/snipershooter/localnotification/b.smali` - getBroadcast: 0x8000000 -> 0xc000000 (two locations)
- `com/fungamesforfree/snipershooter/o/a.smali` - getBroadcast: 0x8000000 -> 0xc000000 (two locations)
- `com/inmobi/commons/internal/ActivityRecognitionManager$b.smali` - getService: 0x8000000 -> 0xc000000
- `com/playhaven/android/push/GCMRegistrationRequest.smali` - getBroadcast: add v5=0x4000000 flag
- `com/playhaven/android/push/PushReceiver.smali` - getBroadcast: set v6=0x4000000 before call, reset to 0 after

### P14. ShopManager Purchase Bypass (`com/fungamesforfree/snipershooter/r/ag.smali`)
- Stub `a(String, am)V` (the purchase launch method) to bypass Google Play IAB
- Instead of calling IabHelper.launchPurchaseFlow, directly:
  - Convert SKU to weapon name via `d/a.a(String)`
  - Find matching weapon in the weapons list
  - Call `GameData.purchaseWeapon(weaponId)` to mark weapon as owned
  - Call `GameData.setUserBoughtSomething(true)`
  - Invoke the success callback with `PurchaseResult.ItemPurchased`
- **Why**: The game used Google Play In-App Billing for weapon purchases (not local coins).
  Since the game is delisted from Google Play, the billing service is unavailable and all
  purchases fail with "Purchase failed! Please check your network connection." This patch
  makes all weapon purchases succeed locally without requiring Google Play.

## Architecture Notes

- The game is a **pure Java/Android app** (no native .so libraries, no game engine like Unity/Cocos)
- Uses Android `Fragment` system for UI (support library v4)
- The main menu fragment is `com/fungamesforfree/snipershooter/l/bn.smali`
- Layout: `main.xml` has a `FrameLayout` container; fragment `bn` inflates `main_fragment.xml`
- Obfuscated class names (ProGuard): single-letter package/class names throughout
- Ad SDKs included: Heyzap, InMobi, Chartboost, PlayHaven, Google AdMob, Flurry
- Analytics: Crashlytics (Fabric), Flurry, Google Analytics
- The `.source` annotations in smali reveal original Java filenames

## Debugging Tips

- Use `adb logcat -s AndroidRuntime:E` to find fatal exceptions
- The `onCreate` catch blocks in MainActivity silently swallow exceptions - check `System.err` too
- `TransparentWindowDetector: Detect Empty window` in logcat = setContentView wasn't called or fragment wasn't added
- PendingIntent crashes show as `IllegalArgumentException` with "RECEIVER_EXPORTED or RECEIVER_NOT_EXPORTED"
- SharedPreferences mode crashes show as `SecurityException: MODE_WORLD_READABLE no longer supported`

## Known Limitations

- Google Play Games integration is fully disabled (leaderboards, achievements won't work)
- All ad networks are disabled (no ads will show)
- Analytics/crash reporting is disabled
- The game data/saves are local only
