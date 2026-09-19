import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Clean digit selector grid (0-9) allowing the user to correct misclassifications.
class DigitSelector extends StatelessWidget {
  final ValueChanged<int> onDigitSelected;
  final VoidCallback onCancel;

  const DigitSelector({
    super.key,
    required this.onDigitSelected,
    required this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
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
                'What digit did you write?',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 18, color: AppTheme.textSecondary),
                onPressed: onCancel,
                visualDensity: VisualDensity.compact,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Row 1: 0 - 4
          Row(
            children: List.generate(5, (index) {
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: _DigitButton(
                    digit: index,
                    onPressed: () => onDigitSelected(index),
                  ),
                ),
              );
            }),
          ),
          const SizedBox(height: 8),
          // Row 2: 5 - 9
          Row(
            children: List.generate(5, (index) {
              final digit = index + 5;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: _DigitButton(
                    digit: digit,
                    onPressed: () => onDigitSelected(digit),
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }
}

class _DigitButton extends StatelessWidget {
  final int digit;
  final VoidCallback onPressed;

  const _DigitButton({
    required this.digit,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onPressed,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        height: 44,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppTheme.borderBlue, width: 1.2),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.02),
              blurRadius: 2,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: Text(
          '$digit',
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: AppTheme.darkBlue,
          ),
        ),
      ),
    );
  }
}
