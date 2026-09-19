/// Data model representing a digit recognition prediction response from the Flask backend.
class PredictionResult {
  final int prediction;
  final double confidence;
  final Map<int, double> probabilities;

  const PredictionResult({
    required this.prediction,
    required this.confidence,
    required this.probabilities,
  });

  /// Factory constructor to parse JSON response from Flask backend.
  factory PredictionResult.fromJson(Map<String, dynamic> json) {
    final rawProbabilities = json['probabilities'] as Map<String, dynamic>? ?? {};
    final Map<int, double> parsedProbabilities = {};

    rawProbabilities.forEach((key, value) {
      final digit = int.tryParse(key);
      if (digit != null) {
        if (value is num) {
          parsedProbabilities[digit] = value.toDouble();
        }
      }
    });

    return PredictionResult(
      prediction: (json['prediction'] as num?)?.toInt() ?? 0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      probabilities: parsedProbabilities,
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
