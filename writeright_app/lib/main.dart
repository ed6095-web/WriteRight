import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const WriteRightApp());
}

class WriteRightApp extends StatelessWidget {
  const WriteRightApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WriteRight',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const HomeScreen(),
    );
  }
}
