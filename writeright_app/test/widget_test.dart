import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:writeright_app/main.dart';

void main() {
  testWidgets('WriteRight app smoke and mode switching test', (WidgetTester tester) async {
    // Set a realistic phone test viewport (412 x 915)
    tester.view.physicalSize = const Size(412, 915);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(const WriteRightApp());
    await tester.pumpAndSettle();

    // Verify App Header
    expect(find.text('WriteRight'), findsOneWidget);
    expect(find.text('Handwriting Recognition'), findsOneWidget);

    // Verify Default Mode is Digits
    expect(find.text('Write your digit'), findsOneWidget);
    expect(find.text('Digits'), findsOneWidget);
    expect(find.text('Letters'), findsOneWidget);
    expect(find.text('Words'), findsOneWidget);

    // Switch to Letters Mode
    await tester.ensureVisible(find.text('Letters'));
    await tester.tap(find.text('Letters'));
    await tester.pumpAndSettle();
    expect(find.text('Write your letter'), findsOneWidget);
    expect(find.text('Recognize Letter'), findsOneWidget);

    // Switch to Words Mode
    await tester.ensureVisible(find.text('Words'));
    await tester.tap(find.text('Words'));
    await tester.pumpAndSettle();
    expect(find.text('Write your word'), findsOneWidget);
    expect(find.text('Recognize Word'), findsOneWidget);

    // Switch back to Digits Mode
    await tester.ensureVisible(find.text('Digits'));
    await tester.tap(find.text('Digits'));
    await tester.pumpAndSettle();
    expect(find.text('Write your digit'), findsOneWidget);
    expect(find.text('Recognize Digit'), findsOneWidget);
  });
}
