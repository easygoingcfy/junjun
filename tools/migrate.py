# TODO
# - 执行数据库迁移升级

import os
import sys

# 回退：若直接运行该脚本，确保项目根在 sys.path 中
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from infrastructure.db.migrations import MigrationManager


def main():
    mgr = MigrationManager()
    mgr.upgrade()
    print("Migration completed.")


if __name__ == "__main__":
    main()
