import 'package:flutter/foundation.dart';

/// In-memory P0 favorite-cast state for the fan app mock shell.
///
/// The real persistence/event path belongs behind ASS-90/91. Until then this
/// store lets the profile, home, and schedule surfaces share one deterministic
/// state without introducing backend claims or public ranking behavior.
class FanFavoriteStore extends ChangeNotifier {
  FanFavoriteStore._() : _favoriteCastIds = {..._initialFavoriteCastIds};

  static const Set<String> _initialFavoriteCastIds = {'mio'};

  /// The singleton store used by the mock fan app.
  static final FanFavoriteStore instance = FanFavoriteStore._();

  Set<String> _favoriteCastIds;

  /// Current favorite cast ids as an immutable snapshot.
  Set<String> get favoriteCastIds => Set.unmodifiable(_favoriteCastIds);

  /// Whether [castId] is currently registered as a favorite.
  bool isFavorite(String castId) => _favoriteCastIds.contains(castId);

  /// Registers or removes [castId] as a favorite.
  void setFavorite(String castId, {required bool isFavorite}) {
    final next = {..._favoriteCastIds};
    if (isFavorite) {
      next.add(castId);
    } else {
      next.remove(castId);
    }

    if (setEquals(next, _favoriteCastIds)) return;
    _favoriteCastIds = next;
    notifyListeners();
  }

  /// Restores the mock seed state for widget tests and demo resets.
  void resetToInitialState() {
    _favoriteCastIds = {..._initialFavoriteCastIds};
    notifyListeners();
  }
}
