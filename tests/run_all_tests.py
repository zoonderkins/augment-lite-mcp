#!/usr/bin/env python3
"""
統一測試運行器
支持不同級別的測試：快速測試、完整測試、端到端測試
"""

import sys
import subprocess
import time
from pathlib import Path
from typing import List, Tuple

# 測試文件配置
TEST_SUITES = {
    "unit": {
        "description": "單元測試（快速，無需 API key）",
        "tests": [
            "test_index_rebuild_logic.py",  # Bug #1 驗證
            "test_ace_enhancements.py",      # ACE 功能測試
        ],
        "timeout": 60  # 秒
    },
    "api": {
        "description": "MCP API 測試（需要數據庫和索引）",
        "tests": [
            "test_all_mcp_apis.py",          # 基本 API 測試
            "test_high_priority_apis.py",    # 高優先級 API
            "test_medium_priority_apis.py",  # 中優先級 API
        ],
        "timeout": 120
    },
    "integration": {
        "description": "整合測試（需要 Proxy 和索引）",
        "tests": [
            "test_dedup_ranking_filtering.py",  # 去重、排序、過濾
            "test_rag_generate_proxies.py",      # Proxy Port 測試
        ],
        "timeout": 180
    }
}


def run_test_file(test_file: str, timeout: int = 120) -> Tuple[bool, str, float]:
    """
    運行單個測試文件

    Returns:
        (success: bool, output: str, duration: float)
    """
    test_path = Path(__file__).parent / test_file

    if not test_path.exists():
        return False, f"測試文件不存在: {test_file}", 0.0

    print(f"\n{'='*80}")
    print(f"運行: {test_file}")
    print(f"{'='*80}")

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=test_path.parent.parent  # 在專案根目錄運行
        )

        duration = time.time() - start_time

        # 打印輸出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        success = result.returncode == 0

        if success:
            print(f"\n✅ {test_file} 通過 ({duration:.1f}s)")
        else:
            print(f"\n❌ {test_file} 失敗 ({duration:.1f}s)")
            print(f"   Exit code: {result.returncode}")

        return success, result.stdout + result.stderr, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"\n⏱️  {test_file} 超時 ({timeout}s)")
        return False, f"Timeout after {timeout}s", duration

    except Exception as e:
        duration = time.time() - start_time
        print(f"\n💥 {test_file} 異常: {e}")
        return False, str(e), duration


def run_test_suite(suite_name: str) -> Tuple[int, int, float]:
    """
    運行測試套件

    Returns:
        (passed: int, total: int, total_duration: float)
    """
    if suite_name not in TEST_SUITES:
        print(f"❌ 未知的測試套件: {suite_name}")
        print(f"可用套件: {', '.join(TEST_SUITES.keys())}")
        return 0, 0, 0.0

    suite = TEST_SUITES[suite_name]

    print(f"\n{'='*80}")
    print(f"測試套件: {suite_name}")
    print(f"描述: {suite['description']}")
    print(f"測試數量: {len(suite['tests'])}")
    print(f"{'='*80}")

    passed = 0
    total = len(suite['tests'])
    total_duration = 0.0
    results = []

    for test_file in suite['tests']:
        success, output, duration = run_test_file(test_file, suite['timeout'])
        total_duration += duration

        if success:
            passed += 1

        results.append({
            'file': test_file,
            'success': success,
            'duration': duration
        })

    # 打印摘要
    print(f"\n{'='*80}")
    print(f"測試套件 '{suite_name}' 完成")
    print(f"{'='*80}")

    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['file']}: {result['duration']:.1f}s")

    print(f"\n總計: {passed}/{total} 測試通過")
    print(f"總耗時: {total_duration:.1f}s")

    return passed, total, total_duration


def run_all_suites():
    """運行所有測試套件"""
    print(f"\n{'#'*80}")
    print(f"# 運行所有測試套件")
    print(f"{'#'*80}")

    total_passed = 0
    total_tests = 0
    total_duration = 0.0
    suite_results = []

    for suite_name in TEST_SUITES.keys():
        passed, total, duration = run_test_suite(suite_name)
        total_passed += passed
        total_tests += total
        total_duration += duration

        suite_results.append({
            'name': suite_name,
            'passed': passed,
            'total': total,
            'duration': duration
        })

    # 最終摘要
    print(f"\n{'#'*80}")
    print(f"# 最終摘要")
    print(f"{'#'*80}")

    for result in suite_results:
        status = "✅" if result['passed'] == result['total'] else "⚠️"
        percentage = (result['passed'] / result['total'] * 100) if result['total'] > 0 else 0
        print(f"{status} {result['name']}: {result['passed']}/{result['total']} ({percentage:.0f}%) - {result['duration']:.1f}s")

    print(f"\n{'#'*80}")
    print(f"總計: {total_passed}/{total_tests} 測試通過 ({total_passed/total_tests*100:.0f}%)")
    print(f"總耗時: {total_duration:.1f}s ({total_duration/60:.1f}分鐘)")
    print(f"{'#'*80}")

    return total_passed == total_tests


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(
        description="統一測試運行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
測試套件：
  unit         - 單元測試（快速，無需 API key）
  api          - MCP API 測試（需要數據庫和索引）
  integration  - 整合測試（需要 Proxy 和索引）
  all          - 運行所有測試

使用範例：
  # 運行單元測試
  python tests/run_all_tests.py --suite unit

  # 運行所有測試
  python tests/run_all_tests.py --suite all

  # 運行特定測試文件
  python tests/run_all_tests.py --file test_high_priority_apis.py

  # 快速檢查（僅單元測試）
  python tests/run_all_tests.py --quick
        """
    )

    parser.add_argument(
        '--suite',
        choices=['unit', 'api', 'integration', 'all'],
        default='all',
        help='要運行的測試套件'
    )

    parser.add_argument(
        '--file',
        help='運行特定測試文件'
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='快速測試模式（僅運行 unit 套件）'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='顯示詳細輸出'
    )

    args = parser.parse_args()

    # 快速模式
    if args.quick:
        print("🚀 快速測試模式")
        passed, total, duration = run_test_suite('unit')
        success = passed == total

    # 運行特定文件
    elif args.file:
        success, output, duration = run_test_file(args.file)

    # 運行套件
    elif args.suite == 'all':
        success = run_all_suites()

    else:
        passed, total, duration = run_test_suite(args.suite)
        success = passed == total

    # 返回狀態碼
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
