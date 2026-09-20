/// Per-character prediction result used in Word Mode.
class CharacterPrediction {
  final String prediction;
  final double confidence;
  final String? debugImageBase64;

  const CharacterPrediction({
    required this.prediction,
    required this.confidence,
    this.debugImageBase64,
  });

  factory CharacterPrediction.fromJson(Map<String, dynamic> json) {
    return CharacterPrediction(
      prediction: json['prediction']?.toString() ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      debugImageBase64: json['debug_image_base64'] as String?,
    );
  }

  String get formattedConfidence => '${(confidence * 100).toStringAsFixed(1)}%';
}

/// Data model representing a recognition prediction response from the Flask backend.
/// Supports Digits, Letters, and Words modes seamlessly.
class PredictionResult {
  final String mode; // 'digit' | 'letter' | 'word'
  final String prediction; // "7", "E", "HELLO"
  final double confidence;
  final Map<dynamic, double> probabilities;
  final String? debugImageBase64;
  final List<CharacterPrediction> characters;
  final List<String> characterPreviewsBase64;

  const PredictionResult({
    required this.mode,
    required this.prediction,
    required this.confidence,
    required this.probabilities,
    this.debugImageBase64,
    this.characters = const [],
    this.characterPreviewsBase64 = const [],
  });

  /// Factory constructor to parse JSON response from Flask backend.
  factory PredictionResult.fromJson(Map<String, dynamic> json, {String? expectedMode}) {
    final mode = (json['mode'] as String?)?.toLowerCase() ?? expectedMode?.toLowerCase() ?? 'digit';
    final rawProbabilities = json['probabilities'];
    final Map<dynamic, double> parsedProbabilities = {};

    if (rawProbabilities is List) {
      for (int i = 0; i < rawProbabilities.length; i++) {
        final val = rawProbabilities[i];
        if (val is num) {
          if (mode == 'letter' || mode == 'letters') {
            parsedProbabilities[String.fromCharCode(65 + i)] = val.toDouble();
          } else {
            parsedProbabilities[i] = val.toDouble();
          }
        }
      }
    } else if (rawProbabilities is Map) {
      rawProbabilities.forEach((key, value) {
        if (value is num) {
          final digit = int.tryParse(key.toString());
          parsedProbabilities[digit ?? key.toString()] = value.toDouble();
        }
      });
    }

    // Parse characters for word mode
    final List<CharacterPrediction> chars = [];
    if (json['characters'] is List) {
      for (final item in json['characters']) {
        if (item is Map<String, dynamic>) {
          chars.add(CharacterPrediction.fromJson(item));
        }
      }
    }

    // Parse character previews
    final List<String> previews = [];
    if (json['character_previews_base64'] is List) {
      for (final item in json['character_previews_base64']) {
        if (item is String) {
          previews.add(item);
        }
      }
    }

    return PredictionResult(
      mode: mode,
      prediction: json['prediction']?.toString() ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      probabilities: parsedProbabilities,
      debugImageBase64: json['debug_image_base64'] as String?,
      characters: chars,
      characterPreviewsBase64: previews,
    );
  }

  /// String representation of primary prediction
  String get displayPrediction => prediction;

  /// Formatted confidence string (e.g., "95.17%")
  String get formattedConfidence => '${(confidence * 100).toStringAsFixed(2)}%';

  bool get isWordMode => mode == 'word' || mode == 'words';
  bool get isLetterMode => mode == 'letter' || mode == 'letters';
  bool get isDigitMode => mode == 'digit' || mode == 'digits';

  /// Top sorted alternatives
  List<MapEntry<dynamic, double>> get sortedProbabilities {
    final entries = probabilities.entries.toList();
    entries.sort((a, b) => b.value.compareTo(a.value));
    return entries;
  }
}
