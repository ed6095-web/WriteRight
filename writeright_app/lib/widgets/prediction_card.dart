import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/prediction_result.dart';
import '../theme/app_theme.dart';
import 'confidence_bar.dart';
import 'digit_selector.dart';
import 'letter_selector.dart';

/// Professional card presenting the predicted digit, letter, or word,
/// along with confidence, segmented character breakdowns, and feedback actions.
class PredictionCard extends StatefulWidget {
  final PredictionResult result;
  final VoidCallback onConfirm;
  final ValueChanged<dynamic> onCorrect;
  final bool isSubmittingFeedback;
  final String? feedbackStatusMessage;

  const PredictionCard({
    super.key,
    required this.result,
    required this.onConfirm,
    required this.onCorrect,
    this.isSubmittingFeedback = false,
    this.feedbackStatusMessage,
  });

  @override
  State<PredictionCard> createState() => _PredictionCardState();
}

class _PredictionCardState extends State<PredictionCard> {
  bool _showCorrectionSelector = false;
  bool _showDetailedBreakdown = false;
  late final TextEditingController _wordCorrectionController;

  @override
  void initState() {
    super.initState();
    _wordCorrectionController = TextEditingController();
  }

  @override
  void dispose() {
    _wordCorrectionController.dispose();
    super.dispose();
  }

  void _submitWordCorrection() {
    final text = _wordCorrectionController.text.trim().toUpperCase();
    if (text.isEmpty) return;
    setState(() {
      _showCorrectionSelector = false;
    });
    widget.onCorrect(text);
  }

  @override
  Widget build(BuildContext context) {
    final result = widget.result;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppTheme.borderBlue, width: 1.2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Row: Mode Label, Prediction Value & Debug 28x28 Thumbnail
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${result.mode.toUpperCase()} PREDICTION',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.1,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        result.displayPrediction,
                        style: TextStyle(
                          fontSize: result.isWordMode ? 34 : 48,
                          fontWeight: FontWeight.w800,
                          letterSpacing: result.isWordMode ? 2.0 : -0.5,
                          height: 1.1,
                          color: AppTheme.darkBlue,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                // Mode Badge & Single Debug Thumbnail (for Digit/Letter)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppTheme.lightBlue,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppTheme.borderBlue),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            result.isWordMode
                                ? Icons.auto_stories_outlined
                                : result.isLetterMode
                                    ? Icons.text_fields_outlined
                                    : Icons.pin_outlined,
                            size: 15,
                            color: AppTheme.primaryBlue,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            result.isWordMode
                                ? '${result.characters.length} Letters'
                                : '${result.mode[0].toUpperCase()}${result.mode.substring(1)} ${result.displayPrediction}',
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.primaryBlue,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (!result.isWordMode && result.debugImageBase64 != null) ...[
                      const SizedBox(height: 8),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 44,
                            height: 44,
                            decoration: BoxDecoration(
                              color: Colors.black,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: AppTheme.borderBlue, width: 1.2),
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(5),
                              child: Image.memory(
                                base64Decode(result.debugImageBase64!),
                                fit: BoxFit.contain,
                                filterQuality: FilterQuality.none,
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Text(
                            'CNN 28×28',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Confidence Bar
            ConfidenceBar(confidence: result.confidence),

            // Word Mode: Character Previews & Confidences
            if (result.isWordMode && result.characters.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Text(
                'CHARACTER SEGMENTATION BREAKDOWN',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.9,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 8),
              SizedBox(
                height: 94,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: result.characters.length,
                  separatorBuilder: (context, index) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final char = result.characters[index];
                    final previewBase64 = char.debugImageBase64 ??
                        (index < result.characterPreviewsBase64.length
                            ? result.characterPreviewsBase64[index]
                            : null);

                    return Container(
                      width: 68,
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: AppTheme.scaffoldBackground,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppTheme.borderBlue),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          // Thumbnail 28x28
                          if (previewBase64 != null)
                            Container(
                              width: 36,
                              height: 36,
                              decoration: BoxDecoration(
                                color: Colors.black,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(4),
                                child: Image.memory(
                                  base64Decode(previewBase64),
                                  fit: BoxFit.contain,
                                  filterQuality: FilterQuality.none,
                                ),
                              ),
                            )
                          else
                            const SizedBox(height: 36),
                          const SizedBox(height: 4),
                          Text(
                            char.prediction,
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w800,
                              color: AppTheme.darkBlue,
                              height: 1.0,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            char.formattedConfidence,
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],

            // Toggleable Detailed Probabilities Section (for Single Digit or Single Letter)
            if (!result.isWordMode && result.probabilities.isNotEmpty) ...[
              const SizedBox(height: 12),
              InkWell(
                onTap: () {
                  setState(() {
                    _showDetailedBreakdown = !_showDetailedBreakdown;
                  });
                },
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _showDetailedBreakdown
                            ? 'Hide probability distribution'
                            : 'View class probabilities',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                      Icon(
                        _showDetailedBreakdown
                            ? Icons.keyboard_arrow_up
                            : Icons.keyboard_arrow_down,
                        size: 16,
                        color: AppTheme.primaryBlue,
                      ),
                    ],
                  ),
                ),
              ),
              if (_showDetailedBreakdown) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.scaffoldBackground,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.borderBlue.withOpacity(0.5)),
                  ),
                  child: Column(
                    children: _buildProbabilityList(result),
                  ),
                ),
              ],
            ],

