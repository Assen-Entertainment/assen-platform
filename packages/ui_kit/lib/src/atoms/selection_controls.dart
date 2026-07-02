import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Shared minimum hit target for selection controls (Apple HIG / Korean B2C).
const double _selectionMinTarget = 44;

/// A design-system checkbox (`checked / unchecked / disabled`).
///
/// Covers the Inputs/Checkbox row of `components.md`. Used for individual
/// agreement rows and multi-select lists. The checked fill is the solid action
/// anchor (`RefColors.roseMain`); the unchecked border uses the ink ramp.
/// Disabled is a null [onChanged]. Tap target is padded to 44pt.
class AssenCheckbox extends StatelessWidget {
  /// Creates a checkbox reflecting [value].
  ///
  /// [onChanged] receives the next value; null disables the control.
  const AssenCheckbox({
    required this.value,
    required this.onChanged,
    super.key,
  });

  /// Whether the box is checked.
  final bool value;

  /// Called with the toggled value. Null disables the control.
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return SizedBox(
      width: _selectionMinTarget,
      height: _selectionMinTarget,
      child: Checkbox(
        value: value,
        onChanged: onChanged == null
            ? null
            : (next) => onChanged!(next ?? false),
        activeColor: colors.roseMain,
        checkColor: colors.white,
        side: BorderSide(color: colors.ink300, width: 2),
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(RadiusTokens.xs)),
        ),
      ),
    );
  }
}

/// A design-system radio button (`selected / unselected / disabled`).
///
/// Covers the Inputs/Radio row of `components.md`. Generic over the option type
/// [T] so a group binds to a domain enum or id. The selected dot is the solid
/// action anchor; the ring uses the ink ramp. Null [onChanged] disables it.
class AssenRadio<T> extends StatelessWidget {
  /// Creates a radio for option [value] within a group whose current selection
  /// is [groupValue].
  ///
  /// [onChanged] fires with [value] when this option is chosen; null disables.
  const AssenRadio({
    required this.value,
    required this.groupValue,
    required this.onChanged,
    super.key,
  });

  /// The value this radio represents.
  final T value;

  /// The currently selected value of the group ([value] is selected when they
  /// are equal).
  final T? groupValue;

  /// Called with [value] when chosen. Null disables the control.
  final ValueChanged<T>? onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    // Flutter 3.32+ moved selection state onto a [RadioGroup] ancestor (the old
    // per-Radio groupValue/onChanged are deprecated). Each atom owns a tiny
    // group so the public API stays value/groupValue/onChanged while the modern
    // widget does the work.
    return RadioGroup<T>(
      groupValue: groupValue,
      onChanged: onChanged == null
          ? (_) {}
          : (next) {
              if (next != null) onChanged!(next);
            },
      child: SizedBox(
        width: _selectionMinTarget,
        height: _selectionMinTarget,
        child: Radio<T>(
          value: value,
          enabled: onChanged != null,
          activeColor: colors.roseMain,
          fillColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) return colors.ink300;
            if (states.contains(WidgetState.selected)) return colors.roseMain;
            return colors.ink300;
          }),
        ),
      ),
    );
  }
}

/// A design-system switch (`on / off / disabled`).
///
/// Covers the Inputs/Switch row of `components.md`. Used for settings and the
/// information/advertising push toggles (Korean B2C convention #4). The on
/// track is the solid action anchor; the off track uses the ink ramp.
class AssenSwitch extends StatelessWidget {
  /// Creates a switch reflecting [value].
  ///
  /// [onChanged] receives the next value; null disables the control.
  const AssenSwitch({
    required this.value,
    required this.onChanged,
    super.key,
  });

  /// Whether the switch is on.
  final bool value;

  /// Called with the toggled value. Null disables the control.
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Switch(
      value: value,
      onChanged: onChanged,
      activeThumbColor: colors.white,
      activeTrackColor: colors.roseMain,
      inactiveThumbColor: colors.white,
      inactiveTrackColor: colors.ink300,
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
    );
  }
}
