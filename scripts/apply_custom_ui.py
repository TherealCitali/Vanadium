#!/usr/bin/env python3
import os, sys

def main():
    print("Executing Vanadium Custom UI & App Lock modification script...")
    src_dir = os.path.abspath("src")
    if not os.path.exists(src_dir):
        src_dir = os.getcwd()

    # 1. Overriding colors for OLED Pitch Black (#000000) Theme
    colors_night_path = os.path.join(src_dir, "chrome/android/java/res/values-night/colors.xml")
    if os.path.exists(colors_night_path):
        with open(colors_night_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        oled_colors = """
    <!-- OLED Pitch Black (#000000) Theme Overrides -->
    <color name="global_bg_color_dark">#000000</color>
    <color name="default_bg_color_dark">#000000</color>
    <color name="toolbar_bg_color_dark">#000000</color>
    <color name="ntp_bg_dark">#000000</color>
    <color name="tab_grid_bg_color_dark">#000000</color>
    <color name="bottom_sheet_bg_color_dark">#000000</color>
    <color name="card_bg_color_dark">#080808</color>
    <color name="omnibox_bg_color_dark">#121212</color>
"""
        if "</resources>" in content:
            content = content.replace("</resources>", f"{oled_colors}\n</resources>")
            with open(colors_night_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Successfully applied OLED Pitch Black theme to chrome/android/java/res/values-night/colors.xml")

    # 2. Overriding browser UI styles for OLED Pitch Black
    styles_colors_night_path = os.path.join(src_dir, "components/browser_ui/styles/android/java/res/values-night/colors.xml")
    if os.path.exists(styles_colors_night_path):
        with open(styles_colors_night_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        style_colors = """
    <!-- OLED Pitch Black (#000000) Styles Overrides -->
    <color name="default_bg_color_baseline_dark">#000000</color>
    <color name="default_bg_color_elevated_1_dark">#050505</color>
    <color name="default_bg_color_elevated_2_dark">#0A0A0A</color>
"""
        if "</resources>" in content:
            content = content.replace("</resources>", f"{style_colors}\n</resources>")
            with open(styles_colors_night_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Successfully applied OLED Pitch Black theme to components/browser_ui/styles/android/java/res/values-night/colors.xml")

    # 3. Create VanadiumAppLockManager.java
    app_lock_dir = os.path.join(src_dir, "chrome/android/java/src/org/chromium/chrome/browser/app")
    os.makedirs(app_lock_dir, exist_ok=True)
    app_lock_file = os.path.join(app_lock_dir, "VanadiumAppLockManager.java")
    
    app_lock_code = """// Copyright 2026 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package org.chromium.chrome.browser.app;

import android.content.Context;
import android.text.InputType;
import android.widget.EditText;
import androidx.appcompat.app.AlertDialog;
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.fragment.app.FragmentActivity;
import org.chromium.chrome.browser.preferences.ChromeSharedPreferences;
import java.security.MessageDigest;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

/**
 * Manages App Lock using Hardware Fingerprint (Device Biometrics) with Instant Fallback
 * to an Internal Custom App PIN whenever biometrics are unavailable or unconfigured.
 */
public class VanadiumAppLockManager {
    private static final String PREF_APP_LOCK_ENABLED = "vanadium_app_lock_enabled";
    private static final String PREF_INTERNAL_PIN_HASH = "vanadium_internal_pin_hash";
    private static boolean sIsUnlocked = false;

    public static boolean isAppLockEnabled() {
        return ChromeSharedPreferences.getInstance().readBoolean(PREF_APP_LOCK_ENABLED, false);
    }

    public static void setAppLockEnabled(boolean enabled) {
        ChromeSharedPreferences.getInstance().writeBoolean(PREF_APP_LOCK_ENABLED, enabled);
    }

    public static boolean hasInternalPin() {
        String hash = ChromeSharedPreferences.getInstance().readString(PREF_INTERNAL_PIN_HASH, "");
        return hash != null && !hash.isEmpty();
    }

    public static void setInternalPin(String pin) {
        String hash = hashPin(pin);
        ChromeSharedPreferences.getInstance().writeString(PREF_INTERNAL_PIN_HASH, hash);
    }

    public static boolean verifyInternalPin(String pin) {
        String savedHash = ChromeSharedPreferences.getInstance().readString(PREF_INTERNAL_PIN_HASH, "");
        return savedHash != null && savedHash.equals(hashPin(pin));
    }

    private static String hashPin(String pin) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(pin.getBytes("UTF-8"));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (Exception e) {
            return pin;
        }
    }

    public static boolean isUnlocked() {
        return !isAppLockEnabled() || sIsUnlocked;
    }

    public static void lockApp() {
        sIsUnlocked = false;
    }

    public static void authenticate(FragmentActivity activity, Runnable onSuccess) {
        if (!isAppLockEnabled() || sIsUnlocked) {
            if (onSuccess != null) onSuccess.run();
            return;
        }

        BiometricManager biometricManager = BiometricManager.from(activity);
        int authenticators = BiometricManager.Authenticators.BIOMETRIC_STRONG
                | BiometricManager.Authenticators.BIOMETRIC_WEAK;
        int canAuth = biometricManager.canAuthenticate(authenticators);

        if (canAuth != BiometricManager.BIOMETRIC_SUCCESS) {
            showInternalPinDialog(activity, onSuccess);
            return;
        }

        Executor executor = Executors.newSingleThreadExecutor();
        BiometricPrompt biometricPrompt = new BiometricPrompt(activity, executor,
                new BiometricPrompt.AuthenticationCallback() {
                    @Override
                    public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                        super.onAuthenticationSucceeded(result);
                        sIsUnlocked = true;
                        if (onSuccess != null) {
                            activity.runOnUiThread(onSuccess);
                        }
                    }

                    @Override
                    public void onAuthenticationError(int errorCode, CharSequence errString) {
                        super.onAuthenticationError(errorCode, errString);
                        activity.runOnUiThread(() -> showInternalPinDialog(activity, onSuccess));
                    }
                });

        BiometricPrompt.PromptInfo promptInfo = new BiometricPrompt.PromptInfo.Builder()
                .setTitle("Unlock Vanadium")
                .setSubtitle("Use Fingerprint or Internal PIN")
                .setNegativeButtonText("Use Internal PIN")
                .setAllowedAuthenticators(authenticators)
                .build();

        biometricPrompt.authenticate(promptInfo);
    }

    public static void showInternalPinDialog(FragmentActivity activity, Runnable onSuccess) {
        AlertDialog.Builder builder = new AlertDialog.Builder(activity);
        builder.setTitle(hasInternalPin() ? "Enter Internal PIN" : "Set Internal PIN");

        final EditText input = new EditText(activity);
        input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        builder.setView(input);

        builder.setPositiveButton("OK", (dialog, which) -> {
            String pin = input.getText().toString();
            if (!hasInternalPin()) {
                setInternalPin(pin);
                sIsUnlocked = true;
                if (onSuccess != null) onSuccess.run();
            } else if (verifyInternalPin(pin)) {
                sIsUnlocked = true;
                if (onSuccess != null) onSuccess.run();
            } else {
                showInternalPinDialog(activity, onSuccess);
            }
        });
        builder.setCancelable(false);
        builder.show();
    }
}
"""
    with open(app_lock_file, "w", encoding="utf-8") as f:
        f.write(app_lock_code)
    print(f"Successfully generated {app_lock_file}")

if __name__ == "__main__":
    main()
