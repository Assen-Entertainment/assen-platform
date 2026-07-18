// A Dio adapter that records each request and replies with a fixed status +
// JSON body, so a repository's real send/parse/translate path runs in-process
// without a socket. The write-action tests use it to assert the HTTP method and
// path a repository issues and to simulate an error status (Dio raises a
// DioException for a >= 400 status, which the repository translates).

import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

/// Captures every outbound request and answers with a fixed [status] + [body].
class RecordingAdapter implements HttpClientAdapter {
  /// Creates an adapter answering with [status] (default 200) and JSON [body].
  RecordingAdapter({this.status = 200, this.body = const {}});

  /// The HTTP status returned for every request.
  int status;

  /// The JSON object serialized as the response body.
  Map<String, dynamic> body;

  /// Every request the client issued, in order.
  final List<RequestOptions> requests = [];

  /// The most recent request (method + path assertions).
  RequestOptions get last => requests.last;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// A [Dio] wired to [adapter] with a fixed base URL (no real socket).
Dio recordingDio(RecordingAdapter adapter) =>
    Dio(BaseOptions(baseUrl: 'http://localhost:8000'))
      ..httpClientAdapter = adapter;
