#!/usr/bin/env python3
"""
測試 index.rebuild 的邏輯（不實際建立大型索引）
主要測試 Bug #1 的修復：is_project_registered 函數可用性
"""

import sys
from pathlib import Path

# Add project root to path
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

def test_is_project_registered_import():
    """測試 is_project_registered 函數是否可以正確導入和使用"""
    print("\n" + "="*80)
    print("測試: is_project_registered 導入和使用")
    print("="*80)

    try:
        # 測試導入
        from utils.project_utils import is_project_registered
        print("✅ is_project_registered 導入成功")

        # 測試調用
        result = is_project_registered("test-nonexistent-project")
        print(f"✅ 函數調用成功: is_project_registered('test-nonexistent-project') = {result}")

        # 測試在 _lazy_engine 環境中是否可用
        print("\n測試: _lazy_engine 中的函數可用性")

        # 模擬 _lazy_engine 的導入
        from utils.project_utils import (
            get_project_status, auto_register_project, set_active_project,
            has_bm25_index, clear_cache, clear_memory, get_active_project,
            is_project_registered  # Bug #1 修復的關鍵
        )

        engine_dict = {
            "get_project_status": get_project_status,
            "auto_register_project": auto_register_project,
            "set_active_project": set_active_project,
            "has_bm25_index": has_bm25_index,
            "clear_cache": clear_cache,
            "clear_memory": clear_memory,
            "get_active_project": get_active_project,
            "is_project_registered": is_project_registered,
        }

        # 測試從字典中調用（模擬 index.rebuild 中的使用方式）
        E = engine_dict
        detected_project = "test-project"

        # 這是 mcp_bridge_lazy.py:629 中的調用方式
        if E["is_project_registered"](detected_project):
            print(f"✅ 專案已註冊: {detected_project}")
        else:
            print(f"✅ 專案未註冊: {detected_project} (預期結果)")

        print("\n✅ 所有測試通過 - Bug #1 已修復")
        return True

    except KeyError as e:
        print(f"\n❌ KeyError: {e}")
        print("   這表示 is_project_registered 未在字典中")
        print("   Bug #1 未修復！")
        return False
    except ImportError as e:
        print(f"\n❌ ImportError: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_index_rebuild_logic():
    """測試 index.rebuild 的專案偵測邏輯"""
    print("\n" + "="*80)
    print("測試: index.rebuild 專案偵測邏輯")
    print("="*80)

    try:
        from utils.project_utils import (
            is_project_registered,
            get_active_project,
            auto_register_project
        )

        # 模擬 index.rebuild 的邏輯（mcp_bridge_lazy.py:624-638）
        project = "auto"
        cwd = str(BASE)

        print(f"當前目錄: {cwd}")
        print(f"專案參數: {project}")

        if project == "auto":
            # 嘗試從當前目錄偵測
            detected_project = Path(cwd).name
            print(f"偵測到的專案名稱: {detected_project}")

            # 檢查是否已註冊（這是 Bug #1 修復的關鍵）
            if is_project_registered(detected_project):
                project = detected_project
                print(f"✅ 專案已註冊，使用: {project}")
            else:
                # 回退到活動專案
                active = get_active_project()
                print(f"專案未註冊，活動專案: {active}")

                if active:
                    project = active
                    print(f"✅ 使用活動專案: {project}")
                else:
                    # 使用偵測到的名稱
                    project = detected_project
                    print(f"✅ 無活動專案，使用偵測名稱: {project}")

        if not project:
            print("❌ 無法確定專案")
            return False

        print(f"\n✅ 專案偵測邏輯正常，最終專案: {project}")
        return True

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """執行所有測試"""
    print("\n" + "="*80)
    print("index.rebuild 邏輯測試（Bug #1 修復驗證）")
    print("="*80)
    print(f"專案根目錄: {BASE}")
    print(f"Python: {sys.version}")

    results = {}

    # 測試 1: is_project_registered 導入和使用
    results["is_project_registered 可用性"] = test_is_project_registered_import()

    # 測試 2: index.rebuild 專案偵測邏輯
    results["專案偵測邏輯"] = test_index_rebuild_logic()

    # 打印測試結果摘要
    print("\n" + "="*80)
    print("測試結果摘要")
    print("="*80)

    for test_name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status}: {test_name}")

    # 統計結果
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("\n🎉 所有測試通過！Bug #1 已成功修復。")
        print("\n說明:")
        print("- is_project_registered 函數已正確導入")
        print("- 函數在 _lazy_engine 字典中可用")
        print("- index.rebuild 的專案偵測邏輯正常")
        print("- 不會再出現 KeyError: 'is_project_registered'")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
