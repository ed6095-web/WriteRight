import 'package:flutter_test/flutter_test.dart';
import 'package:writeright_app/main.dart';

void main() {
  testWidgets('WriteRight app smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const WriteRightApp());
    await tester.pumpAndSettle();

    expect(find.text('WriteRight'), findsOneWidget);
    expect(find.text('Handwriting Recognition'), findsOneWidget);
    expect(find.text('Write your digit'), findsOneWidget);
    expect(find.text('Clear'), findsOneWidget);
    expect(find.text('Recognize'), findsOneWidget);
  });
}
