# 日志打印装饰器

给一个节点函数写一个装饰器, 可以自动打印日志, 计算时间

```python
@node_log("node_import_milvus")
def node_upsert_milvus(state: ImportGraphState):
    ...
    return state
```

最终打印:

```
TODO
```

## 1. 写出最终的调用

```python
result = func(*args, **kwargs)
```

## 2. 增加计时逻辑和相关打印

```python
start_ts = time.time()  # 秒(float)
logger.info(f"节点开始")

result = func(*args, **kwargs)

cost_ms = int((time.time() - start_ts) * 1000)
logger.info(f"节点完成, 耗时={cost_ms}ms")

return result
```

## 3. 增加异常处理

```python
start_ts = time.time()
logger.info(f"节点开始")
try:
    result = func(*args, **kwargs)
    cost_ms = int((time.time() - start_ts) * 1000)
    logger.info(f"节点完成, 耗时={cost_ms}ms")
    return result
except Exception:
    # opt(exception=True) 可以打印异常堆栈
    logger.opt(exception=True).error("节点异常")
    # raise 保证不吞 exception, 继续抛出
    raise
```

## 4. 设置为装饰器

```python
def node_log(func):
    def wrapper(*args, **kwargs):
        start_ts = time.time()  # 秒(float)
        logger.info(f"节点开始")
        try:
            result = func(*args, **kwargs)
            cost_ms = int((time.time() - start_ts) * 1000)
            logger.info(f"节点完成, 耗时={cost_ms}ms")
            return result
        except Exception:
            logger.opt(exception=True).error("节点异常")
            raise
    return wrapper
```

> 现在, 可以实现如下测试代码:
>
> ```python
> @node_log
> def node_test(state: NodeState):
>     logger.info("processing...")
>     state["a"] = state["a"] + 1
>     return state
>
> """
> ... | INFO    | logging_util.py:wrapper:66  节点开始
> ... | INFO    | logging_util.py:node_test:92  ...
> ... | INFO    | logging_util.py:wrapper:71  节点完成, 耗时=0ms
> """
> ```

## 5. 设置为有参数的装饰器, 并在内部使用参数

```python
def node_log(node_name: str):   # <---
    def deco(func):   # <---
        def wrapper(*args, **kwargs):
            start_ts = time.time()
            logger.info(f"[{node_name}] 节点开始")
            try:
                result = func(*args, **kwargs)
                cost_ms = int((time.time() - start_ts) * 1000)
                logger.info(f"[{node_name}] 节点完成, 耗时={cost_ms}ms")
                return result
            except Exception:
                logger.opt(exception=True).error(f"[{node_name}] 节点异常")
                raise
        return wrapper
    return deco # <---
```

## 6. 添加一些其他辅助信息打印

```python
def node_log(node_name: str):

    def _task_id(state) -> str:
        return state.get("task_id", "-")

    def deco(func):
        # 明确装饰函数要有一个 state 参数
        def wrapper(state, *args, **kwargs):
            task_id = _task_id(state)
            start_ts = time.time()
            logger.info(f"<task_id = {task_id}> [{node_name}] 节点开始")
            try:
                result = func(state, *args, **kwargs)
                cost_ms = int((time.time() - start_ts) * 1000)
                logger.info(f"<task_id = {task_id}> [{node_name}] 节点完成, 耗时={cost_ms}ms")
                return result
            except Exception:
                logger.opt(exception=True).error(f"<task_id = {task_id}> [{node_name}] 节点异常")
                raise
        return wrapper
    return deco
```

- 此时, 可以得到这样的测试效果:

  ```python
  @node_log("node_test")
  def node_test(state: NodeState):
      logger.info("processing...")
      state["a"] = state["a"] + 1
      return state

  start_state: NodeState = {"a": 0, "task_id": 12345}
  end_state = node_test(state=start_state)
  logger.info(end_state["a"])

  """
  ... | INFO    | logging_util.py:wrapper:72  <task_id = 12345> [node_test] 节点开始
  ... | INFO    | logging_util.py:node_test:97  processing...
  ... | INFO    | logging_util.py:wrapper:76  <task_id = 12345> [node_test] 节点完成, 耗时=0ms
  ... | INFO    | logging_util.py:<module>:103 1
  """
  ```

- 但是, 如果在其他文件使用此装饰器, 文件和函数名显示是不正确的. 需要:
  1. 通过 `logger.patch` 更新打印的堆栈追踪, 剔除堆栈顶层的 logger frame.
  2. 通过 `@wrap` 保留原函数名、文档、注解等元信息, 否则只会追踪到装饰函数.

两处修改完成, 即可得到最终版本:

## 7. 剔除 log 模块堆栈信息 (最终版本)

```python
def fix_log_position(record):
    """
    为了在其他文件中调用 logger 打印
    能正常追踪文件与函数名
    这里需要剔除 logging 模块的 frame
    """
    def _this_is_logging_frame(frame):
        if ('logging_util.py' in frame.filename):
            return True
        if ('_logger.py' in frame.filename):
            return True
        if ('_log' in frame.function):
            return True
        return False

    for frame in inspect.stack():
        if _this_is_logging_frame(frame):
            continue
        record.update(
            file=frame.filename.split("/")[-1].split("\\")[-1],
            function=frame.function,
            line=frame.lineno
        )
        break


logger = base_logger.patch(fix_log_position)

def node_log(node_name: str):

    def _task_id(state) -> str:
        return state.get("task_id", "-")

    def deco(func):
        # 明确装饰函数要有一个 state 参数
        @wraps(func)
        def wrapper(state, *args, **kwargs):
            task_id = _task_id(state)
            start_ts = time.time()
            logger.info(f"<task_id = {task_id}> [{node_name}] 节点开始")
            try:
                result = func(state, *args, **kwargs)
                cost_ms = int((time.time() - start_ts) * 1000)
                logger.info(f"<task_id = {task_id}> [{node_name}] 节点完成, 耗时={cost_ms}ms")
                return result
            except Exception:
                logger.opt(exception=True).error(f"<task_id = {task_id}> [{node_name}] 节点异常")
                raise
        return wrapper
    return deco
```
