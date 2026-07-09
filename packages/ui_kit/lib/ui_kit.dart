/// Assen Platform design system: ThemeData and shared widgets.
///
/// Apps must theme through this package rather than hard-coding colours. The
/// Atoms layer (ASS-88) lives under `src/atoms/`, the Molecules layer (the
/// `04 Molecules` Figma page) under `src/molecules/`, and the Organisms layer
/// (the `05 Organisms` page) under `src/organisms/`; every public widget reads
/// its colour/spacing/radius from `core_tokens` (never a hard-coded value). The
/// `AtomCatalog`, `MoleculeCatalog` and `OrganismCatalog` galleries render
/// every component for visual review. The library is domain-agnostic — it
/// mirrors the web design system (`web/src/components/ui`); product screens
/// live in `apps/assen_mobile`, never here.
library;

export 'src/atoms/avatar.dart';
export 'src/atoms/badges.dart';
export 'src/atoms/button.dart';
export 'src/atoms/card.dart';
export 'src/atoms/chips.dart';
export 'src/atoms/divider.dart';
export 'src/atoms/favorite_button.dart';
export 'src/atoms/icon_button.dart';
export 'src/atoms/logo.dart';
export 'src/atoms/progress.dart';
export 'src/atoms/selection_controls.dart';
export 'src/atoms/skeleton.dart';
export 'src/catalog.dart';
export 'src/creator_accent.dart';
export 'src/layout/adaptive_shell.dart';
export 'src/layout/content_column.dart';
export 'src/layout/feed_grid.dart';
export 'src/layout/list_detail_scaffold.dart';
export 'src/layout/sidebar_shell.dart';
export 'src/layout/supporting_pane_scaffold.dart';
export 'src/layout/window_size.dart';
export 'src/molecule_catalog.dart';
export 'src/molecules/agreement_cell.dart';
export 'src/molecules/banner_card.dart';
export 'src/molecules/key_value_row.dart';
export 'src/molecules/list_item.dart';
export 'src/molecules/notice_bar.dart';
export 'src/molecules/otp_field.dart';
export 'src/molecules/search_field.dart';
export 'src/molecules/section_header.dart';
export 'src/molecules/segmented_tabs.dart';
export 'src/molecules/stat_card.dart';
export 'src/molecules/stat_row.dart';
export 'src/molecules/step_indicator.dart';
export 'src/molecules/stepper.dart';
export 'src/molecules/text_field.dart';
export 'src/molecules/timeline_item.dart';
export 'src/molecules/toast.dart';
export 'src/molecules/underline_tabs.dart';
export 'src/organism_catalog.dart';
export 'src/organisms/app_bar.dart';
export 'src/organisms/bottom_cta.dart';
export 'src/organisms/bottom_sheet.dart';
export 'src/organisms/cover_header.dart';
export 'src/organisms/dialog.dart';
export 'src/organisms/empty_state.dart';
export 'src/organisms/error_state.dart';
export 'src/organisms/membership_card.dart';
export 'src/organisms/post_card.dart';
export 'src/organisms/product_card.dart';
export 'src/reveal.dart';
export 'src/theme.dart';
export 'src/token_swatch.dart';
