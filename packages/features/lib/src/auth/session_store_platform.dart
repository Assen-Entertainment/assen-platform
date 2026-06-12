export 'session_store_io.dart'
    if (dart.library.js_interop) 'session_store_web.dart'
    show createPlatformSessionStore;
