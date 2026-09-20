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

  // Drawing tools state
  double _brushSize = 14.0; // Default: Medium (14px)
  Color _brushColor = const Color(0xFF0D47A1); // Default: WriteRight Blue
  bool _showToolsMenu = false;

  // Available brush sizes: Small (8px), Medium (14px), Large (20px)
  static const List<Map<String, dynamic>> _brushSizes = [
    {'name': 'Small', 'size': 8.0},
    {'name': 'Medium', 'size': 14.0},
    {'name': 'Large', 'size': 20.0},
  ];

  // Available colors: Blue, Black, Red, Green, Purple
  static const List<Map<String, dynamic>> _brushColors = [
    {'name': 'Blue', 'color': Color(0xFF0D47A1)},
    {'name': 'Black', 'color': Color(0xFF212121)},
    {'name': 'Red', 'color': Color(0xFFD32F2F)},
    {'name': 'Green', 'color': Color(0xFF2E7D32)},
    {'name': 'Purple', 'color': Color(0xFF7B1FA2)},
  ];

  double get brushSize => _brushSize;
  Color get brushColor => _brushColor;

  bool get hasStrokes => _strokes.isNotEmpty || _currentStroke != null;

  void clear() {
    setState(() {
      _strokes.clear();
      _currentStroke = null;
      _showToolsMenu = false;
    });
    widget.onDrawingChanged?.call(false);
  }

  void _onPanStart(DragStartDetails details) {
    if (_showToolsMenu) {
      setState(() {
        _showToolsMenu = false;
      });
    }

    final RenderBox renderBox = context.findRenderObject() as RenderBox;
    final localPosition = renderBox.globalToLocal(details.globalPosition);

    setState(() {
      _currentStroke = Stroke(
        points: [localPosition],
        strokeWidth: _brushSize,
        color: _brushColor,
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
    return ClipRRect(
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
          child: Stack(
            fit: StackFit.expand,
            children: [
              // RepaintBoundary isolates only the pure white drawing canvas and user strokes
              RepaintBoundary(
                key: widget.boundaryKey,
                child: CustomPaint(
                  painter: CanvasPainter(
                    strokes: _strokes,
                    currentStroke: _currentStroke,
                  ),
                  size: Size.infinite,
                ),
              ),

              // Placeholder guide if canvas is blank
              if (!hasStrokes)
                const IgnorePointer(
                  child: Center(
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
                          'Write here with finger or stylus',
                          style: TextStyle(
                            color: AppTheme.textMuted,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

              // Floating Drawing Tools Popup Card (Outside RepaintBoundary so never captured)
              if (_showToolsMenu)
                Positioned(
                  bottom: 60,
                  right: 12,
                  child: GestureDetector(
                    onTap: () {}, // Prevent pan on canvas
                    child: Material(
                      elevation: 8,
                      borderRadius: BorderRadius.circular(16),
                      color: Colors.white,
                      shadowColor: Colors.black.withOpacity(0.2),
                      child: Container(
                        width: 230,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppTheme.borderBlue),
                        ),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Header
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Row(
                                  children: [
                                    Icon(Icons.brush, size: 16, color: AppTheme.primaryBlue),
                                    SizedBox(width: 6),
                                    Text(
                                      'Drawing Tools',
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                        color: AppTheme.darkBlue,
                                      ),
                                    ),
                                  ],
                                ),
                                InkWell(
                                  borderRadius: BorderRadius.circular(12),
                                  onTap: () {
                                    setState(() {
                                      _showToolsMenu = false;
                                    });
                                  },
                                  child: const Padding(
                                    padding: EdgeInsets.all(2),
                                    child: Icon(Icons.close, size: 16, color: AppTheme.textMuted),
                                  ),
                                ),
                              ],
                            ),
                            const Divider(height: 16, color: AppTheme.borderBlue),

                            // Brush Size Section
                            const Text(
                              'Brush Size',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.textSecondary,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: _brushSizes.map((opt) {
                                final isSelected = _brushSize == opt['size'];
                                return InkWell(
                                  borderRadius: BorderRadius.circular(8),
                                  onTap: () {
                                    setState(() {
                                      _brushSize = opt['size'] as double;
                                    });
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: isSelected ? AppTheme.primaryBlue : AppTheme.lightBlue.withOpacity(0.4),
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: isSelected ? AppTheme.primaryBlue : AppTheme.borderBlue,
                                      ),
                                    ),
                                    child: Text(
                                      opt['name'] as String,
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                        color: isSelected ? Colors.white : AppTheme.textPrimary,
                                      ),
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                            const SizedBox(height: 14),

                            // Brush Color Section
                            const Text(
                              'Brush Color',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.textSecondary,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: _brushColors.map((opt) {
                                final color = opt['color'] as Color;
                                final isSelected = _brushColor.value == color.value;
                                return InkWell(
                                  borderRadius: BorderRadius.circular(16),
                                  onTap: () {
                                    setState(() {
                                      _brushColor = color;
                                    });
                                  },
                                  child: Container(
                                    width: 32,
                                    height: 32,
                                    decoration: BoxDecoration(
                                      color: color,
                                      shape: BoxShape.circle,
                                      border: Border.all(
                                        color: isSelected ? AppTheme.primaryBlue : Colors.white,
                                        width: isSelected ? 2.5 : 1.5,
                                      ),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withOpacity(0.15),
                                          blurRadius: 3,
                                          offset: const Offset(0, 1),
                                        ),
                                      ],
                                    ),
                                    child: isSelected
                                        ? const Center(
                                            child: Icon(
                                              Icons.check,
                                              size: 16,
                                              color: Colors.white,
                                            ),
                                          )
                                        : null,
                                  ),
                                );
                              }).toList(),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

              // Floating Circular Brush Tools Button (Bottom-Right, outside RepaintBoundary)
              Positioned(
                bottom: 12,
                right: 12,
                child: GestureDetector(
                  onTap: () {
                    setState(() {
                      _showToolsMenu = !_showToolsMenu;
                    });
                  },
                  child: Material(
                    elevation: 4,
                    shape: const CircleBorder(),
                    color: Colors.white,
                    child: Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white,
                        border: Border.all(color: AppTheme.borderBlue, width: 1.5),
                      ),
                      child: Center(
                        child: Icon(
                          Icons.palette_outlined,
                          size: 20,
                          color: _brushColor,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
