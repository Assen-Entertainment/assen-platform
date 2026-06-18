import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/selection_controls.dart';
import 'package:ui_kit/src/molecules/list_item.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';

/// Handles a local preference switch change from the F4 notification template.
///
/// The app layer owns state and side effects because ASS-143 is a mock-only
/// surface until the ASS-113 notification body replaces it.
typedef AssenNotificationPrefChanged =
    void Function(
      String id, {
      required bool enabled,
    });

/// One notification preference row in the fan-facing F4 settings screen.
///
/// ASS-143 keeps this typed and copy-led so unavailable categories cannot drift
/// into the screen while notification delivery is still mocked locally.
class AssenNotificationPref {
  /// Creates a notification preference row model.
  const AssenNotificationPref({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.enabled,
    this.disabled = false,
  });

  /// Stable preference id used by the app-local state map.
  final String id;

  /// Primary row copy approved for the F4 mock.
  final String title;

  /// Secondary row copy approved for the F4 mock.
  final String subtitle;

  /// Whether the preference is currently on.
  final bool enabled;

  /// Whether the control is unavailable because a parent consent is off.
  final bool disabled;
}

/// Fan-facing notification settings screen template (F4).
///
/// The template owns only layout and token-based controls. Persistence, actual
/// push delivery, and legal consent timestamps stay out of ui_kit and are
/// intentionally mocked by the app until ASS-113 replaces this local surface.
class AssenNotificationSettingsTemplate extends StatelessWidget {
  /// Creates the F4 notification settings template.
  const AssenNotificationSettingsTemplate({
    required this.servicePreferences,
    required this.benefitPreferences,
    required this.onPreferenceChanged,
    this.onBack,
    super.key,
  });

  /// Service notification rows shown in the first section.
  final List<AssenNotificationPref> servicePreferences;

  /// Advertising/benefit notification rows shown after the divider band.
  final List<AssenNotificationPref> benefitPreferences;

  /// Called when an enabled switch changes.
  final AssenNotificationPrefChanged onPreferenceChanged;

  /// Optional back handler for nested fan-app routes.
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '알림', onBack: onBack),
      body: ListView(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              SpacingTokens.screenMargin,
              SpacingTokens.s5,
              SpacingTokens.screenMargin,
              SpacingTokens.s3,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '알림',
                  style: TypographyTokens.titleL.copyWith(
                    color: colors.ink900,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  '서비스 알림',
                  style: TypographyTokens.captionMicro.copyWith(
                    color: colors.ink500,
                  ),
                ),
              ],
            ),
          ),
          for (final pref in servicePreferences)
            _NotificationPreferenceRow(
              pref: pref,
              onPreferenceChanged: onPreferenceChanged,
            ),
          Container(height: SpacingTokens.s2, color: colors.cream100),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              SpacingTokens.screenMargin,
              SpacingTokens.s5,
              SpacingTokens.screenMargin,
              SpacingTokens.s2,
            ),
            child: Text(
              '혜택(광고성) 알림',
              style: TypographyTokens.titleL.copyWith(
                color: colors.ink900,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          for (final pref in benefitPreferences)
            _NotificationPreferenceRow(
              pref: pref,
              onPreferenceChanged: onPreferenceChanged,
            ),
        ],
      ),
    );
  }
}

/// The Scaffold-less notification-settings body for embedding in a list-detail
/// pane (ASS-147 Slice 4): the same service/benefit preference sections as
/// [AssenNotificationSettingsTemplate] but WITHOUT a [Scaffold] or
/// [AssenAppBar], so it mounts as the detail pane of the My hub. The
/// route-built full-Scaffold template is unchanged.
class AssenNotificationSettingsBody extends StatelessWidget {
  /// Creates an embeddable notification-settings body.
  const AssenNotificationSettingsBody({
    required this.servicePreferences,
    required this.benefitPreferences,
    required this.onPreferenceChanged,
    super.key,
  });

  /// Service notification rows shown in the first section.
  final List<AssenNotificationPref> servicePreferences;

  /// Advertising/benefit notification rows shown after the divider band.
  final List<AssenNotificationPref> benefitPreferences;

  /// Called when an enabled switch changes.
  final AssenNotificationPrefChanged onPreferenceChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.screenMargin,
            SpacingTokens.s5,
            SpacingTokens.screenMargin,
            SpacingTokens.s3,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '알림',
                style: TypographyTokens.titleL.copyWith(
                  color: colors.ink900,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: SpacingTokens.s1),
              Text(
                '서비스 알림',
                style: TypographyTokens.captionMicro.copyWith(
                  color: colors.ink500,
                ),
              ),
            ],
          ),
        ),
        for (final pref in servicePreferences)
          _NotificationPreferenceRow(
            pref: pref,
            onPreferenceChanged: onPreferenceChanged,
          ),
        Container(height: SpacingTokens.s2, color: colors.cream100),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.screenMargin,
            SpacingTokens.s5,
            SpacingTokens.screenMargin,
            SpacingTokens.s2,
          ),
          child: Text(
            '혜택(광고성) 알림',
            style: TypographyTokens.titleL.copyWith(
              color: colors.ink900,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        for (final pref in benefitPreferences)
          _NotificationPreferenceRow(
            pref: pref,
            onPreferenceChanged: onPreferenceChanged,
          ),
      ],
    );
  }
}

class _NotificationPreferenceRow extends StatelessWidget {
  const _NotificationPreferenceRow({
    required this.pref,
    required this.onPreferenceChanged,
  });

  final AssenNotificationPref pref;
  final AssenNotificationPrefChanged onPreferenceChanged;

  @override
  Widget build(BuildContext context) {
    return AssenListItem(
      title: pref.title,
      subtitle: pref.subtitle,
      showChevron: false,
      trailing: AssenSwitch(
        key: ValueKey<String>('notification-${pref.id}'),
        value: pref.enabled,
        onChanged: pref.disabled
            ? null
            : (enabled) => onPreferenceChanged(pref.id, enabled: enabled),
      ),
    );
  }
}
