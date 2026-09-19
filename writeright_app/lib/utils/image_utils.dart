import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

/// Utilities for converting Flutter Canvas drawings into PNG bytes for API transmission.
class ImageUtils {
  /// Captures the specified [RepaintBoundary] as compressed PNG bytes.
  /// Uses a pixel ratio of 2.0 for sharp, high-fidelity capture of strokes.
  static Future<Uint8List?> captureBoundaryToPng(GlobalKey repaintBoundaryKey) async {
    try {
      final boundary = repaintBoundaryKey.currentContext?.findRenderObject()
          as RenderRepaintBoundary?;
      if (boundary == null) return null;

      final ui.Image image = await boundary.toImage(pixelRatio: 2.0);
      final ByteData? byteData =
          await image.toByteData(format: ui.ImageByteFormat.png);

      return byteData?.buffer.asUint8List();
    } catch (e) {
      debugPrint('Error capturing canvas boundary: $e');
      return null;
    }
  }
}
