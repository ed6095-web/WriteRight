import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/prediction_result.dart';

/// Custom exception for backend API errors with user-friendly messages.
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

/// Service to interact with the Python Flask ML backend.
class ApiService {
  final http.Client _client;

  ApiService({http.Client? client}) : _client = client ?? http.Client();

  /// Health check to test backend connection and model availability.
  Future<Map<String, dynamic>> checkHealth() async {
    try {
      final response = await _client
          .get(Uri.parse(ApiConfig.healthEndpoint))
          .timeout(ApiConfig.requestTimeout);

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw ApiException(
          'Server returned status ${response.statusCode}: ${response.body}',
          statusCode: response.statusCode,
        );
      }
    } on SocketException {
      throw ApiException(
        "Couldn't connect to the recognition server at ${ApiConfig.baseUrl}.\n"
        "Ensure the Flask backend is running on your computer.",
      );
    } on TimeoutException {
      throw ApiException('Connection timed out. The server took too long to respond.');
    } on FormatException {
      throw ApiException('Received invalid response format from server.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Connection error: $e');
    }
  }

  /// Send captured handwriting PNG bytes to Flask /predict with specified mode ('digit', 'letter', 'word').
  Future<PredictionResult> predict(
    Uint8List imageBytes, {
    String mode = 'digit',
  }) async {
    if (imageBytes.isEmpty) {
      throw ApiException('Please draw on the canvas before recognizing.');
    }

    try {
      final uri = Uri.parse(ApiConfig.predictEndpoint);
      final request = http.MultipartRequest('POST', uri);

      request.fields['mode'] = mode;
      final multipartFile = http.MultipartFile.fromBytes(
        'image',
        imageBytes,
        filename: 'handwriting_$mode.png',
      );
      request.files.add(multipartFile);

      final streamedResponse =
          await _client.send(request).timeout(ApiConfig.requestTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final Map<String, dynamic> jsonResponse = json.decode(response.body);
        return PredictionResult.fromJson(jsonResponse, expectedMode: mode);
      } else {
        String errorMsg = 'Recognition failed (${response.statusCode})';
        try {
          final errorJson = json.decode(response.body);
          if (errorJson['error'] != null) {
            errorMsg = errorJson['error'];
          }
        } catch (_) {}
        throw ApiException(errorMsg, statusCode: response.statusCode);
      }
    } on SocketException {
      throw ApiException(
        "Couldn't connect to the recognition server at ${ApiConfig.baseUrl}.\n"
        "Please check your internet connection or server status.",
      );
    } on TimeoutException {
      throw ApiException(
        'Request timed out while waiting for prediction. '
        'The server may be waking up, please try again in a moment.',
      );
    } on FormatException {
      throw ApiException('Invalid data received from recognition server.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Error during recognition: $e');
    }
  }

  /// Convenience wrapper for backwards compatibility with digit mode.
  Future<PredictionResult> predictDigit(Uint8List imageBytes) {
    return predict(imageBytes, mode: 'digit');
  }

  /// Send user correction to Flask /feedback.
  Future<bool> sendFeedback(
    Uint8List imageBytes,
    dynamic correctLabel, {
    String mode = 'digit',
  }) async {
    try {
      final uri = Uri.parse(ApiConfig.feedbackEndpoint);
      final request = http.MultipartRequest('POST', uri);

      request.fields['correct_label'] = correctLabel.toString();
      request.fields['mode'] = mode;
      request.files.add(
        http.MultipartFile.fromBytes(
          'image',
          imageBytes,
          filename: 'feedback_${mode}_$correctLabel.png',
        ),
      );

      final streamedResponse =
          await _client.send(request).timeout(ApiConfig.requestTimeout);
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return true;
      } else {
        throw ApiException(
          'Failed to record feedback (${response.statusCode})',
          statusCode: response.statusCode,
        );
      }
    } on SocketException {
      throw ApiException(
        "Couldn't connect to the server at ${ApiConfig.baseUrl} to save feedback.",
      );
    } on TimeoutException {
      throw ApiException('Request timed out while saving feedback.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Feedback error: $e');
    }
  }
}
