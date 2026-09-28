from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from common.enum.doc_type import DocType
from processor.import_processor.main_graph import import_processor
from processor.import_processor.state import create_state
from utils import task_utils
from utils.logging_utils import logger
from rich import print as rprint

task_id = "import-pdf-debug"
origin_file_path = PROJECT_ROOT / "test" / "test-data" / "hak180产品安全手册.pdf"

task_utils.clear_task(task_id)
initial_state = create_state(
    task_id=task_id,
    origin_file_path=str(origin_file_path),
)

end_state = import_processor.invoke(initial_state)

logger.complete()

rprint(task_utils.get_task_done_nodes(task_id))
rprint(end_state)