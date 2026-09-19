import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Single point with stroke metadata
class StrokePoint {
  final Offset offset;
  StrokePoint(this.offset);
}

/// A continuous stroke consisting of points
class Stroke {
  final List<Offset> points;
  final Color color;
  final double strokeWidth;

  Stroke({
    required this.points,
    this.color = const Color(0xFF0D47A1), // Deep navy/blue stroke
    this.strokeWidth = 18.0, // High-contrast, bold stroke ideal for 28x28 MNIST downsampling
  });
}

/// CustomPainter that renders smooth finger/stylus strokes on a clean white surface.
class CanvasPainter extends CustomPainter {
  final List<Stroke> strokes;
  final Stroke? currentStroke;

  CanvasPainter({
    required this.strokes,
    this.currentStroke,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Draw solid white background to guarantee clean background for PNG export
    final Paint bgPaint = Paint()..color = Colors.white;
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), bgPaint);

    // 2. Draw all completed strokes
    for (final stroke in strokes) {
      _drawStroke(canvas, stroke);
    }

    // 3. Draw active in-progress stroke
    if (currentStroke != null) {
      _drawStroke(canvas, currentStroke!);
    }
  }

  void _drawStroke(Canvas canvas, Stroke stroke) {
    if (stroke.points.isEmpty) return;

    final Paint paint = Paint()
      ..color = stroke.color
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..strokeWidth = stroke.strokeWidth
      ..style = PaintingStyle.stroke;

    if (stroke.points.length == 1) {
      // Single tap -> draw a dot
      final dotPaint = Paint()
        ..color = stroke.color
        ..style = PaintingStyle.fill;
      canvas.drawCircle(stroke.points.first, stroke.strokeWidth / 2, dotPaint);
      return;
    }

    // Draw smooth quadratic bezier path connecting points
    final Path path = Path();
    path.moveTo(stroke.points[0].dx, stroke.points[0].dy);

    for (int i = 1; i < stroke.points.length; i++) {
      final p0 = stroke.points[i - 1];
      final p1 = stroke.points[i];
      final midPoint = Offset((p0.dx + p1.dx) / 2, (p0.dy + p1.dy) / 2);
      path.quadraticBezierTo(p0.dx, p0.dy, midPoint.dx, midPoint.dy);
    }

    final lastPoint = stroke.points.last;
    path.lineTo(lastPoint.dx, lastPoint.dy);

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CanvasPainter oldDelegate) => true;
}

/// Interactive Drawing Canvas Widget with gesture detection and boundary capture key.
class DrawingCanvas extends StatefulWidget {
  final GlobalKey boundaryKey;
  final ValueChanged<bool>? onDrawingChanged;

  const DrawingCanvas({
    super.key,
    required this.boundaryKey,
    this.onDrawingChanged,
  });

  @override
  State<DrawingCanvas> createState() => DrawingCanvasState();
}

class DrawingCanvasState extends State<DrawingCanvas> {
  final List<Stroke> _strokes = [];
  Stroke? _currentStroke;

  bool get hasStrokes => _strokes.isNotEmpty || _currentStroke != null;

  void clear() {
    setState(() {
      _strokes.clear();
      _currentStroke = null;
    });
    widget.onDrawingChanged?.call(false);
  }

  void _onPanStart(DragStartDetails details) {
    final RenderBox renderBox = context.findRenderObject() as RenderBox;
    final localPosition = renderBox.globalToLocal(details.globalPosition);

    setState(() {
      _currentStroke = Stroke(
        points: [localPosition],
      );
    });
    widget.onDrawingChanged?.call(true);
  }

  void _onPanUpdate(DragUpdateDetails details) {
    final RenderBox renderBox = context.findRenderObject() as RenderBox;
    final localPosition = renderBox.globalToLocal(details.globalPosition);

    if (_currentStroke != null) {
      setState(() {
        _currentStroke!.points.add(localPosition);
      });
    }
  }

  void _onPanEnd(DragEndDetails details) {
    if (_currentStroke != null) {
      setState(() {
        _strokes.add(_currentStroke!);
        _currentStroke = null;
      });
    }
    widget.onDrawingChanged?.call(hasStrokes);
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      key: widget.boundaryKey,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: AppTheme.borderBlue,
              width: 1.5,
            ),
          ),
          child: GestureDetector(
            onPanStart: _onPanStart,
            onPanUpdate: _onPanUpdate,
            onPanEnd: _onPanEnd,
            behavior: HitTestBehavior.opaque,
            child: CustomPaint(
              painter: CanvasPainter(
                strokes: _strokes,
                currentStroke: _currentStroke,
              ),
              child: Stack(
                children: [
                  if (!hasStrokes)
                    const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.draw_outlined,
                            size: 40,
                            color: AppTheme.borderBlue,
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Draw a digit (0–9) here',
                            style: TextStyle(
                              color: AppTheme.textMuted,
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
