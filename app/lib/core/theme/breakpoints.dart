import 'package:flutter/widgets.dart';

/// Mobile < 600 · Tablet 600–1024 · Desktop/Web ≥ 1024.
class Breakpoints {
  static const mobile = 600.0;
  static const tablet = 1024.0;

  static bool isMobile(BuildContext context) => MediaQuery.sizeOf(context).width < mobile;
  static bool isTablet(BuildContext context) {
    final w = MediaQuery.sizeOf(context).width;
    return w >= mobile && w < tablet;
  }

  static bool isDesktop(BuildContext context) => MediaQuery.sizeOf(context).width >= tablet;
}
