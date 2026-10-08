from __future__ import annotations

from processor.import_processor.main_graph import import_processor
from processor.import_processor.state import create_state
from utils import task_utils
from utils.logging_utils import logger
from rich import print as rprint
from utils.path_utils import PROJECT_ROOT

task_id = "import-pdf-test"
# origin_file_path = PROJECT_ROOT / "asset/hak180产品安全手册.pdf"
origin_file_path = PROJECT_ROOT / "asset/万用表RS-12的使用.pdf"

task_utils.clear_task(task_id)
initial_state = create_state(
    task_id=task_id,
    origin_file_path=str(origin_file_path),
)

end_state = import_processor.invoke(initial_state)

logger.complete()

rprint(task_utils.get_task_done_nodes(task_id))
rprint(end_state)