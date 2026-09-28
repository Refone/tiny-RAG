from utils.path_utils import PROJECT_ROOT

def load_prompt(prompt_template: str, **kwargs) -> str:
    """
    加载提示词
    Args:
        prompt_name: 提示词模板名称
        kwargs: 提示词参数
    Returns:
        拼装好的提示词
    """
    prompt_path = PROJECT_ROOT / f"src/common/prompt/{prompt_template}.prompt"
    print(prompt_path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file {prompt_path} not found")

    prompt = prompt_path.read_text(encoding="utf-8")

    if kwargs:
        prompt = prompt.format(**kwargs)

    return prompt

if __name__ == "__main__":
    prompt = load_prompt("image_summary",
                         md_title="咖啡机使用说明",
                         pre_text="这是操作面板",
                         post_text="关机在这个地方",)
    print(prompt)