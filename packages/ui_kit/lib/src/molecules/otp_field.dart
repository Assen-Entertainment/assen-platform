import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Completion/validation status of an [AssenOtpField].
enum AssenOtpStatus {
  /// 입력중 — the user is still entering digits (resting/active styling).
  entering,

  /// 완료 — all digits entered and accepted (matcha success border).
  complete,

  /// 오류 — the code was rejected (`red.main` border + message).
  error,
}

/// A 6-digit one-time-password field (`입력중 / 완료 / 오류`).
///
/// Covers the Inputs/OTPField row of `components.md` and the Korean identity
/// verification convention #5 (본인인증 — the standard flow ends in a 6-digit
/// OTP). Renders [length] cells (6 by default) over a single hidden input so
/// the platform autofill / SMS-code suggestion still works. The focused cell is
/// outlined in the rose action anchor; [status] recolours every cell
/// (matcha when complete, `red.main` on error). Solid fills only.
///
/// Accessibility: the underlying field is a real text input with a semantics
/// label, so the cells are decorative and the value is announced as one string.
class AssenOtpField extends StatefulWidget {
  /// Creates a 6-digit OTP field.
  ///
  /// [onChanged] fires as digits change; [onCompleted] fires once exactly
  /// [length] digits are present. [status] drives the success/error styling
  /// (the caller flips it after verifying the code server-side).
  const AssenOtpField({
    required this.onChanged,
    this.onCompleted,
    this.length = 6,
    this.status = AssenOtpStatus.entering,
    this.errorText,
    super.key,
  });

  /// Called whenever the entered code changes.
  final ValueChanged<String> onChanged;

  /// Called once the code reaches [length] digits.
  final ValueChanged<String>? onCompleted;

  /// Number of digit cells. Defaults to 6 (Korean OTP standard).
  final int length;

  /// Completion/validation status — drives cell colour.
  final AssenOtpStatus status;

  /// Optional message shown under the cells in the [AssenOtpStatus.error]
  /// state.
  final String? errorText;

  @override
  State<AssenOtpField> createState() => _AssenOtpFieldState();
}

class _AssenOtpFieldState extends State<AssenOtpField> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _controller.addListener(_handleChange);
  }

  @override
  void dispose() {
    _controller
      ..removeListener(_handleChange)
      ..dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleChange() {
    final text = _controller.text;
    widget.onChanged(text);
    if (text.length == widget.length) widget.onCompleted?.call(text);
    setState(() {});
  }

  /// Moves focus into the hidden input when the visible cells are tapped.
  void _focus() => _focusNode.requestFocus();

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final filled = _controller.text.length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // The real input sits in a zero-size box; the visible cells mirror it.
        SizedBox.shrink(
          child: TextField(
            controller: _controller,
            focusNode: _focusNode,
            keyboardType: TextInputType.number,
            maxLength: widget.length,
            autofillHints: const [AutofillHints.oneTimeCode],
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: const InputDecoration(counterText: ''),
          ),
        ),
        Semantics(
          label: '인증번호 ${widget.length}자리',
          textField: true,
          value: _controller.text,
          child: GestureDetector(
            onTap: _focus,
            child: Row(
              children: List.generate(widget.length, (i) {
                final hasDigit = i < filled;
                final isCursor = i == filled && _focusNode.hasFocus;
                return Expanded(
                  child: Padding(
                    padding: EdgeInsets.only(
                      right: i == widget.length - 1 ? 0 : SpacingTokens.s2,
                    ),
                    child: _Cell(
                      digit: hasDigit ? _controller.text[i] : '',
                      isCursor: isCursor,
                      status: widget.status,
                      colors: colors,
                    ),
                  ),
                );
              }),
            ),
          ),
        ),
        if (widget.status == AssenOtpStatus.error && widget.errorText != null)
          Padding(
            padding: const EdgeInsets.only(top: SpacingTokens.s2),
            child: Text(
              widget.errorText!,
              style: TextStyle(
                color: colors.redMain,
                fontSize: TypographyTokens.bodySSize,
              ),
            ),
          ),
      ],
    );
  }
}

/// One OTP digit cell — decorative; the value lives in the hidden field.
class _Cell extends StatelessWidget {
  const _Cell({
    required this.digit,
    required this.isCursor,
    required this.status,
    required this.colors,
  });

  final String digit;
  final bool isCursor;
  final AssenOtpStatus status;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    final Color border;
    if (status == AssenOtpStatus.error) {
      border = colors.redMain;
    } else if (status == AssenOtpStatus.complete) {
      border = colors.matchaBorder;
    } else if (isCursor) {
      border = colors.roseMain;
    } else {
      border = colors.ink200;
    }

    return Container(
      height: SpacingTokens.s12,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: colors.white,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        border: Border.all(color: border, width: isCursor ? 2 : 1),
      ),
      child: Text(
        digit,
        style: TextStyle(
          fontSize: TypographyTokens.headlineSize,
          fontWeight: FontWeight.w700,
          color: colors.ink900,
        ),
      ),
    );
  }
}
