import 'package:flutter_test/flutter_test.dart';

import 'package:jarvas/core/config.dart';

void main() {
  group('normalizeBaseUrl', () {
    test('adds http when missing', () {
      expect(normalizeBaseUrl('192.168.1.90:3000'), 'http://192.168.1.90:3000');
    });
    test('removes trailing slash', () {
      expect(normalizeBaseUrl('http://host/'), 'http://host');
    });
    test('keeps https', () {
      expect(normalizeBaseUrl('https://host'), 'https://host');
    });
  });
}
