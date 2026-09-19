import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Clean, professional horizontal confidence progress bar.
class ConfidenceBar extends StatelessWidget {
  final double confidence; // 0.0 to 1.0

  const ConfidenceBar({
    super.key,
    required this.confidence,
  });

  @override
  Widget build(BuildContext context) {
    final clamped = confidence.clamp(0.0, 1.0);
    final percentageString = (clamped * 100).toStringAsFixed(2);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Confidence',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppTheme.textSecondary,
              ),
            ),
            Text(
              '$percentageString%',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppTheme.darkBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: Container(
            height: 10,
            width: double.infinity,
            color: AppTheme.lightBlue,
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: clamped,
              child: Container(
                decoration: BoxDecoration(
                  color: clamped > 0.8
                      ? AppTheme.primaryBlue
                      : (clamped > 0.5 ? AppTheme.accentBlue : AppTheme.warningOrange),
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
