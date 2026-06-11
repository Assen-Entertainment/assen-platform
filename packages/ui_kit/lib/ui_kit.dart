/// Assen Platform design system: ThemeData and shared widgets.
///
/// Apps must theme through this package rather than hard-coding colours. The
/// Atoms layer (ASS-88) lives under `src/atoms/`; every public widget reads its
/// colour/spacing/radius from `core_tokens` (never a hard-coded value). The
/// `AtomCatalog` gallery (src/catalog.dart) renders every atom for visual
/// review.
library;

export 'src/atoms/avatar.dart';
export 'src/atoms/badges.dart';
export 'src/atoms/button.dart';
export 'src/atoms/card.dart';
export 'src/atoms/chips.dart';
export 'src/atoms/divider.dart';
export 'src/atoms/favorite_button.dart';
export 'src/atoms/icon_button.dart';
export 'src/atoms/progress.dart';
export 'src/atoms/selection_controls.dart';
export 'src/atoms/skeleton.dart';
export 'src/catalog.dart';
export 'src/theme.dart';
export 'src/token_swatch.dart';
