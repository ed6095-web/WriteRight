import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/prediction_result.dart';
import '../theme/app_theme.dart';
import 'confidence_bar.dart';
import 'digit_selector.dart';

/// Professional card presenting the predicted digit, confidence, and feedback actions.
class PredictionCard extends StatefulWidget {
  final PredictionResult result;
  final VoidCallback onConfirm;
  final ValueChanged<int> onCorrect;
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

  @override
  Widget build(BuildContext context) {
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
            // Header Row: Label & Top Prediction Badge & Debug 28x28 Image
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'PREDICTION',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.1,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${widget.result.prediction}',
                      style: const TextStyle(
                        fontSize: 48,
                        fontWeight: FontWeight.w800,
                        height: 1.0,
                        color: AppTheme.darkBlue,
                      ),
                    ),
                  ],
                ),
                if (widget.result.debugImageBase64 != null)
                  Column(
                    children: [
                      Container(
                        width: 56,
                        height: 56,
                        decoration: BoxDecoration(
                          color: Colors.black,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.borderBlue, width: 1.5),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(6),
                          child: Image.memory(
                            base64Decode(widget.result.debugImageBase64!),
                            fit: BoxFit.contain,
                            filterQuality: FilterQuality.none,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'CNN 28×28 Input',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
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
                      const Icon(
                        Icons.verified_outlined,
                        size: 16,
                        color: AppTheme.primaryBlue,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Digit ${widget.result.prediction}',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Confidence Bar
            ConfidenceBar(confidence: widget.result.confidence),

            const SizedBox(height: 12),

            // Toggleable Detailed Probabilities Section
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
                          : 'View all class probabilities',
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
                  children: List.generate(10, (digit) {
                    final prob = widget.result.probabilities[digit] ?? 0.0;
                    final isTop = digit == widget.result.prediction;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 24,
                            child: Text(
                              '$digit:',
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
                  }),
                ),
              ),
            ],

            const Divider(height: 32, thickness: 1, color: AppTheme.borderBlue),

            // Feedback Section
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
              DigitSelector(
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
              )
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Was this prediction correct?',
                    style: TextStyle(
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
}
