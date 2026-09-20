import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../config/api_config.dart';
import '../models/prediction_result.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/image_utils.dart';
import '../widgets/drawing_canvas.dart';
import '../widgets/prediction_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GlobalKey _canvasBoundaryKey = GlobalKey();
  final GlobalKey<DrawingCanvasState> _canvasKey = GlobalKey<DrawingCanvasState>();
  final ApiService _apiService = ApiService();

  String _currentMode = 'digit'; // 'digit' | 'letter' | 'word'
  bool _hasDrawing = false;
  bool _isRecognizing = false;
  bool _isSlowRequest = false;
  bool _isSubmittingFeedback = false;
  Timer? _slowRequestTimer;
  Uint8List? _lastCapturedImage;
  PredictionResult? _predictionResult;
  String? _feedbackStatusMessage;

  @override
  void dispose() {
    _slowRequestTimer?.cancel();
    super.dispose();
  }

  void _onDrawingChanged(bool hasDrawing) {
    setState(() {
      _hasDrawing = hasDrawing;
      if (!hasDrawing) {
        _predictionResult = null;
        _lastCapturedImage = null;
        _feedbackStatusMessage = null;
      }
    });
  }

  void _clearCanvas() {
    _canvasKey.currentState?.clear();
    setState(() {
      _hasDrawing = false;
      _predictionResult = null;
      _lastCapturedImage = null;
      _feedbackStatusMessage = null;
    });
  }

  void _onModeChanged(String mode) {
    if (_currentMode == mode) return;
    _clearCanvas();
    setState(() {
      _currentMode = mode;
    });
  }

  Future<void> _recognize() async {
    if (!_hasDrawing) {
      final modeLabel = _currentMode == 'word'
          ? 'a word'
          : _currentMode == 'letter'
              ? 'an uppercase letter'
              : 'a digit';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Please write $modeLabel on the canvas first.'),
          backgroundColor: AppTheme.darkBlue,
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    setState(() {
      _isRecognizing = true;
      _isSlowRequest = false;
      _feedbackStatusMessage = null;
    });

    _slowRequestTimer?.cancel();
    _slowRequestTimer = Timer(const Duration(milliseconds: 2500), () {
      if (mounted && _isRecognizing) {
        setState(() {
          _isSlowRequest = true;
        });
      }
    });

    try {
      final imageBytes = await ImageUtils.captureBoundaryToPng(_canvasBoundaryKey);
      if (imageBytes == null || imageBytes.isEmpty) {
        throw ApiException('Failed to capture canvas image.');
      }

      _lastCapturedImage = imageBytes;
      final result = await _apiService.predict(imageBytes, mode: _currentMode);

      setState(() {
        _predictionResult = result;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
          backgroundColor: AppTheme.warningOrange,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 4),
          action: SnackBarAction(
            label: 'Server IP',
            textColor: Colors.white,
            onPressed: _showServerConfigDialog,
          ),
        ),
      );
    } finally {
      _slowRequestTimer?.cancel();
      if (mounted) {
        setState(() {
          _isRecognizing = false;
          _isSlowRequest = false;
        });
      }
    }
  }

  Future<void> _confirmCorrectPrediction() async {
    if (_lastCapturedImage == null || _predictionResult == null) return;

    setState(() {
      _isSubmittingFeedback = true;
    });

    try {
      await _apiService.sendFeedback(
        _lastCapturedImage!,
        _predictionResult!.prediction,
        mode: _currentMode,
      );
      if (!mounted) return;
      setState(() {
        _feedbackStatusMessage = 'Confirmed! Sample saved to improve future training.';
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Feedback note: $e'),
          backgroundColor: AppTheme.textSecondary,
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingFeedback = false;
        });
      }
    }
  }

  Future<void> _submitCorrection(dynamic correctLabel) async {
    if (_lastCapturedImage == null) return;

    setState(() {
      _isSubmittingFeedback = true;
    });

    try {
      await _apiService.sendFeedback(
        _lastCapturedImage!,
        correctLabel,
        mode: _currentMode,
      );
      if (!mounted) return;
      setState(() {
        _feedbackStatusMessage =
            'Saved! Corrected label ($correctLabel) stored successfully.';
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to save correction: $e'),
          backgroundColor: AppTheme.warningOrange,
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingFeedback = false;
        });
      }
    }
  }

  void _showServerConfigDialog() {
    final controller = TextEditingController(text: ApiConfig.baseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text(
          'Backend Server Configuration',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Enter your Flask server URL. For physical phones, use your computer\'s Wi-Fi LAN IP (e.g. http://192.168.1.50:5000):',
              style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Base URL',
                hintText: 'http://192.168.x.x:5000',
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                ActionChip(
                  label: const Text('Render Cloud (Live)'),
                  avatar: const Icon(Icons.cloud_outlined, size: 16),
                  onPressed: () => controller.text = ApiConfig.defaultProductionUrl,
                ),
                ActionChip(
                  label: const Text('Emulator (10.0.2.2)'),
                  onPressed: () => controller.text = ApiConfig.defaultAndroidEmulatorUrl,
                ),
                ActionChip(
                  label: const Text('Localhost (127.0.0.1)'),
                  onPressed: () => controller.text = ApiConfig.defaultDesktopUrl,
                ),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {
                ApiConfig.baseUrl = controller.text;
              });
              Navigator.of(ctx).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Server URL set to: ${ApiConfig.baseUrl}'),
                  behavior: SnackBarBehavior.floating,
                ),
              );
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  String get _subtitleText {
    switch (_currentMode) {
      case 'letter':
        return 'Write a single uppercase letter (A–Z) and let the CNN recognize it.';
      case 'word':
        return 'Write a word horizontally with slight spacing between letters.';
      case 'digit':
      default:
        return 'Write a single digit (0–9) and let the CNN recognize it.';
    }
  }

  String get _headerTitle {
    switch (_currentMode) {
      case 'letter':
        return 'Write your letter';
      case 'word':
        return 'Write your word';
      case 'digit':
      default:
        return 'Write your digit';
    }
  }

  String get _recognizeButtonLabel {
    if (_isRecognizing) return 'Recognizing...';
    switch (_currentMode) {
      case 'letter':
        return 'Recognize Letter';
      case 'word':
        return 'Recognize Word';
      case 'digit':
      default:
        return 'Recognize Digit';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Icon(
                    Icons.edit_note,
                    color: Colors.white,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 8),
                const Text(
                  'WriteRight',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.darkBlue,
                    letterSpacing: -0.5,
                  ),
                ),
              ],
            ),
            const Text(
              'Handwriting Recognition',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Configure Backend Server URL',
            icon: const Icon(Icons.settings_ethernet, color: AppTheme.primaryBlue),
            onPressed: _showServerConfigDialog,
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Subtitle
              Text(
                _subtitleText,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w400,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 16),

              // Canvas Section Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    _headerTitle,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  if (_hasDrawing)
                    const Text(
                      'Ready to recognize',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.primaryBlue,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 10),

              // Drawing Canvas Container (Dynamic aspect ratio: 1.0 for digits/letters, 2.2 for words)
              AspectRatio(
                aspectRatio: _currentMode == 'word' ? 2.2 : 1.0,
                child: DrawingCanvas(
                  key: _canvasKey,
                  boundaryKey: _canvasBoundaryKey,
                  onDrawingChanged: _onDrawingChanged,
                ),
              ),
              const SizedBox(height: 12),

              // Pill-shaped Mode Tabs near the bottom of handwriting area: [ Digits ] [ Letters ] [ Words ]
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: AppTheme.lightBlue.withOpacity(0.45),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: AppTheme.borderBlue),
                ),
                child: Row(
                  children: [
                    _buildModePill(
                      label: 'Digits',
                      mode: 'digit',
                      icon: Icons.pin_outlined,
                    ),
                    const SizedBox(width: 4),
                    _buildModePill(
                      label: 'Letters',
                      mode: 'letter',
                      icon: Icons.text_fields_outlined,
                    ),
                    const SizedBox(width: 4),
                    _buildModePill(
                      label: 'Words',
                      mode: 'word',
                      icon: Icons.auto_stories_outlined,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Action Buttons Row: [ Clear ] [ Recognize ]
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: OutlinedButton.icon(
                      onPressed: _hasDrawing ? _clearCanvas : null,
                      icon: const Icon(Icons.refresh, size: 18),
                      label: const Text('Clear'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 3,
                    child: ElevatedButton.icon(
                      onPressed: (_hasDrawing && !_isRecognizing) ? _recognize : null,
                      icon: _isRecognizing
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Icon(Icons.search, size: 18),
                      label: Text(_recognizeButtonLabel),
                    ),
                  ),
                ],
              ),

              // Cold-start wakeup hint
              if (_isSlowRequest) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.lightBlue,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.borderBlue),
                  ),
                  child: const Row(
                    children: [
                      SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Connecting to cloud server (waking up free instance, ~20-30s)...',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            color: AppTheme.darkBlue,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              const SizedBox(height: 24),

              // Prediction Result Card
              if (_predictionResult != null)
                PredictionCard(
                  result: _predictionResult!,
                  onConfirm: _confirmCorrectPrediction,
                  onCorrect: _submitCorrection,
                  isSubmittingFeedback: _isSubmittingFeedback,
                  feedbackStatusMessage: _feedbackStatusMessage,
                ),

              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildModePill({
    required String label,
    required String mode,
    required IconData icon,
  }) {
    final isSelected = _currentMode == mode;
    return Expanded(
      child: GestureDetector(
        onTap: () => _onModeChanged(mode),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? AppTheme.primaryBlue : Colors.transparent,
            borderRadius: BorderRadius.circular(20),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: AppTheme.primaryBlue.withOpacity(0.25),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                size: 15,
                color: isSelected ? Colors.white : AppTheme.textSecondary,
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
                  color: isSelected ? Colors.white : AppTheme.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
