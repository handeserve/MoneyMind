import logging
from . import config_manager as cm

logger = logging.getLogger(__name__)

def generate_system_prompt() -> str:
    """
    Dynamically generates the system prompt for classification based on the 
    categories defined in the configuration.
    """
    logger.info("Generating system prompt from preset categories.")
    
    try:
        categories = cm.get_preset_categories()
        if not categories:
            logger.warning("Preset categories are empty. Using a fallback prompt.")
            return 'You are a helpful assistant. Please classify the following expense into a category.'

        prompt_parts = [
            '你是一个专业的财务助手。你的任务是根据用户提供的支出描述，将其分类到预定义的类别中。',
            '请严格按照以下JSON格式返回结果: {"category_l1": "主分类", "category_l2": "子分类"}',
            '\n可用主分类和子分类如下:\n'
        ]

        for l1, l2_list in categories.items():
            if l2_list:
                l2_str = ", ".join(l2_list)
                prompt_parts.append(f'- {l1} (包含子分类: {l2_str})')
            else:
                prompt_parts.append(f'- {l1} (无子分类)')
        
        prompt_parts.append('\n## 注意事项：')
        prompt_parts.append('- category_l1 必须是可用主分类中的一个，完全匹配分类名称。')
        prompt_parts.append('- category_l2 必须是对应主分类下的一个子分类。如果无法或无需细分到子分类, 或者该主分类下没有定义子分类, 请返回空字符串 ""。')
        prompt_parts.append('- 只返回JSON格式，不要添加其他说明文字或代码块标记。')
        
        system_prompt = "\n".join(prompt_parts)
        logger.debug(f"Generated system prompt: {system_prompt}")
        return system_prompt

    except Exception as e:
        logger.error(f"Failed to generate system prompt due to an error: {e}", exc_info=True)
        # Fallback prompt in case of unexpected errors
        return 'You are a helpful assistant. Please classify the following expense into a category based on the provided examples.'

if __name__ == '__main__':
    # For testing the prompt generation
    logging.basicConfig(level=logging.DEBUG)
    print("--- Testing System Prompt Generation ---")
    # This requires the config_manager to be able to find a config file or use defaults
    generated_prompt = generate_system_prompt()
    print(generated_prompt)
    print("\n--- Test Complete ---") 