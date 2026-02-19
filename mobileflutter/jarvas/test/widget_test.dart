import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:jarvas/app.dart';

void main() {
  testWidgets('App starts with ProviderScope and JarvasApp', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: JarvasApp()));
    await tester.pump();
    expect(find.byType(CupertinoApp), findsOneWidget);
  });
}
