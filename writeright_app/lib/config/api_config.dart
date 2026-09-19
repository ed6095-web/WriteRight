
/// Configuration for backend API connectivity.
/// Supports running on:
/// - Android Emulator: http://10.0.2.2:5000
/// - Physical Android Phone: http://<LAN_IP>:5000 (e.g. http://192.168.1.100:5000)
/// - Desktop / Localhost: http://127.0.0.1:5000
class ApiConfig {
  /// Default base URL.
  /// Change this to your computer's LAN IP when deploying to a physical Android device.
  static const String defaultProductionUrl = 'https://writeright-backend-gcwb.onrender.com';
  static const String defaultAndroidEmulatorUrl = 'http://10.0.2.2:5000';
  static const String defaultDesktopUrl = 'http://127.0.0.1:5000';

  /// Currently active base URL. Defaults to the live cloud backend on Render.
  static String _currentBaseUrl = defaultProductionUrl;

  static String get baseUrl => _currentBaseUrl;

  static set baseUrl(String url) {
    var trimmed = url.trim();
    if (trimmed.endsWith('/')) {
      trimmed = trimmed.substring(0, trimmed.length - 1);
    }
    _currentBaseUrl = trimmed;
  }

  // Endpoints
  static String get predictEndpoint => '$_currentBaseUrl/predict';
  static String get feedbackEndpoint => '$_currentBaseUrl/feedback';
  static String get healthEndpoint => '$_currentBaseUrl/health';

  /// Timeout duration for requests
  static const Duration requestTimeout = Duration(seconds: 12);
}
