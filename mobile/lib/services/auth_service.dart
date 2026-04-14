import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:logger/logger.dart';
import 'package:uuid/uuid.dart';

import '../utils/constants.dart';

final _logger = Logger(printer: PrettyPrinter(methodCount: 0));
const _storage = FlutterSecureStorage();
const _uuid = Uuid();

/// Manages JWT token lifecycle (request, store, refresh).
class AuthService {
  static const _tokenKey = 'jwt_access_token';
  static const _deviceIdKey = 'device_id';

  String? _cachedToken;

  Future<String> getDeviceId() async {
    String? id = await _storage.read(key: _deviceIdKey);
    if (id == null) {
      id = _uuid.v4();
      await _storage.write(key: _deviceIdKey, value: id);
    }
    return id;
  }

  /// Returns a valid JWT, refreshing if needed.
  Future<String> getToken({bool forceRefresh = false}) async {
    if (!forceRefresh && _cachedToken != null) return _cachedToken!;

    final stored = await _storage.read(key: _tokenKey);
    if (!forceRefresh && stored != null && !_isExpired(stored)) {
      _cachedToken = stored;
      return stored;
    }

    return _fetchNewToken();
  }

  Future<String> _fetchNewToken() async {
    final deviceId = await getDeviceId();
    final uri = Uri.parse('${AppConstants.apiBaseUrl}${AppConstants.authTokenEndpoint}');

    try {
      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'client_id': deviceId}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final token = data['access_token'] as String;
        await _storage.write(key: _tokenKey, value: token);
        _cachedToken = token;
        _logger.i('JWT token refreshed');
        return token;
      } else {
        throw Exception('Auth failed: ${response.statusCode}');
      }
    } on SocketException {
      throw Exception('No network connection');
    }
  }

  bool _isExpired(String token) {
    try {
      final parts = token.split('.');
      if (parts.length != 3) return true;
      final payload = jsonDecode(
        utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
      ) as Map<String, dynamic>;
      final exp = payload['exp'] as int?;
      if (exp == null) return true;
      // Treat as expired if within 60s of expiry
      return DateTime.now().millisecondsSinceEpoch / 1000 > exp - 60;
    } catch (_) {
      return true;
    }
  }

  Future<void> clearToken() async {
    _cachedToken = null;
    await _storage.delete(key: _tokenKey);
  }
}
