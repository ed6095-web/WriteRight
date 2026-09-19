/// Data model representing a digit recognition prediction response from the Flask backend.
class PredictionResult {
  final int prediction;
  final double confidence;
  final Map<int, double> probabilities;
  final String? debugImageBase64;

  const PredictionResult({
    required this.prediction,
    required this.confidence,
    required this.probabilities,
    this.debugImageBase64,
  });

  /// Factory constructor to parse JSON response from Flask backend.
  /// Seamlessly supports probabilities formatted as either a List or Map.
  factory PredictionResult.fromJson(Map<String, dynamic> json) {
    final rawProbabilities = json['probabilities'];
    final Map<int, double> parsedProbabilities = {};

    if (rawProbabilities is List) {
      for (int i = 0; i < rawProbabilities.length; i++) {
        final val = rawProbabilities[i];
        if (val is num) {
          parsedProbabilities[i] = val.toDouble();
        }
      }
    } else if (rawProbabilities is Map) {
      rawProbabilities.forEach((key, value) {
        final digit = int.tryParse(key.toString());
        if (digit != null && value is num) {
          parsedProbabilities[digit] = value.toDouble();
        }
      });
    }

    return PredictionResult(
      prediction: (json['prediction'] as num?)?.toInt() ?? 0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      probabilities: parsedProbabilities,
      debugImageBase64: json['debug_image_base64'] as String?,
    );
  }

  /// Formatted confidence string (e.g., "95.17%")
  String get formattedConfidence => '${(confidence * 100).toStringAsFixed(2)}%';

  /// Top 3 most likely alternative digits
  List<MapEntry<int, double>> get sortedProbabilities {
    final entries = probabilities.entries.toList();
    entries.sort((a, b) => b.value.compareTo(a.value));
    return entries;
  }
}
