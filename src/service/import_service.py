from processor.import_processor.main_graph import import_processor
from processor.import_processor.state import ImportNodeState, create_state
from utils import task_utils
from utils.logging_utils import logger


async def arun_import(task_id: str, origin_file_path: str) -> ImportNodeState:
    """异步执行导入图, 返回最终状态。

    import_processor 是同步编译图; 这里用 ainvoke 让 LangGraph 把同步节点
    调度到线程池, 避免阻塞 FastAPI 事件循环。
    """
    task_utils.clear_task(task_id)
    task_utils.set_task_status(task_id, task_utils.TaskStatus.PROCESSING.value)

    initial_state = create_state(
        task_id=task_id,
        origin_file_path=origin_file_path,
    )
    logger.info("导入任务启动: task_id={}, path={}", task_id, origin_file_path)

    try:
        end_state = await import_processor.ainvoke(initial_state)
    except Exception:
        task_utils.set_task_status(task_id, task_utils.TaskStatus.FAILED.value)
        logger.exception("导入任务失败: task_id={}", task_id)
        raise

    task_utils.set_task_status(task_id, task_utils.TaskStatus.COMPLETE.value)
    task_utils.set_task_result(task_id, "result", "ok")
    logger.info("导入任务完成: task_id={}", task_id)
    return end_state