            const Divider(height: 28, thickness: 1, color: AppTheme.borderBlue),

            // Feedback / Correction Section
            if (widget.feedbackStatusMessage != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppTheme.lightBlue,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.borderBlue),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_circle_outline,
                      size: 18,
                      color: AppTheme.successGreen,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        widget.feedbackStatusMessage!,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else if (_showCorrectionSelector)
              _buildCorrectionInput(result)
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    result.isWordMode
                        ? 'Was this word recognized correctly?'
                        : 'Was this prediction correct?',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: widget.isSubmittingFeedback ? null : widget.onConfirm,
                          icon: const Icon(Icons.check, size: 16),
                          label: const Text('Yes'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryBlue,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: widget.isSubmittingFeedback
                              ? null
                              : () {
                                  setState(() {
                                    _showCorrectionSelector = true;
                                    if (result.isWordMode) {
                                      _wordCorrectionController.text =
                                          result.displayPrediction;
                                    }
                                  });
                                },
                          icon: const Icon(Icons.edit_outlined, size: 16),
                          label: const Text('Correct it'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppTheme.textPrimary,
                            side: const BorderSide(color: AppTheme.borderBlue),
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildCorrectionInput(PredictionResult result) {
    if (result.isLetterMode) {
      return LetterSelector(
        onLetterSelected: (letter) {
          setState(() {
            _showCorrectionSelector = false;
          });
          widget.onCorrect(letter);
        },
        onCancel: () {
          setState(() {
            _showCorrectionSelector = false;
          });
        },
      );
    } else if (result.isWordMode) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.lightBlue.withOpacity(0.4),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.borderBlue),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'What word did you write?',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, size: 18, color: AppTheme.textSecondary),
                  onPressed: () {
                    setState(() {
                      _showCorrectionSelector = false;
                    });
                  },
                  visualDensity: VisualDensity.compact,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _wordCorrectionController,
              textCapitalization: TextCapitalization.characters,
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[a-zA-Z]')),
              ],
              decoration: InputDecoration(
                hintText: 'e.g. HELLO',
                filled: true,
                fillColor: Colors.white,
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppTheme.borderBlue),
                ),
              ),
              onSubmitted: (_) => _submitWordCorrection(),
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () {
                    setState(() {
                      _showCorrectionSelector = false;
                    });
                  },
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _submitWordCorrection,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Text('Save Correction'),
                ),
              ],
            ),
          ],
        ),
      );
    } else {
      // Digit Mode
      return DigitSelector(
        onDigitSelected: (correctDigit) {
          setState(() {
            _showCorrectionSelector = false;
          });
          widget.onCorrect(correctDigit);
        },
        onCancel: () {
          setState(() {
            _showCorrectionSelector = false;
          });
        },
      );
    }
  }

  List<Widget> _buildProbabilityList(PredictionResult result) {
    final sorted = result.sortedProbabilities;
    // Show top 6 for letters to prevent clutter, or all 10 for digits
    final itemsToShow = result.isLetterMode ? sorted.take(6).toList() : sorted;

    return itemsToShow.map((entry) {
      final label = entry.key.toString();
      final prob = entry.value;
      final isTop = label == result.displayPrediction;

      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          children: [
            SizedBox(
              width: 24,
              child: Text(
                '$label:',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: isTop ? FontWeight.w700 : FontWeight.w500,
                  color: isTop ? AppTheme.darkBlue : AppTheme.textSecondary,
                ),
              ),
            ),
            Expanded(
              child: LinearProgressIndicator(
                value: prob,
                backgroundColor: Colors.white,
                valueColor: AlwaysStoppedAnimation<Color>(
                  isTop ? AppTheme.primaryBlue : AppTheme.borderBlue,
                ),
                minHeight: 6,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 48,
              child: Text(
                '${(prob * 100).toStringAsFixed(1)}%',
                textAlign: TextAlign.right,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: isTop ? FontWeight.w700 : FontWeight.w400,
                  color: isTop ? AppTheme.darkBlue : AppTheme.textSecondary,
                ),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }
}
