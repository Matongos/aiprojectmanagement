#!/usr/bin/env python3
"""
Test file to check analytics.py syntax
"""

try:
    from routers.analytics import router
    print("✅ analytics.py imported successfully!")
except IndentationError as e:
    print(f"❌ Indentation error in analytics.py: {e}")
except Exception as e:
    print(f"❌ Other error in analytics.py: {e}") 